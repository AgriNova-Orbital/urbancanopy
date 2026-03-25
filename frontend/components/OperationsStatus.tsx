"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { createFrontendLogger, type FrontendLogger } from "../lib/logger";
import { createLogStore } from "../lib/log-store";
import {
  DEFAULT_REFRESH_INTERVAL,
  REFRESH_INTERVAL_OPTIONS,
  normalizeOperationsMode,
  normalizeOperationsSnapshot,
  parseOperationsSsePayload,
  refreshIntervalToMs,
  readRefreshIntervalPreference,
  resolveDisplayedQueueSize,
  type OperationsEvent,
  type OperationsMode,
  type OperationsSnapshot,
  type RefreshIntervalValue,
  writeRefreshIntervalPreference,
} from "../lib/operations-status";

const EVENT_FEED_LIMIT = 8;

const EMPTY_SNAPSHOT: OperationsSnapshot = {
  mode: "offline",
  lastUpdatedAt: null,
  queueSize: 0,
  events: [],
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function mergeEvents(previousEvents: OperationsEvent[], incomingEvents: OperationsEvent[]): OperationsEvent[] {
  const entries = [...incomingEvents, ...previousEvents];
  const seen = new Set<string>();
  const merged: OperationsEvent[] = [];

  for (const event of entries) {
    const key = `${event.ts}:${event.event}:${event.component}:${event.message}`;

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    merged.push(event);
  }

  return merged
    .sort((left, right) => right.ts.localeCompare(left.ts))
    .slice(0, EVENT_FEED_LIMIT);
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "Waiting for first update";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return "Waiting for first update";
  }

  return parsed.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function modeClasses(mode: OperationsMode): string {
  if (mode === "online") {
    return "bg-emerald-500/15 text-emerald-300 border border-emerald-400/30";
  }

  if (mode === "degraded") {
    return "bg-amber-500/15 text-amber-300 border border-amber-400/30";
  }

  return "bg-slate-700/60 text-slate-200 border border-slate-600";
}

function modeFromRealtimePayload(payload: unknown, fallback: OperationsMode): OperationsMode {
  if (!isRecord(payload)) {
    return fallback;
  }

  if (payload.fallbackUsed === true) {
    return "degraded";
  }

  if (payload.online === true) {
    return "online";
  }

  if (payload.online === false) {
    return "offline";
  }

  return normalizeOperationsMode(payload.status ?? payload.mode ?? fallback);
}

function fireAndForget(promise: Promise<unknown>): void {
  promise.catch(() => {
    return;
  });
}

export default function OperationsStatus() {
  const storeRef = useRef(createLogStore());
  const loggerRef = useRef<FrontendLogger | null>(null);
  const intervalInitializedRef = useRef(false);
  const [snapshot, setSnapshot] = useState<OperationsSnapshot>(EMPTY_SNAPSHOT);
  const [localQueueSize, setLocalQueueSize] = useState(storeRef.current.size());
  const [hasAuthoritativeRemoteQueue, setHasAuthoritativeRemoteQueue] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState<RefreshIntervalValue>(DEFAULT_REFRESH_INTERVAL);
  const [browserOnline, setBrowserOnline] = useState<boolean>(true);
  const [transport, setTransport] = useState<"sse" | "polling">("polling");
  const [clientReady, setClientReady] = useState(false);

  const ensureLogger = useCallback(() => {
    if (!loggerRef.current) {
      loggerRef.current = createFrontendLogger({
        component: "frontend.operations",
        mode: "browser",
        store: storeRef.current,
      });
    }

    return loggerRef.current;
  }, []);

  const syncLocalQueueSize = useCallback(() => {
    setLocalQueueSize(storeRef.current.size());
  }, []);

  const loadStatus = useCallback(async () => {
    syncLocalQueueSize();

    try {
      const response = await fetch("/api/status", { cache: "no-store" });

      if (!response.ok) {
        throw new Error(`status request failed: ${response.status}`);
      }

      const nextSnapshot = normalizeOperationsSnapshot(await response.json());
      setHasAuthoritativeRemoteQueue(true);
      setSnapshot((previous) => ({
        ...nextSnapshot,
        events: mergeEvents(previous.events, nextSnapshot.events),
      }));
    } catch {
      setSnapshot((previous) => ({
        ...previous,
        mode: browserOnline ? "degraded" : "offline",
      }));
    }
  }, [browserOnline, syncLocalQueueSize]);

  useEffect(() => {
    if (typeof navigator !== "undefined") {
      setBrowserOnline(navigator.onLine);
    }

    if (typeof window !== "undefined") {
      setRefreshInterval(readRefreshIntervalPreference(window.localStorage));
    }

    void loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    writeRefreshIntervalPreference(refreshInterval, window.localStorage);

    if (!intervalInitializedRef.current) {
      intervalInitializedRef.current = true;
      return;
    }

    fireAndForget(
      ensureLogger().info("refresh.interval.changed", "Refresh interval updated", {
        interval: refreshInterval,
      }),
    );
    syncLocalQueueSize();
  }, [ensureLogger, refreshInterval, syncLocalQueueSize]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const handleConnectivityChange = () => {
      const online = window.navigator.onLine;
      setBrowserOnline(online);
      setSnapshot((previous) => ({
        ...previous,
        mode: online ? previous.mode : "offline",
      }));
      fireAndForget(
        ensureLogger().info("connectivity.changed", online ? "Browser connection restored" : "Browser connection lost", {
          online,
        }),
      );
      syncLocalQueueSize();

      if (!online) {
        setTransport("polling");
      }
    };

    window.addEventListener("online", handleConnectivityChange);
    window.addEventListener("offline", handleConnectivityChange);

    return () => {
      window.removeEventListener("online", handleConnectivityChange);
      window.removeEventListener("offline", handleConnectivityChange);
    };
  }, [ensureLogger, syncLocalQueueSize]);

  useEffect(() => {
    if (!browserOnline || typeof EventSource !== "function") {
      setTransport("polling");
      return;
    }

    const source = new EventSource("/api/events/stream");

    source.addEventListener("open", () => {
      setTransport("sse");
    });

    source.addEventListener("status", (event) => {
      const payload = parseOperationsSsePayload((event as MessageEvent<string>).data);

      if (!payload) {
        return;
      }

      setSnapshot((previous) => ({
        ...previous,
        mode: normalizeOperationsMode(payload.status ?? payload.mode),
        queueSize: typeof payload.queueDepth === "number" ? payload.queueDepth : previous.queueSize,
      }));

      if (typeof payload.queueDepth === "number") {
        setHasAuthoritativeRemoteQueue(true);
      }
    });

    source.addEventListener("event", (event) => {
      const rawPayload = parseOperationsSsePayload((event as MessageEvent<string>).data);

      if (!rawPayload) {
        return;
      }

      const payload = normalizeOperationsSnapshot({
        lastUpdatedAt: isRecord(rawPayload) && typeof rawPayload.ts === "string" ? rawPayload.ts : null,
        queueDepth: typeof rawPayload.queueDepth === "number" ? rawPayload.queueDepth : snapshot.queueSize,
        events: [rawPayload],
      });

      setSnapshot((previous) => ({
        ...previous,
        mode: modeFromRealtimePayload(rawPayload, previous.mode),
        lastUpdatedAt: payload.events[0]?.ts ?? previous.lastUpdatedAt,
        queueSize: typeof rawPayload.queueDepth === "number" ? rawPayload.queueDepth : previous.queueSize,
        events: mergeEvents(previous.events, payload.events),
      }));

      if (typeof rawPayload.queueDepth === "number") {
        setHasAuthoritativeRemoteQueue(true);
      }
    });

    source.addEventListener("error", () => {
      setTransport("polling");
    });

    return () => {
      source.close();
    };
  }, [browserOnline]);

  const pollIntervalMs = useMemo(() => refreshIntervalToMs(refreshInterval), [refreshInterval]);

  useEffect(() => {
    if (transport === "sse" || pollIntervalMs === null) {
      return;
    }

    void loadStatus();
    const intervalId = window.setInterval(() => {
      void loadStatus();
    }, pollIntervalMs);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [loadStatus, pollIntervalMs, transport]);

  const displayedQueueSize = resolveDisplayedQueueSize(
    snapshot.queueSize,
    localQueueSize,
    hasAuthoritativeRemoteQueue,
  );

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-950/70 p-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Operations Status</h2>
          <p className="mt-1 text-sm text-slate-400">Live operator health, refresh controls, and recent logger activity.</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${modeClasses(snapshot.mode)}`}>
          {snapshot.mode}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-lg bg-slate-900/80 p-3">
          <div className="text-xs uppercase tracking-wide text-slate-500">Last Update</div>
          <div className="mt-1 font-medium text-slate-100">{formatTimestamp(snapshot.lastUpdatedAt)}</div>
        </div>
        <div className="rounded-lg bg-slate-900/80 p-3">
          <div className="text-xs uppercase tracking-wide text-slate-500">Queue Size</div>
          <div className="mt-1 font-medium text-slate-100">{displayedQueueSize}</div>
        </div>
        <div className="rounded-lg bg-slate-900/80 p-3">
          <div className="text-xs uppercase tracking-wide text-slate-500">Refresh</div>
          <div className="mt-1 font-medium text-slate-100">{refreshInterval}</div>
        </div>
        <div className="rounded-lg bg-slate-900/80 p-3">
          <div className="text-xs uppercase tracking-wide text-slate-500">Transport</div>
          <div className="mt-1 font-medium text-slate-100">{transport === "sse" ? "SSE online" : "Polling fallback"}</div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {REFRESH_INTERVAL_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setRefreshInterval(option.value)}
            className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
              refreshInterval === option.value
                ? "border-emerald-400/50 bg-emerald-500/15 text-emerald-200"
                : "border-slate-700 bg-slate-900/70 text-slate-300 hover:border-slate-500"
            }`}
          >
            {option.label}
          </button>
        ))}
        <button
          type="button"
          onClick={() => {
            void loadStatus();
          }}
          className="rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-500"
        >
          Refresh now
        </button>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Recent Events</h3>
          <span className="text-[11px] uppercase tracking-wide text-slate-500">{transport}</span>
        </div>

        {snapshot.events.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/60 px-3 py-4 text-sm text-slate-500">
            Waiting for backend status events.
          </div>
        ) : (
          <div className="space-y-2">
            {snapshot.events.map((event) => (
              <article key={`${event.ts}:${event.event}:${event.component}`} className="rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-medium text-slate-100">{event.event}</span>
                  <span className="text-[11px] uppercase tracking-wide text-slate-500">{formatTimestamp(event.ts)}</span>
                </div>
                <p className="mt-1 text-sm text-slate-400">{event.message}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
