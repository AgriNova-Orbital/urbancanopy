import type { PriorityZonesCollection, PriorityZoneFeature } from "./artifacts";

export type UtciBand = {
  label: string;
  minimum: number;
  maximum: number | null;
};

const UTCI_BANDS: UtciBand[] = [
  { minimum: 46, maximum: null, label: "very strong heat stress" },
  { minimum: 38, maximum: 46, label: "strong heat stress" },
  { minimum: 32, maximum: 38, label: "moderate heat stress" },
  { minimum: 26, maximum: 32, label: "no thermal stress" },
  { minimum: 9, maximum: 26, label: "slight cold stress" },
  { minimum: 0, maximum: 9, label: "moderate cold stress" },
  { minimum: -13, maximum: 0, label: "strong cold stress" },
  { minimum: -27, maximum: -13, label: "very strong cold stress" },
  { minimum: -40, maximum: -27, label: "extreme cold stress" },
  { minimum: Number.NEGATIVE_INFINITY, maximum: -40, label: "extreme cold stress" },
];

export function classifyUtciEquivalentTemperature(value: number): UtciBand {
  return (
    UTCI_BANDS.find((band) => value >= band.minimum && (band.maximum === null || value < band.maximum)) ??
    UTCI_BANDS[UTCI_BANDS.length - 1]
  );
}

function scoreToEquivalentTemperature(score: number, minimum: number, maximum: number): number {
  if (!Number.isFinite(score)) {
    return 26;
  }

  if (maximum <= minimum) {
    return 26;
  }

  const normalized = Math.max(0, Math.min(1, (score - minimum) / (maximum - minimum)));

  return 26 + normalized * 20;
}

export function decoratePriorityZonesWithUtci<T extends PriorityZonesCollection>(zones: T): T {
  const scores = zones.features.map((feature) => feature.properties.priority_score);
  const minimum = scores.length ? Math.min(...scores) : 0;
  const maximum = scores.length ? Math.max(...scores) : 1;

  return {
    ...zones,
    features: zones.features.map((feature: PriorityZoneFeature) => {
      const utcValue = scoreToEquivalentTemperature(feature.properties.priority_score, minimum, maximum);
      const level = classifyUtciEquivalentTemperature(utcValue);

      return {
        ...feature,
        properties: {
          ...feature.properties,
          utci_equivalent_temperature: utcValue,
          utci_level: level.label,
        },
      };
    }),
  };
}
