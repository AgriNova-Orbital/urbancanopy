"use client";

import { useEffect, useMemo, useState } from "react";
import { Building2, Flame, Leaf, MapPin, TriangleAlert } from "lucide-react";
import {
  getHighestPriorityZone,
  loadDashboardArtifacts,
  type DashboardArtifacts,
  type CityComparisonRow,
  type CitySignatureRow,
  type ParkCoolingRow,
} from "../lib/artifacts";

type SidebarProps = {
  selectedZoneId: string | null;
};

function formatCityName(city: string): string {
  return city.replaceAll("_", " ");
}

function sortComparisonRows(rows: CityComparisonRow[]): CityComparisonRow[] {
  return [...rows].sort((left, right) => right.heat_gap_c - left.heat_gap_c);
}

function sortSignatures(rows: CitySignatureRow[]): CitySignatureRow[] {
  return [...rows].sort((left, right) => right.signature_score - left.signature_score);
}

function topParkRows(rows: ParkCoolingRow[]): ParkCoolingRow[] {
  return [...rows].sort((left, right) => right.delta_lst_c - left.delta_lst_c);
}

export default function Sidebar({ selectedZoneId }: SidebarProps) {
  const [artifacts, setArtifacts] = useState<DashboardArtifacts>({
    priorityZones: null,
    citySignatures: [],
    cityComparison: [],
    parkCooling: [],
    errors: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    loadDashboardArtifacts()
      .then((result) => {
        if (!active) {
          return;
        }

        setArtifacts(result);
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const rankedCities = useMemo(() => sortSignatures(artifacts.citySignatures), [artifacts.citySignatures]);
  const comparisonRows = useMemo(() => sortComparisonRows(artifacts.cityComparison), [artifacts.cityComparison]);
  const parkRows = useMemo(() => topParkRows(artifacts.parkCooling), [artifacts.parkCooling]);

  const selectedZone =
    artifacts.priorityZones?.features.find((feature) => feature.properties.zone_id === selectedZoneId) ??
    getHighestPriorityZone(artifacts.priorityZones) ??
    null;

  return (
    <aside className="pointer-events-auto absolute left-4 top-4 z-10 flex h-[calc(100vh-2rem)] w-[22rem] flex-col gap-4 overflow-hidden rounded-3xl border border-cyan-200/10 bg-slate-950/85 px-5 py-5 shadow-[0_20px_80px_rgba(2,6,23,0.55)] backdrop-blur-xl">
      <div className="space-y-2 border-b border-white/8 pb-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-100">
          Taipei action map
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">Urban Canopy</h1>
        <p className="text-sm leading-6 text-slate-300">
          Priority zones, city evidence, and park cooling signals in one dashboard.
        </p>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-white/8 bg-white/4 p-4 text-sm text-slate-300">
          Loading local artifacts...
        </div>
      ) : null}

      {artifacts.errors.length > 0 ? (
        <div className="space-y-2 rounded-2xl border border-amber-400/20 bg-amber-400/8 p-4 text-sm text-amber-100">
          <div className="flex items-center gap-2 font-semibold text-amber-200">
            <TriangleAlert size={16} /> Data notice
          </div>
          <ul className="space-y-1 text-amber-50/80">
            {artifacts.errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <section className="space-y-3 rounded-2xl border border-white/8 bg-white/4 p-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100/80">
          <MapPin size={14} /> Selected zone
        </div>
        {selectedZone ? (
          <div className="space-y-2">
            <div className="text-lg font-semibold text-white">{selectedZone.properties.zone_id ?? "Zone"}</div>
            <div className="text-sm text-slate-300">
              Priority score: <span className="font-mono text-cyan-100">{selectedZone.properties.priority_score.toFixed(3)}</span>
            </div>
            <div className="text-sm text-slate-300">
              UTCI level: <span className="font-mono text-cyan-100">{selectedZone.properties.utci_level ?? "unknown"}</span>
            </div>
            <div className="text-sm text-slate-300">
              UTCI ET: <span className="font-mono text-cyan-100">{selectedZone.properties.utci_equivalent_temperature?.toFixed(1) ?? "--"} degC</span>
            </div>
            <div className="text-xs text-slate-400">
              Priority now follows the UTCI equivalent-temperature bands from the thermal index reference.
            </div>
          </div>
        ) : (
          <div className="text-sm text-slate-400">No zone selected yet.</div>
        )}
      </section>

      <section className="space-y-3 rounded-2xl border border-white/8 bg-white/4 p-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100/80">
          <Flame size={14} /> City comparison
        </div>
        <div className="space-y-2">
          {comparisonRows.map((row, index) => (
            <div key={row.city} className="flex items-center justify-between rounded-xl bg-slate-900/70 px-3 py-2">
              <div>
                <div className="text-sm font-medium text-white">{formatCityName(row.city)}</div>
                <div className="text-xs text-slate-400">Rank #{index + 1}</div>
              </div>
              <div className="font-mono text-sm text-cyan-100">{row.heat_gap_c.toFixed(1)}°C</div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3 rounded-2xl border border-white/8 bg-white/4 p-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100/80">
          <Leaf size={14} /> City signatures
        </div>
        <div className="space-y-2">
          {rankedCities.map((row) => (
            <div key={row.city} className="rounded-xl bg-slate-900/70 px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-white">{formatCityName(row.city)}</div>
                <div className="font-mono text-sm text-cyan-100">{row.signature_score.toFixed(2)}</div>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/8">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-300 via-teal-300 to-amber-300"
                  style={{ width: `${Math.max(8, row.signature_score * 100)}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                <span>Heat gap {row.heat_gap_c.toFixed(1)}°C</span>
                <span>NDVI {row.mean_ndvi.toFixed(2)} • NDBI {row.mean_ndbi.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3 rounded-2xl border border-white/8 bg-white/4 p-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-100/80">
          <Building2 size={14} /> Park cooling
        </div>
        <div className="space-y-2">
          {parkRows.map((row) => (
            <div key={row.park_id} className="rounded-xl bg-slate-900/70 px-3 py-2 text-sm text-slate-200">
              <div className="flex items-center justify-between">
                <span className="font-medium text-white">{row.park_id}</span>
                <span className="font-mono text-cyan-100">{row.delta_lst_c.toFixed(1)}°C</span>
              </div>
              <div className="mt-1 text-xs text-slate-400">
                CI {row.ci_low_c.toFixed(1)}°C to {row.ci_high_c.toFixed(1)}°C
              </div>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}
