"use client";

import {
  Cloud,
  ThermometerSun,
  MapPin,
  ChevronRight,
  Bot,
  User,
  Flame,
} from "lucide-react";

type HotspotRow = {
  zoneId: string;
  location: string;
  maxTempC: number;
};

type TempBar = {
  label: string;
  value: number;
  max: number;
  color: string;
};

const HOTSPOT_DATA: HotspotRow[] = [
  { zoneId: "HE-03", location: "Xinyi Commercial", maxTempC: 52 },
  { zoneId: "NT-07", location: "Neihu Tech Park", maxTempC: 48 },
  { zoneId: "TP-11", location: "Taipei Main Station", maxTempC: 46 },
  { zoneId: "DT-01", location: "Daan Forest Park", maxTempC: 34 },
];

const TEMPERATURE_BARS: TempBar[] = [
  { label: "Xinyi Commercial", value: 52, max: 60, color: "#ef4444" },
  { label: "Neihu Tech Park", value: 48, max: 60, color: "#f97316" },
  { label: "Taipei Main Station", value: 46, max: 60, color: "#f59e0b" },
  { label: "Daan Forest Park", value: 34, max: 60, color: "#22c55e" },
  { label: "Zhongshan District", value: 41, max: 60, color: "#eab308" },
];

const SUGGESTIONS = [
  "Increase public cooling center hours",
  "Deploy water mist stations in Xinyi",
  "Activate emergency shade net program",
  "Open school gyms for heat refuge",
];

export default function RightPanel() {
  return (
    <aside className="pointer-events-auto absolute right-4 top-4 z-10 flex h-[calc(100vh-2rem)] w-[22rem] flex-col gap-4 overflow-hidden rounded-3xl border border-white/10 bg-slate-950/85 px-5 py-5 shadow-[0_20px_80px_rgba(2,6,23,0.55)] backdrop-blur-xl">
      {/* User / Top Bar */}
      <div className="flex items-center gap-3 rounded-2xl border border-white/5 bg-white/4 p-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-cyan-400/15 text-cyan-300">
          <User size={18} />
        </div>
        <div>
          <div className="text-sm font-semibold text-white">System Operator</div>
          <div className="text-xs text-slate-400">Urban Canopy Dashboard</div>
        </div>
      </div>

      {/* LLM Decision Support */}
      <div className="space-y-3 rounded-2xl border border-white/5 bg-white/4 p-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-400/15 text-violet-300">
            <Bot size={16} />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-violet-200">
              LLM Decision Support
            </div>
          </div>
        </div>
        <p className="text-xs leading-relaxed text-slate-400">
          We integrate an LLM-based decision support module to evaluate heat exposure conditions
          and recommend operational responses for urban heat mitigation.
        </p>
        <div className="space-y-1.5">
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Real-Condition Response Suggestions
          </div>
          {SUGGESTIONS.map((suggestion) => (
            <div
              key={suggestion}
              className="flex items-center gap-2 rounded-lg bg-violet-500/8 px-3 py-1.5 text-xs text-violet-200"
            >
              <ChevronRight size={12} />
              {suggestion}
            </div>
          ))}
        </div>
      </div>

      {/* Surface Temperature Distribution */}
      <div className="space-y-3 rounded-2xl border border-white/5 bg-white/4 p-4">
        <div className="flex items-center gap-2">
          <ThermometerSun size={14} className="text-amber-300" />
          <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-300">
            City Surface Temperature Distribution
          </div>
        </div>
        <div className="space-y-3">
          {TEMPERATURE_BARS.map((bar) => (
            <div key={bar.label} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-300">{bar.label}</span>
                <span
                  className="font-mono font-semibold"
                  style={{ color: bar.color }}
                >
                  {bar.value}°C
                </span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-white/6">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${(bar.value / bar.max) * 100}%`,
                    background: `linear-gradient(90deg, ${bar.color}88, ${bar.color})`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Hotspot Priority */}
      <div className="space-y-3 rounded-2xl border border-white/5 bg-white/4 p-4">
        <div className="flex items-center gap-2">
          <Flame size={14} className="text-red-400" />
          <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-300">
            Hotspot Priority
          </div>
        </div>
        <div className="overflow-hidden rounded-xl border border-white/5">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/5 bg-white/4 text-left text-slate-400">
                <th className="px-3 py-2 font-medium">Zone ID</th>
                <th className="px-3 py-2 font-medium">Location</th>
                <th className="px-3 py-2 text-right font-medium">Max Temp</th>
              </tr>
            </thead>
            <tbody>
              {HOTSPOT_DATA.map((row) => (
                <tr
                  key={row.zoneId}
                  className="border-t border-white/5 hover:bg-white/4"
                >
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <MapPin size={12} className="text-cyan-300" />
                      <span className="font-mono text-slate-200">{row.zoneId}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-slate-300">{row.location}</td>
                  <td
                    className="px-3 py-2 text-right font-mono font-semibold"
                    style={{
                      color:
                        row.maxTempC >= 50
                          ? "#ef4444"
                          : row.maxTempC >= 40
                            ? "#f97316"
                            : "#22c55e",
                    }}
                  >
                    {row.maxTempC}°C
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </aside>
  );
}
