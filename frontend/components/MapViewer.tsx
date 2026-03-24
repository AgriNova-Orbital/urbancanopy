"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Map, { NavigationControl, Source, Layer, type FillLayer, type MapRef, type MapLayerMouseEvent } from "react-map-gl/maplibre";
import bbox from "@turf/bbox";
import "maplibre-gl/dist/maplibre-gl.css";
import { getHighestPriorityZone, loadPriorityZones, type PriorityZonesCollection } from "../lib/artifacts";
import { reportFrontendRuntimeError } from "../lib/runtime-error-dedupe";

type MapViewerProps = {
  selectedZoneId: string | null;
  onZoneSelect: (zoneId: string | null) => void;
};

const streetStyle = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap Contributors",
    },
  },
  layers: [
    {
      id: "osm-tiles",
      type: "raster",
      source: "osm",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

const satelliteStyle = {
  version: 8,
  sources: {
    esri: {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
      attribution: "&copy; Esri",
    },
  },
  layers: [
    {
      id: "satellite-tiles",
      type: "raster",
      source: "esri",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

const priorityLayerStyle: FillLayer = {
  id: "priority-zones-fill",
  type: "fill",
  source: "priority-data",
  paint: {
    "fill-color": [
      "interpolate",
      ["linear"],
      ["get", "utci_equivalent_temperature"],
      26,
      "#fde68a",
      32,
      "#fb923c",
      38,
      "#f97316",
      46,
      "#b91c1c",
    ],
    "fill-opacity": 0.6,
  },
};

const selectedLayerStyle: FillLayer = {
  id: "priority-zones-selected",
  type: "fill",
  source: "priority-data",
  paint: {
    "fill-color": "#22d3ee",
    "fill-opacity": 0.2,
  },
};

export default function MapViewer({ selectedZoneId, onZoneSelect }: MapViewerProps) {
  const [geoData, setGeoData] = useState<PriorityZonesCollection | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [mapStyleType, setMapStyleType] = useState<"streets" | "satellite">("streets");
  const [clickedCoords, setClickedCoords] = useState<{lat: number; lon: number} | null>(null);
  const [weather, setWeather] = useState<Record<string, unknown> | null>(null);
  const mapRef = useRef<MapRef>(null);

  const fitToPriorityZones = useCallback((data: PriorityZonesCollection) => {
    if (!mapRef.current || !data.features?.length) {
      return;
    }

    const [minLng, minLat, maxLng, maxLat] = bbox(data as never);
    mapRef.current.fitBounds(
      [[minLng, minLat], [maxLng, maxLat]],
      { padding: 80, duration: 1500 },
    );
  }, []);

  useEffect(() => {
    let active = true;

    loadPriorityZones()
      .then((data) => {
        if (!active) {
          return;
        }

        setGeoData(data);
        if (!selectedZoneId) {
          onZoneSelect(getHighestPriorityZone(data)?.properties.zone_id ?? null);
        }
        if (mapReady) {
          fitToPriorityZones(data);
        }
      })
      .catch((error) => {
        reportFrontendRuntimeError("Failed to load priority zones", error);
        if (active) {
          setMapError("Priority zones could not be loaded.");
        }
      });

    return () => {
      active = false;
    };
  }, [fitToPriorityZones, mapReady, onZoneSelect, selectedZoneId]);

  useEffect(() => {
    if (geoData && mapReady) {
      fitToPriorityZones(geoData);
    }
  }, [fitToPriorityZones, geoData, mapReady]);

  useEffect(() => {
    if (!clickedCoords) {
      setWeather(null);
      return;
    }

    let active = true;
    setWeather(null);
    fetch(`/api/weather?lat=${clickedCoords.lat}&lon=${clickedCoords.lon}`)
      .then((res) => res.json())
      .then((data: unknown) => {
        if (active && typeof data === "object" && data !== null && !("error" in data)) {
          setWeather(data as Record<string, unknown>);
        }
      })
      .catch((err: unknown) => {
        console.error("Weather fetch failed", err);
      });

    return () => {
      active = false;
    };
  }, [clickedCoords]);

  const onMapClick = useCallback(
    (event: MapLayerMouseEvent) => {
      const { lngLat } = event;
      setClickedCoords({ lat: lngLat.lat, lon: lngLat.lng });

      const feature = event.features?.[0] as
        | { properties?: Record<string, unknown> }
        | undefined;
      const zoneId =
        typeof feature?.properties?.zone_id === "string"
          ? feature.properties.zone_id
          : null;

      onZoneSelect(zoneId);
    },
    [onZoneSelect],
  );

  return (
    <div className="absolute inset-0 min-h-screen w-screen bg-slate-950">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 121.5,
          latitude: 25.03,
          zoom: 11,
        }}
        mapStyle={mapStyleType === "streets" ? streetStyle : satelliteStyle}
        interactiveLayerIds={
          geoData ? ["priority-zones-fill", "priority-zones-selected"] : undefined
        }
        onLoad={() => {
          setMapReady(true);
          setMapError(null);
        }}
        onError={(event) => {
          reportFrontendRuntimeError(
            "Map initialization failed",
            event.error,
          );
          setMapError(
            event.error?.message ?? "Interactive map failed to initialize.",
          );
        }}
        onClick={geoData ? onMapClick : undefined}
        reuseMaps
        style={{ width: "100%", height: "100%" }}
      >
        <NavigationControl position="bottom-right" />

        {geoData ? (
          <Source id="priority-data" type="geojson" data={geoData as never}>
            <Layer {...priorityLayerStyle} />
            {selectedZoneId ? (
              <Layer
                {...selectedLayerStyle}
                filter={["==", "zone_id", selectedZoneId]}
              />
            ) : null}
          </Source>
        ) : null}
      </Map>

      <div className="pointer-events-none absolute left-6 top-6 z-20 rounded-full border border-white/10 bg-slate-950/80 px-3 py-1 text-xs uppercase tracking-[0.24em] text-cyan-100 backdrop-blur">
        Taipei UTCI priority
      </div>

      <button
        onClick={() =>
          setMapStyleType((prev) =>
            prev === "streets" ? "satellite" : "streets",
          )
        }
        className="absolute bottom-6 left-6 z-20 rounded-full border border-white/10 bg-slate-950/80 px-4 py-2 text-xs font-semibold text-white backdrop-blur transition hover:bg-slate-800/90"
      >
        {mapStyleType === "streets" ? "Satellite" : "Streets"}
      </button>

      {weather && (
        <div className="absolute top-6 right-6 z-20 w-72 rounded-xl border border-cyan-300/20 bg-slate-950/90 p-4 text-sm text-white shadow-2xl backdrop-blur">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">
              Weather
            </span>
            <button
              onClick={() => setClickedCoords(null)}
              className="text-slate-400 transition hover:text-white"
            >
              X
            </button>
          </div>
          {weather.current ? (
            <div className="space-y-1">
              <div>
                Temperature:{" "}
                <span className="font-mono text-cyan-100">
                  {(weather.current as Record<string, unknown>)?.temperature_2m as string ?? "--"}°C
                </span>
              </div>
              <div>
                Humidity:{" "}
                <span className="font-mono text-cyan-100">
                  {(weather.current as Record<string, unknown>)?.relative_humidity_2m as string ?? "--"}%
                </span>
              </div>
              <div>
                Wind:{" "}
                <span className="font-mono text-cyan-100">
                  {(weather.current as Record<string, unknown>)?.wind_speed_10m as string ?? "--"} km/h
                </span>
              </div>
            </div>
          ) : (
            <div className="text-slate-400">Loading weather data...</div>
          )}
        </div>
      )}

      {mapError && (
        <div className="absolute bottom-4 left-1/2 z-20 w-[min(32rem,calc(100vw-2rem))] -translate-x-1/2 rounded-xl border border-amber-400/40 bg-slate-950/90 px-4 py-3 text-sm text-slate-100 shadow-2xl backdrop-blur">
          <div className="font-semibold text-amber-300">Map loading issue</div>
          <div className="mt-1 text-slate-300">{mapError}</div>
          <div className="mt-2 text-xs text-slate-400">
            If you use a content blocker, allow the map domain for this page and refresh.
          </div>
        </div>
      )}
    </div>
  );
}
