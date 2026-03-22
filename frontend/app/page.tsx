import MapViewer from "../components/MapViewer";
import Sidebar from "../components/Sidebar";

export default function Home() {
  return (
    <main className="relative flex min-h-screen w-full overflow-hidden bg-slate-900">
      <MapViewer />
      <Sidebar />
    </main>
  );
}
