"use client";

import { useState } from "react";
import Map, { NavigationControl } from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";

// Taipei coordinates roughly
const INITIAL_VIEW_STATE = {
  longitude: 121.5,
  latitude: 25.03,
  zoom: 11,
  pitch: 0,
  bearing: 0
};

export default function MapViewer() {
  // Replace with a real token locally using NEXT_PUBLIC_MAPBOX_TOKEN
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "pk.eyJ1IjoibW9jay10b2tlbiJ9.mock";

  return (
    <div className="absolute inset-0 w-full h-full">
      <Map
        mapboxAccessToken={mapboxToken}
        initialViewState={INITIAL_VIEW_STATE}
        mapStyle="mapbox://styles/mapbox/dark-v11"
      >
        <NavigationControl position="bottom-right" />
      </Map>
    </div>
  );
}
