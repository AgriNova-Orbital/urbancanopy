import type { FrontendLogEvent } from "./log-store";

export const REFRESH_INTERVAL_OPTIONS = [
  { value: "5s", label: "5s", ms: 5000 },
  { value: "15s", label: "15s", ms: 15000 },
  { value: "30s", label: "30s", ms: 30000 },
  { value: "1m", label: "1m", ms: 60000 },
  { value: "manual", label: "Manual", ms: null },
] as const;

export type RefreshIntervalValue = (typeof REFRESH_INTERVAL_OPTIONS)[number]["value"];
export type OperationsMode = "online" | "offline" | "degraded";

export interface OperationsEvent {
  ts: string;
  level: FrontendLogEvent["level"];
  event: string;
  component: string;
  message: string;
}

export interface OperationsSnapshot {
  mode: OperationsMode;
  lastUpdatedAt: string | null;
  queueSize: number;
  events: OperationsEvent[];
}

type StorageLike = Pick<Storage, "getItem" | "setItem">;

const REFRESH_INTERVAL_STORAGE_KEY = "urbancanopy.operations.refreshInterval";

export const DEFAULT_REFRESH_INTERVAL: RefreshIntervalValue = "15s";

function isRefreshIntervalValue(value: unknown): value is RefreshIntervalValue {
  return REFRESH_INTERVAL_OPTIONS.some((option) => option.value === value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function readRefreshIntervalPreference(storage?: StorageLike): RefreshIntervalValue {
  const value = storage?.getItem(REFRESH_INTERVAL_STORAGE_KEY);
  return isRefreshIntervalValue(value) ? value : DEFAULT_REFRESH_INTERVAL;
}

export function writeRefreshIntervalPreference(value: RefreshIntervalValue, storage?: StorageLike): void {
  storage?.setItem(REFRESH_INTERVAL_STORAGE_KEY, value);
}

export function refreshIntervalToMs(value: RefreshIntervalValue): number | null {
  return REFRESH_INTERVAL_OPTIONS.find((option) => option.value === value)?.ms ?? null;
}

export function resolveDisplayedQueueSize(
  remoteQueueSize: number,
  localQueueSize: number,
  hasAuthoritativeRemoteQueue: boolean,
): number {
  return hasAuthoritativeRemoteQueue ? remoteQueueSize : localQueueSize;
}

export function normalizeOperationsMode(value: unknown): OperationsMode {
  if (value === "online" || value === "offline" || value === "degraded") {
    return value;
  }

  return "offline";
}

function normalizeEvent(value: unknown): OperationsEvent | null {
  if (!isRecord(value)) {
    return null;
  }

  return {
    ts: typeof value.ts === "string" ? value.ts : new Date(0).toISOString(),
    level: value.level === "debug" || value.level === "info" || value.level === "warn" || value.level === "error"
      ? value.level
      : "info",
    event: typeof value.event === "string" ? value.event : "unknown.event",
    component: typeof value.component === "string" ? value.component : "system",
    message: typeof value.message === "string" ? value.message : "No message available",
  };
}

export function normalizeOperationsSnapshot(value: unknown): OperationsSnapshot {
  if (!isRecord(value)) {
    return {
      mode: "offline",
      lastUpdatedAt: null,
      queueSize: 0,
      events: [],
    };
  }

  const events = Array.isArray(value.events)
    ? value.events.map((event) => normalizeEvent(event)).filter((event): event is OperationsEvent => event !== null)
    : [];

  return {
    mode: normalizeOperationsMode(value.status ?? value.mode),
    lastUpdatedAt: typeof value.lastUpdatedAt === "string" ? value.lastUpdatedAt : null,
    queueSize: typeof value.queueDepth === "number" ? value.queueDepth : 0,
    events,
  };
}

export function parseOperationsSsePayload(value: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(value);
    return isRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}
