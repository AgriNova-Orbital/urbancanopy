"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import Map, { NavigationControl, Source, Layer, FillLayer, MapRef, MapLayerMouseEvent } from "react-map-gl/maplibre";
import bbox from "@turf/bbox";
import "maplibre-gl/dist/maplibre-gl.css";

import { reportFrontendRuntimeIssue } from "./FrontendLogger";

const priorityLayerStyle: FillLayer = {
  id: "priority-zones",
  type: "fill",
  source: "priority-data",
  paint: {
    "fill-color": [
      "interpolate",
      ["linear"],
      ["get", "priority_score"],
      0.0, "#fde047", // yellow-300
      0.5, "#f97316", // orange-500
      1.0, "#b91c1c"  // red-700
    ],
    "fill-opacity": 0.6
  }
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

export default function MapViewer({ onZoneSelect = () => {} }: { onZoneSelect?: (id: string | null) => void } = {}) {
  const [geoData, setGeoData] = useState<any>(null);
  const [mapStyleType, setMapStyleType] = useState<"streets" | "satellite">("streets");
  const mapRef = useRef<MapRef>(null);

  const [weather, setWeather] = useState<any>(null);
  const [clickedCoords, setClickedCoords] = useState<{lat: number, lon: number} | null>(null);

  const onMapClick = useCallback((event: MapLayerMouseEvent) => {
    const { lngLat } = event;
    setClickedCoords({ lat: lngLat.lat, lon: lngLat.lng });
    
    // also keep the existing zone selection logic if a feature is clicked
    const feature = event.features?.[0] as any;
    const zoneId = typeof feature?.properties?.zone_id === "string" ? feature.properties.zone_id : null;
    onZoneSelect(zoneId);
  }, [onZoneSelect]);

  useEffect(() => {
    if (!clickedCoords) return;
    let active = true;
    setWeather(null); // loading state
    fetch(`/api/weather?lat=${clickedCoords.lat}&lon=${clickedCoords.lon}`)
      .then(res => res.json())
      .then(data => {
        if (active && !data.error) setWeather(data);
      })
      .catch(err => console.error("Weather fetch failed", err));
    return () => { active = false; };
  }, [clickedCoords]);

  useEffect(() => {
    fetch("/data/priority_zones.geojson")
      .then(res => {
        if (!res.ok) throw new Error("No data");
        return res.json();
      })
      .then(data => {
        setGeoData(data);
        if (data.features && data.features.length > 0 && mapRef.current) {
          const [minLng, minLat, maxLng, maxLat] = bbox(data);
          mapRef.current.fitBounds(
            [[minLng, minLat], [maxLng, maxLat]],
            { padding: 80, duration: 1500 }
          );
        }
      })
      .catch(err => {
        reportFrontendRuntimeIssue("error", "ui.map.error", "Failed to load priority zones", {
          source: "priority_zones.geojson",
          error: err instanceof Error ? err.message : String(err),
        });
      });
  }, []);

  return (
    <div className="absolute inset-0 w-screen h-screen">
      <button
        onClick={() => setMapStyleType(prev => prev === "streets" ? "satellite" : "streets")}
        className="absolute bottom-6 left-6 z-20 bg-slate-900 text-white px-3 py-1 rounded"
      >
        Toggle Style ({mapStyleType})
      </button>

      {clickedCoords && (
        <div className="absolute top-6 right-6 z-20 bg-slate-900 text-white p-4 rounded shadow-2xl backdrop-blur border border-white/10 max-w-sm">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-lg">Weather Data</h3>
            <button
              onClick={() => setClickedCoords(null)}
              className="text-gray-400 hover:text-white font-bold ml-4"
              aria-label="Close"
            >
              X
            </button>
          </div>
          {!weather ? (
            <p className="text-sm text-gray-300">Loading weather data...</p>
          ) : (
            <div className="space-y-1 text-sm">
              <p><span className="text-gray-400">Temp:</span> {weather.current?.temperature_2m}°C</p>
              <p><span className="text-gray-400">Humidity:</span> {weather.current?.relative_humidity_2m}%</p>
              <p><span className="text-gray-400">Wind:</span> {weather.current?.wind_speed_10m} km/h</p>
              {weather.historical && (
                <div className="mt-2 pt-2 border-t border-gray-700">
                  <p className="text-xs text-gray-400 font-medium mb-1">Historical Averages</p>
                  <p>Max Temp: {weather.historical.temperature_2m_max_mean?.toFixed(1)}°C</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 121.5, // Default Taipei
          latitude: 25.03,
          zoom: 11
        }}
        mapStyle={mapStyleType === "streets" ? (streetStyle as any) : (satelliteStyle as any)}
        style={{ width: "100%", height: "100%" }}
        onClick={onMapClick}
        interactiveLayerIds={["priority-zones"]}
        onError={(event) => {
          reportFrontendRuntimeIssue("error", "ui.map.error", "MapLibre runtime error", {
            error: event.error?.message ?? "Unknown MapLibre error",
          });
        }}
      >
        <NavigationControl position="bottom-right" />
        
        {geoData && (
          <Source id="priority-data" type="geojson" data={geoData}>
            <Layer {...priorityLayerStyle} />
          </Source>
        )}
      </Map>
    </div>
  );
}