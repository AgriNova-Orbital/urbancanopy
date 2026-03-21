"use client";

import { useEffect, useState } from "react";
import Map, { NavigationControl, Source, Layer, FillLayer } from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";

const INITIAL_VIEW_STATE = {
  longitude: 121.5,
  latitude: 25.03,
  zoom: 11,
  pitch: 0,
  bearing: 0
};

const priorityLayerStyle: FillLayer = {
  id: "priority-zones",
  type: "fill",
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

  useEffect(() => {
    fetch("/data/priority_zones.geojson")
      .then(res => {
        if (!res.ok) throw new Error("No data");
        return res.json();
      })
      .then(data => setGeoData(data))
      .catch(err => console.log("Failed to load priority zones", err));
  }, []);

  return (
    <div className="absolute inset-0 w-full h-full">
      <Map
        mapboxAccessToken={mapboxToken}
        initialViewState={INITIAL_VIEW_STATE}
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
