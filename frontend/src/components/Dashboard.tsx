"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

// Dynamically import map to avoid SSR issues with Leaflet
const Map = dynamic(() => import("./Map"), { ssr: false });

export type RegionScore = {
  id: string;
  name: string;
  heat_score: number;
  vegetation_score: number;
  exposure_score: number;
  priority_score: number;
  recommendation: string;
  geometry: any;
};

export default function Dashboard() {
  const [regions, setRegions] = useState<RegionScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRegion, setSelectedRegion] = useState<RegionScore | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/regions")
      .then((res) => res.json())
      .then((data) => {
        setRegions(data);
        if (data.length > 0) setSelectedRegion(data[0]);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch regions", err);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="p-8 text-center text-gray-500">Loading geospatial data...</div>;

  const avgHeat = Math.round(regions.reduce((acc, r) => acc + r.heat_score, 0) / (regions.length || 1));
  const avgVeg = Math.round(regions.reduce((acc, r) => acc + r.vegetation_score, 0) / (regions.length || 1));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Left panel: Stats & List */}
      <div className="lg:col-span-1 space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">Summary Stats</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-red-50 p-4 rounded text-center">
              <span className="block text-3xl font-bold text-red-600">
                {avgHeat}
              </span>
              <span className="text-sm text-gray-600 font-medium">Avg Heat Index</span>
            </div>
            <div className="bg-green-50 p-4 rounded text-center">
              <span className="block text-3xl font-bold text-green-600">
                {avgVeg}
              </span>
              <span className="text-sm text-gray-600 font-medium">Avg Veg Index</span>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">Priority Areas</h2>
          <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
            {regions.map((region, idx) => (
              <div 
                key={region.id} 
                onClick={() => setSelectedRegion(region)}
                className={`p-3 border rounded cursor-pointer transition-all ${
                  selectedRegion?.id === region.id 
                    ? 'border-green-500 bg-green-50 shadow-sm' 
                    : 'border-gray-200 hover:border-green-300'
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-gray-700">{idx + 1}. {region.name}</span>
                  <span className="bg-emerald-100 text-emerald-800 text-xs px-2.5 py-1 rounded-full font-bold">
                    {region.priority_score.toFixed(1)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {selectedRegion && (
          <div className="bg-white p-6 rounded-lg shadow border-l-4 border-emerald-500">
            <h2 className="text-xl font-bold text-gray-800 mb-3">{selectedRegion.name}</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between border-b pb-1">
                <span className="text-gray-500">Heat Score</span>
                <span className="font-semibold text-red-600">{selectedRegion.heat_score} / 100</span>
              </div>
              <div className="flex justify-between border-b pb-1">
                <span className="text-gray-500">Vegetation Index</span>
                <span className="font-semibold text-green-600">{selectedRegion.vegetation_score} / 100</span>
              </div>
              <div className="flex justify-between border-b pb-1">
                <span className="text-gray-500">Exposure/Population</span>
                <span className="font-semibold text-blue-600">{selectedRegion.exposure_score} / 100</span>
              </div>
              <div className="mt-4 pt-2">
                <strong className="block text-gray-800 mb-1">Recommendation</strong>
                <p className="text-gray-600 italic leading-relaxed">{selectedRegion.recommendation}</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Right panel: Map */}
      <div className="lg:col-span-2 bg-white p-4 rounded-lg shadow min-h-[600px] flex flex-col">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">Priority Heatmap</h2>
        <div className="flex-1 rounded-lg overflow-hidden border border-gray-200">
          <Map 
            regions={regions} 
            selectedRegionId={selectedRegion?.id} 
            onSelectRegion={(id) => setSelectedRegion(regions.find(r => r.id === id) || null)} 
          />
        </div>
      </div>
    </div>
  );
}
