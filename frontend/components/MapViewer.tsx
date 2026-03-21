"use client";

import { useEffect, useState, useRef } from "react";
import Map, { NavigationControl, Source, Layer, FillLayer, MapRef } from "react-map-gl";
import bbox from "@turf/bbox";
import "mapbox-gl/dist/mapbox-gl.css";

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

export default function MapViewer() {
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
  const [geoData, setGeoData] = useState<any>(null);
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
      .catch(err => console.log("Failed to load priority zones", err));
  }, []);

  if (!mapboxToken) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-900 text-white">
        <div className="bg-red-900/50 border border-red-500 p-6 rounded-lg max-w-md text-center">
          <h2 className="text-xl font-bold mb-2">Missing Mapbox Token</h2>
          <p>Please ensure <code className="bg-slate-800 px-1 rounded">NEXT_PUBLIC_MAPBOX_TOKEN</code> is set in your <code className="bg-slate-800 px-1 rounded">.env.local</code> file to view the satellite map.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 w-screen h-screen">
      <Map
        ref={mapRef}
        mapboxAccessToken={mapboxToken}
        initialViewState={{
          longitude: 121.5, // Default Taipei
          latitude: 25.03,
          zoom: 11
        }}
        mapStyle="mapbox://styles/mapbox/dark-v11"
        style={{ width: "100%", height: "100%" }}
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
