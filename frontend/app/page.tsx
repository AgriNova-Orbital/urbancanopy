import MapViewer from "../components/MapViewer";
import Sidebar from "../components/Sidebar";

export default function Home() {
  return (
    <main className="relative flex h-screen w-full bg-slate-900">
      <MapViewer />
      <Sidebar />
    </main>
  );
}
