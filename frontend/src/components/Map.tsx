"use client";

import { MapContainer, TileLayer, Polygon, Popup, useMap } from "react-leaflet";
import { RegionScore } from "./Dashboard";
import { useEffect } from "react";
import L from "leaflet";

function MapUpdater({ regions }: { regions: RegionScore[] }) {
  const map = useMap();

  useEffect(() => {
    if (regions.length > 0) {
      const allCoords = regions.flatMap(r => 
        r.geometry.coordinates[0].map((coord: number[]) => [coord[1], coord[0]] as [number, number])
      );
      if (allCoords.length > 0) {
        const bounds = L.latLngBounds(allCoords);
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    }
  }, [regions, map]);

  return null;
}

export default function Map({ 
  regions, 
  selectedRegionId,
  onSelectRegion
}: { 
  regions: RegionScore[], 
  selectedRegionId?: string,
  onSelectRegion: (id: string) => void
}) {
  return (
    <MapContainer center={[37.78, -122.41]} zoom={12} scrollWheelZoom={true} className="w-full h-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />
      <MapUpdater regions={regions} />
      
      {regions.map(region => {
        const positions = region.geometry.coordinates[0].map(
          (coord: number[]) => [coord[1], coord[0]] as [number, number]
        );
        
        const isSelected = selectedRegionId === region.id;
        
        // Priority color scale: red for high priority, orange for medium, green for low
        const fillColor = region.priority_score > 70 
          ? "#ef4444" // red
          : region.priority_score > 50 
            ? "#f97316" // orange
            : "#22c55e"; // green

        return (
          <Polygon 
            key={region.id} 
            positions={positions} 
            pathOptions={{ 
              color: isSelected ? "#0f172a" : "#ffffff", 
              weight: isSelected ? 3 : 1,
              fillColor, 
              fillOpacity: isSelected ? 0.8 : 0.6 
            }}
            eventHandlers={{
              click: () => onSelectRegion(region.id)
            }}
          >
            <Popup>
              <div className="font-sans text-sm">
                <h3 className="font-bold text-gray-800 text-base border-b pb-1 mb-1">{region.name}</h3>
                <p className="m-0 text-gray-600">Priority Score: <span className="font-bold text-black">{region.priority_score.toFixed(1)}</span></p>
                <p className="m-0 text-gray-600">Heat Index: {region.heat_score}</p>
                <p className="m-0 text-gray-600">Vegetation Index: {region.vegetation_score}</p>
              </div>
            </Popup>
          </Polygon>
        );
      })}
    </MapContainer>
  );
}
