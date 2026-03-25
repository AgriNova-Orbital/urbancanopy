"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Sidebar from "../components/Sidebar";

const OperationsStatus = dynamic(
  () => import("../components/OperationsStatus"),
  { ssr: false },
);

const MapViewer = dynamic(() => import("../components/MapViewer"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 flex items-center justify-center bg-slate-950 text-slate-300">
      Loading map workspace...
    </div>
  ),
});

export default function Home() {
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);

  return (
    <main className="relative flex h-screen w-full overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.12),_rgba(15,23,42,0.96)_35%,_rgba(2,6,23,1)_100%)] text-slate-50">
      <MapViewer selectedZoneId={selectedZoneId} onZoneSelect={setSelectedZoneId} />
      <Sidebar selectedZoneId={selectedZoneId} />
      <OperationsStatus />
    </main>
  );
}
