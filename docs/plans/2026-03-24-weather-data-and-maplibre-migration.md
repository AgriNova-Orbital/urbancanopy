# Weather Data and MapLibre Migration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate the frontend map from Mapbox to MapLibre using OpenStreetMap tiles (with a satellite/street toggle), and add a local Next.js API route to fetch open weather data (historical and current) from Open-Meteo when the user clicks the map.

**Architecture:** 
1. The frontend map will be powered by `maplibre-gl` and `react-map-gl/maplibre`, using free OSM raster tiles and a public imagery basemap (Esri World Imagery or similar open equivalent) without requiring an API key. 
2. A new Next.js App Router API endpoint (`/api/weather`) will proxy requests to the Open-Meteo API. This hides the provider details, enables local caching if needed, and avoids CORS/mixed-content issues on the client.
3. The frontend `MapViewer` will capture map clicks, query the new API endpoint with coordinates, and display a weather summary panel showing current temperature, humidity, and simple historical trends.

**Tech Stack:** Next.js (App Router), React, `maplibre-gl`, `react-map-gl`, `lucide-react`, Open-Meteo API

---

### Task 1: Swap Mapbox for MapLibre

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/app/layout.tsx`

**Step 1: Write the failing test (mental check)**
`mapbox-gl` is in `package.json` and its CSS is imported in `layout.tsx`. We need `maplibre-gl` instead.

**Step 2: Run test to verify it fails**
Run: `cat frontend/package.json | grep maplibre-gl`
Expected: empty

**Step 3: Write minimal implementation**
Uninstall mapbox and install maplibre:
```bash
cd frontend
npm uninstall mapbox-gl @types/mapbox-gl
npm install maplibre-gl
npm install -D @types/maplibre-gl
```

Update `frontend/app/layout.tsx` to use MapLibre CSS instead of Mapbox:
```tsx
import "./globals.css";
import "maplibre-gl/dist/maplibre-gl.css";

export const metadata = {
  title: "Urban Canopy Pipeline",
  description: "Cross-city urban cooling analysis",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

**Step 4: Run test to verify it passes**
Run: `npm run build` inside `frontend/` (Note: ignore the Next.js/Node 25 runtime bug if it occurs during build, just verify tsc passes: `npx tsc --noEmit`)

**Step 5: Commit**
```bash
git add frontend/package.json frontend/package-lock.json frontend/app/layout.tsx
git commit -m "chore: swap mapbox for maplibre-gl"
```

### Task 2: Migrate MapViewer to MapLibre and OpenStreetMap

**Files:**
- Modify: `frontend/components/MapViewer.tsx`

**Step 1: Write the failing test**
Run: `npx tsc --noEmit` inside `frontend/` after changing imports in Step 3.

**Step 2: Run test to verify it fails**
Expected: import errors if we miss changing `react-map-gl` to `react-map-gl/maplibre`.

**Step 3: Write minimal implementation**
Modify `frontend/components/MapViewer.tsx`:
- Change `import Map, { ... } from "react-map-gl";` to `import Map, { ... } from "react-map-gl/maplibre";`.
- Remove `mapboxAccessToken` and the `mapboxToken` check/warning UI entirely.
- Add a state for `mapStyleType`: `const [mapStyleType, setMapStyleType] = useState<"streets" | "satellite">("streets");`.
- Add a toggle button in the UI to switch `mapStyleType`.
- Define minimal inline map styles for raster tiles:
```tsx
const streetStyle = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap Contributors",
    },
  },
  layers: [
    {
      id: "osm-tiles",
      type: "raster",
      source: "osm",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

const satelliteStyle = {
  version: 8,
  sources: {
    esri: {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
      attribution: "&copy; Esri",
    },
  },
  layers: [
    {
      id: "satellite-tiles",
      type: "raster",
      source: "esri",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};
```
- Set `mapStyle={mapStyleType === "streets" ? streetStyle : satelliteStyle}`.

**Step 4: Run test to verify it passes**
Run: `npx tsc --noEmit` inside `frontend/`

**Step 5: Commit**
```bash
git add frontend/components/MapViewer.tsx
git commit -m "feat: use MapLibre with OSM and Esri raster tiles"
```

### Task 3: Create Next.js API Route for Weather

**Files:**
- Create: `frontend/app/api/weather/route.ts`

**Step 1: Write the failing test**
Run: `curl -s http://localhost:3000/api/weather?lat=25.03&lon=121.5`

**Step 2: Run test to verify it fails**
Expected: 404 Not Found (or connection refused if dev server not running).

**Step 3: Write minimal implementation**
Create `frontend/app/api/weather/route.ts`:
```tsx
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const lat = searchParams.get("lat");
  const lon = searchParams.get("lon");

  if (!lat || !lon) {
    return NextResponse.json({ error: "Missing lat or lon parameters" }, { status: 400 });
  }

  try {
    // Fetch current weather and 7 days of historical temperature data
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&past_days=7&daily=temperature_2m_max,temperature_2m_min&timezone=auto`;
    const response = await fetch(url, { next: { revalidate: 3600 } }); // cache for 1 hour
    
    if (!response.ok) {
      throw new Error(`Open-Meteo returned ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Weather API error:", error);
    return NextResponse.json({ error: "Failed to fetch weather data" }, { status: 502 });
  }
}
```

**Step 4: Run test to verify it passes**
Run: `npx tsc --noEmit` inside `frontend/`

**Step 5: Commit**
```bash
git add frontend/app/api/weather/route.ts
git commit -m "feat: add Next.js API route for Open-Meteo weather data"
```

### Task 4: Add Weather Panel UI on Map Click

**Files:**
- Modify: `frontend/components/MapViewer.tsx`

**Step 1: Write the failing test (mental check)**
The map click handler currently selects priority zones but does not fetch weather data.

**Step 2: Run test to verify it fails**
Visual check: Clicking the map doesn't show a weather panel.

**Step 3: Write minimal implementation**
Modify `frontend/components/MapViewer.tsx`:
- Add a new state: `const [weather, setWeather] = useState<any>(null);`
- Add a new state for coordinates: `const [clickedCoords, setClickedCoords] = useState<{lat: number, lon: number} | null>(null);`
- In `onMapClick`, extract the coordinates:
```tsx
const onMapClick = useCallback((event: MapLayerMouseEvent) => {
  const { lngLat } = event;
  setClickedCoords({ lat: lngLat.lat, lon: lngLat.lng });
  
  // also keep the existing zone selection logic if a feature is clicked
  const feature = event.features?.[0] as any;
  const zoneId = typeof feature?.properties?.zone_id === "string" ? feature.properties.zone_id : null;
  onZoneSelect(zoneId);
}, [onZoneSelect]);
```
- Add a `useEffect` to fetch weather when `clickedCoords` changes:
```tsx
useEffect(() => {
  if (!clickedCoords) return;
  let active = true;
  setWeather(null); // loading state
  fetch(`/api/weather?lat=${clickedCoords.lat}&lon=${clickedCoords.lon}`)
    .then(res => res.json())
    .then(data => {
      if (active && !data.error) setWeather(data);
    })
    .catch(err => console.error("Weather fetch failed", err));
  return () => { active = false; };
}, [clickedCoords]);
```
- Add a floating UI panel on top of the map to display the weather data (current temp, humidity, wind) if `weather` is set. Include a close button (`X`) to set `clickedCoords` to `null`.

**Step 4: Run test to verify it passes**
Run: `npx tsc --noEmit` inside `frontend/`

**Step 5: Commit**
```bash
git add frontend/components/MapViewer.tsx
git commit -m "feat: show weather panel on map click"
```
