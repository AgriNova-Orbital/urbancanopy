"use client";

import { useEffect, useState, useRef } from "react";
import Map, { NavigationControl, Source, Layer, FillLayer, MapRef } from "react-map-gl/maplibre";
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

export default function MapViewer() {
  const [geoData, setGeoData] = useState<any>(null);
  const [mapStyleType, setMapStyleType] = useState<"streets" | "satellite">("streets");
  const mapRef = useRef<MapRef>(null);

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

      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 121.5, // Default Taipei
          latitude: 25.03,
          zoom: 11
        }}
        mapStyle={mapStyleType === "streets" ? (streetStyle as any) : (satelliteStyle as any)}
        style={{ width: "100%", height: "100%" }}
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