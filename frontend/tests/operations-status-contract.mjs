import {
  DEFAULT_REFRESH_INTERVAL,
  REFRESH_INTERVAL_OPTIONS,
  normalizeOperationsSnapshot,
  readRefreshIntervalPreference,
  writeRefreshIntervalPreference,
} from "../lib/operations-status.mjs";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function createMemoryStorage() {
  const values = new Map();

  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null;
    },
    setItem(key, value) {
      values.set(key, value);
    },
  };
}

function testRefreshIntervalOptions() {
  assert(REFRESH_INTERVAL_OPTIONS.length === 5, "expected five refresh interval options");
  assert(REFRESH_INTERVAL_OPTIONS.map((option) => option.value).join(",") === "5s,15s,30s,1m,manual", "expected required refresh interval values");
  assert(DEFAULT_REFRESH_INTERVAL === "15s", "expected 15s default refresh interval");
}

function testRefreshIntervalPersistence() {
  const storage = createMemoryStorage();

  assert(readRefreshIntervalPreference(storage) === "15s", "expected default interval before persistence");

  writeRefreshIntervalPreference("manual", storage);

  assert(readRefreshIntervalPreference(storage) === "manual", "expected persisted manual interval");
}

function testStatusNormalization() {
  const snapshot = normalizeOperationsSnapshot({
    status: "degraded",
    lastUpdatedAt: "2026-03-22T16:00:00.000Z",
    queueDepth: 3,
    events: [
      {
        ts: "2026-03-22T15:59:00.000Z",
        level: "warn",
        event: "connectivity.changed",
        component: "sync",
        message: "Connection unstable",
      },
    ],
  });

  assert(snapshot.mode === "degraded", "expected mode from backend status field");
  assert(snapshot.lastUpdatedAt === "2026-03-22T16:00:00.000Z", "expected last update from snapshot");
  assert(snapshot.queueSize === 3, "expected queue size from snapshot");
  assert(snapshot.events.length === 1, "expected normalized event feed");
  assert(snapshot.events[0].message === "Connection unstable", "expected normalized event message");
}

testRefreshIntervalOptions();
testRefreshIntervalPersistence();
testStatusNormalization();
