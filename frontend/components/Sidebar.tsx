"use client";

import { useEffect, useState } from "react";
import Papa from "papaparse";
import { ThermometerSun, Leaf, Building2 } from "lucide-react";

type CitySignature = {
  city: string;
  heat_gap_c: number;
  mean_ndvi: number;
  mean_ndbi: number;
  signature_score: number;
};

export default function Sidebar() {
  const [signatures, setSignatures] = useState<CitySignature[]>([]);

  useEffect(() => {
    fetch("/data/city_signature.csv")
      .then(res => res.text())
      .then(csv => {
        const parsed = Papa.parse<CitySignature>(csv, { header: true, dynamicTyping: true });
        if (parsed.data) {
          // Filter out empty rows
          setSignatures(parsed.data.filter(d => d.city));
        }
      })
      .catch(err => console.error("Failed to load CSV", err));
  }, []);

  return (
    <div className="absolute top-4 left-4 z-10 w-80 bg-slate-900/90 p-6 rounded-lg border border-slate-700 shadow-xl text-white backdrop-blur-sm max-h-[90vh] overflow-y-auto">
      <h1 className="text-xl font-bold mb-1">Urban Canopy</h1>
      <p className="text-sm text-slate-400 mb-6">Cross-city cooling analysis</p>

      <div className="space-y-4">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">City Signatures</h2>
        
        {signatures.length === 0 ? (
          <p className="text-sm text-slate-500">Loading signatures or run `make data` first...</p>
        ) : (
          signatures.map((sig) => (
            <div key={sig.city} className="bg-slate-800 p-4 rounded-md border border-slate-700">
              <div className="flex justify-between items-center mb-2">
                <span className="font-medium capitalize">{sig.city.replace("_", " ")}</span>
                <span className="text-xs bg-slate-700 px-2 py-1 rounded text-slate-300">
                  Score: {sig.signature_score?.toFixed(2)}
                </span>
              </div>
              
              <div className="space-y-2 text-sm text-slate-400">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2"><ThermometerSun size={14} className="text-orange-400"/> Heat Gap</span>
                  <span className="font-mono text-slate-200">{sig.heat_gap_c?.toFixed(1)}°C</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2"><Leaf size={14} className="text-green-400"/> Mean NDVI</span>
                  <span className="font-mono text-slate-200">{sig.mean_ndvi?.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-2"><Building2 size={14} className="text-slate-400"/> Mean NDBI</span>
                  <span className="font-mono text-slate-200">{sig.mean_ndbi?.toFixed(2)}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
