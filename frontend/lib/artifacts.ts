import Papa from "papaparse";
import { decoratePriorityZonesWithUtci } from "./utci";

export interface PriorityZoneFeature {
  type: "Feature";
  properties: {
    priority_score: number;
    zone_id?: string;
    utci_equivalent_temperature?: number;
    utci_level?: string;
    [key: string]: unknown;
  };
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: unknown;
  };
}

export interface PriorityZonesCollection {
  type: "FeatureCollection";
  features: PriorityZoneFeature[];
}

export interface CitySignatureRow {
  city: string;
  heat_gap_c: number;
  mean_ndvi: number;
  mean_ndbi: number;
  signature_score: number;
}

export interface CityComparisonRow {
  city: string;
  heat_gap_c: number;
}

export interface ParkCoolingRow {
  park_id: string;
  delta_lst_c: number;
  ci_low_c: number;
  ci_high_c: number;
}

export interface DashboardArtifacts {
  priorityZones: PriorityZonesCollection | null;
  citySignatures: CitySignatureRow[];
  cityComparison: CityComparisonRow[];
  parkCooling: ParkCoolingRow[];
  errors: string[];
}

function asRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function formatLoadError(name: string, error: unknown): string {
  if (error instanceof Error) {
    return `${name}: ${error.message}`;
  }

  return `${name}: failed to load`;
}

export async function loadJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`failed to load ${url}: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function loadPriorityZones(url = "/data/priority_zones.geojson"): Promise<PriorityZonesCollection> {
  const value = await loadJson<unknown>(url);

  if (!asRecord(value) || value.type !== "FeatureCollection" || !Array.isArray(value.features)) {
    throw new Error("priority zones file is malformed");
  }

  return decoratePriorityZonesWithUtci({
    type: "FeatureCollection",
    features: value.features
      .filter(asRecord)
      .map((feature) => ({
        type: "Feature",
        properties: {
          ...(asRecord(feature.properties) ? feature.properties : {}),
          priority_score: toNumber(asRecord(feature.properties) ? feature.properties.priority_score : 0),
          zone_id: toString(asRecord(feature.properties) ? feature.properties.zone_id : ""),
        },
        geometry: asRecord(feature.geometry)
          ? {
              type: feature.geometry.type === "Polygon" || feature.geometry.type === "MultiPolygon" ? feature.geometry.type : "Polygon",
              coordinates: feature.geometry.coordinates,
            }
          : { type: "Polygon", coordinates: [] },
      })),
  });
}

export function getHighestPriorityZone(zones: PriorityZonesCollection | null | undefined): PriorityZoneFeature | null {
  if (!zones?.features.length) {
    return null;
  }

  return zones.features.reduce<PriorityZoneFeature | null>((current, next) => {
    if (!current) {
      return next;
    }

    return next.properties.priority_score > current.properties.priority_score ? next : current;
  }, null);
}

async function loadCsvRows<T>(url: string, mapRow: (row: Record<string, unknown>) => T | null): Promise<T[]> {
  const response = await fetch(url, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`failed to load ${url}: ${response.status}`);
  }

  const parsed = Papa.parse<Record<string, unknown>>(await response.text(), {
    header: true,
    dynamicTyping: true,
    skipEmptyLines: true,
  });

  return (parsed.data ?? [])
    .filter(asRecord)
    .map(mapRow)
    .filter((row): row is T => row !== null);
}

export async function loadCitySignatures(url = "/data/city_signature.csv"): Promise<CitySignatureRow[]> {
  return loadCsvRows(url, (row) => {
    const city = toString(row.city);

    if (!city) {
      return null;
    }

    return {
      city,
      heat_gap_c: toNumber(row.heat_gap_c),
      mean_ndvi: toNumber(row.mean_ndvi),
      mean_ndbi: toNumber(row.mean_ndbi),
      signature_score: toNumber(row.signature_score),
    };
  });
}

export async function loadCityComparison(url = "/data/city_comparison.csv"): Promise<CityComparisonRow[]> {
  return loadCsvRows(url, (row) => {
    const city = toString(row.city);

    if (!city) {
      return null;
    }

    return {
      city,
      heat_gap_c: toNumber(row.heat_gap_c),
    };
  });
}

export async function loadParkCooling(url = "/data/park_cooling.csv"): Promise<ParkCoolingRow[]> {
  return loadCsvRows(url, (row) => {
    const parkId = toString(row.park_id);

    if (!parkId) {
      return null;
    }

    return {
      park_id: parkId,
      delta_lst_c: toNumber(row.delta_lst_c),
      ci_low_c: toNumber(row.ci_low_c),
      ci_high_c: toNumber(row.ci_high_c),
    };
  });
}

async function loadOptional<T>(name: string, loader: () => Promise<T>, fallback: T): Promise<{ value: T; error: string | null }> {
  try {
    return { value: await loader(), error: null };
  } catch (error) {
    return { value: fallback, error: formatLoadError(name, error) };
  }
}

export async function loadDashboardArtifacts(): Promise<DashboardArtifacts> {
  const [priorityZones, citySignatures, cityComparison, parkCooling] = await Promise.all([
    loadOptional("priority_zones.geojson", () => loadPriorityZones(), null),
    loadOptional("city_signature.csv", () => loadCitySignatures(), []),
    loadOptional("city_comparison.csv", () => loadCityComparison(), []),
    loadOptional("park_cooling.csv", () => loadParkCooling(), []),
  ]);

  return {
    priorityZones: priorityZones.value,
    citySignatures: citySignatures.value,
    cityComparison: cityComparison.value,
    parkCooling: parkCooling.value,
    errors: [priorityZones.error, citySignatures.error, cityComparison.error, parkCooling.error].filter(
      (error): error is string => Boolean(error),
    ),
  };
}
