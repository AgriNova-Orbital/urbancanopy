import MapViewer from "../components/MapViewer";

export default function Home() {
  return (
    <main className="relative flex h-screen w-full bg-slate-900">
      <MapViewer />
      
      {/* Absolute positioned UI overlay will go here */}
      <div className="absolute top-4 left-4 z-10 w-80 bg-slate-900/90 p-6 rounded-lg border border-slate-700 shadow-xl text-white backdrop-blur-sm">
        <h1 className="text-xl font-bold mb-2">Urban Canopy</h1>
        <p className="text-sm text-slate-300">Planting priority and heat gap analysis.</p>
      </div>
    </main>
  );
}
