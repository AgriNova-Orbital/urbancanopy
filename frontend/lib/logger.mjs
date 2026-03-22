import { createLogStore } from "./log-store.mjs";

export function createFrontendLogger(options = {}) {
  const component = options.component ?? "frontend";
  const mode = options.mode ?? "offline";
  const transport = options.transport ?? (async () => {});
  const store = options.store ?? createLogStore();

  let lastStatus = {
    state: "idle",
    syncedAt: null,
    error: null,
    queueSize: store.size(),
  };

  const setStatus = (status) => {
    lastStatus = {
      ...lastStatus,
      ...status,
      queueSize: store.size(),
    };
  };

  const flush = async () => {
    const queuedEvents = store.list();

    if (queuedEvents.length === 0) {
      setStatus({ state: "idle", error: null });
      return;
    }

    try {
      await transport(queuedEvents);
      store.replace([]);
      setStatus({ state: "success", syncedAt: new Date().toISOString(), error: null });
    } catch (error) {
      setStatus({
        state: "error",
        error: error instanceof Error ? error.message : String(error),
      });
    }
  };

  const log = async (level, event, message, meta = {}) => {
    const payload = {
      ts: new Date().toISOString(),
      level,
      event,
      component,
      message,
      runId: null,
      jobId: null,
      mode,
      online: typeof navigator !== "undefined" ? navigator.onLine : null,
      fallbackUsed: false,
      meta: { ...meta },
    };

    store.enqueue(payload);
    setStatus({ queueSize: store.size() });
    await flush();
    return payload;
  };

  return {
    debug(event, message, meta) {
      return log("debug", event, message, meta);
    },
    info(event, message, meta) {
      return log("info", event, message, meta);
    },
    warn(event, message, meta) {
      return log("warn", event, message, meta);
    },
    error(event, message, meta) {
      return log("error", event, message, meta);
    },
    queueSize() {
      return store.size();
    },
    lastSyncStatus() {
      return { ...lastStatus, queueSize: store.size() };
    },
    sync() {
      return flush();
    },
  };
}
