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
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "pk.eyJ1IjoibW9jay10b2tlbiJ9.mock";
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
          // Calculate bounding box [minX, minY, maxX, maxY]
          const [minLng, minLat, maxLng, maxLat] = bbox(data);
          mapRef.current.fitBounds(
            [
              [minLng, minLat],
              [maxLng, maxLat]
            ],
            { padding: 80, duration: 1500 } // Swoop in over 1.5 seconds!
          );
        }
      })
      .catch(err => console.log("Failed to load priority zones", err));
  }, []);

  return (
    <div className="absolute inset-0 w-full h-full">
      <Map
        ref={mapRef}
        mapboxAccessToken={mapboxToken}
        initialViewState={{
          longitude: 0,
          latitude: 0,
          zoom: 1
        }}
        mapStyle="mapbox://styles/mapbox/dark-v11"
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
