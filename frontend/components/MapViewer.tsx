"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Map, { Layer, NavigationControl, Source, type FillLayer, type MapLayerMouseEvent, type MapRef } from "react-map-gl";
import bbox from "@turf/bbox";
import { getHighestPriorityZone, loadPriorityZones, type PriorityZonesCollection } from "../lib/artifacts";

type MapViewerProps = {
  selectedZoneId: string | null;
  onZoneSelect: (zoneId: string | null) => void;
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
  const mapboxToken = useMemo(() => {
    const raw = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
    if (!raw) {
      return "";
    }

    return raw.trim().replace(/^['"]|['"]$/g, "");
  }, []);
  const [geoData, setGeoData] = useState<PriorityZonesCollection | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
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
        console.error("Failed to load priority zones", error);
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

  const onMapClick = useCallback(
    (event: MapLayerMouseEvent) => {
      const feature = event.features?.[0] as { properties?: Record<string, unknown> } | undefined;
      const zoneId = typeof feature?.properties?.zone_id === "string" ? feature.properties.zone_id : null;

      onZoneSelect(zoneId);
    },
    [onZoneSelect],
  );

  if (!mapboxToken) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-950 text-white">
        <div className="max-w-md rounded-2xl border border-red-500/40 bg-red-950/50 p-6 text-center shadow-2xl">
          <h2 className="mb-2 text-xl font-bold">Missing Mapbox Token</h2>
          <p>
            Please ensure <code className="rounded bg-slate-900 px-1">NEXT_PUBLIC_MAPBOX_TOKEN</code> is set in your
            <code className="rounded bg-slate-900 px-1">.env.local</code> file to view the map.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 min-h-screen w-screen bg-slate-950">
      <Map
        ref={mapRef}
        mapboxAccessToken={mapboxToken}
        initialViewState={{
          longitude: 121.5,
          latitude: 25.03,
          zoom: 11,
        }}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        interactiveLayerIds={geoData ? ["priority-zones-fill", "priority-zones-selected"] : undefined}
        onLoad={() => {
          setMapReady(true);
          setMapError(null);
        }}
        onError={(event) => {
          console.error("Mapbox runtime error", event.error);
          setMapError(event.error?.message ?? "Interactive map failed to initialize.");
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

      {mapError ? (
        <div className="absolute bottom-4 left-1/2 z-20 w-[min(32rem,calc(100vw-2rem))] -translate-x-1/2 rounded-xl border border-amber-400/40 bg-slate-950/90 px-4 py-3 text-sm text-slate-100 shadow-2xl backdrop-blur">
          <div className="font-semibold text-amber-300">Map loading issue</div>
          <div className="mt-1 text-slate-300">{mapError}</div>
        </div>
      ) : null}
    </div>
  );
}
