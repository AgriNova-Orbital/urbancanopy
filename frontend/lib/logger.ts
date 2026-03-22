import { createLogStore, type FrontendLogEvent, type FrontendLogStore } from "./log-store";

export type FrontendLogLevel = FrontendLogEvent["level"];

export interface FrontendLoggerSyncStatus {
  state: "idle" | "success" | "error";
  syncedAt: string | null;
  error: string | null;
  queueSize: number;
}

export interface FrontendLogger {
  debug(event: string, message: string, meta?: Record<string, unknown>): Promise<FrontendLogEvent>;
  info(event: string, message: string, meta?: Record<string, unknown>): Promise<FrontendLogEvent>;
  warn(event: string, message: string, meta?: Record<string, unknown>): Promise<FrontendLogEvent>;
  error(event: string, message: string, meta?: Record<string, unknown>): Promise<FrontendLogEvent>;
  queueSize(): number;
  lastSyncStatus(): FrontendLoggerSyncStatus;
  sync(): Promise<void>;
}

type Transport = (events: FrontendLogEvent[]) => Promise<void>;

type FetchLike = (input: string, init?: { method?: string; headers?: Record<string, string>; body?: string }) => Promise<{
  ok: boolean;
  status: number;
}>;

function createBackendTransport(options?: { endpoint?: string; fetch?: FetchLike }): Transport {
  const endpoint = options?.endpoint ?? "/api/logs";
  const hasCustomFetch = typeof options?.fetch === "function";
  const fetchImpl = options?.fetch ?? (typeof globalThis.fetch === "function" ? globalThis.fetch.bind(globalThis) : undefined);

  return async (events: FrontendLogEvent[]) => {
    if (!fetchImpl) {
      throw new Error("backend transport unavailable");
    }

    if (endpoint.startsWith("/") && typeof window === "undefined" && !hasCustomFetch) {
      throw new Error("backend transport unavailable");
    }

    const response = await fetchImpl(endpoint, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ events }),
    });

    if (!response.ok) {
      throw new Error(`backend transport failed: ${response.status}`);
    }
  };
}

export function createFrontendLogger(options?: {
  component?: string;
  mode?: string;
  transport?: Transport;
  endpoint?: string;
  fetch?: FetchLike;
  store?: FrontendLogStore;
}): FrontendLogger {
  const component = options?.component ?? "frontend";
  const mode = options?.mode ?? "offline";
  const transport = options?.transport ?? createBackendTransport({ endpoint: options?.endpoint, fetch: options?.fetch });
  const store = options?.store ?? createLogStore();

  let lastStatus: FrontendLoggerSyncStatus = {
    state: "idle",
    syncedAt: null,
    error: null,
    queueSize: store.size(),
  };
  let flushRequested = false;
  let flushPromise: Promise<void> | null = null;

  const setStatus = (status: Partial<FrontendLoggerSyncStatus>) => {
    lastStatus = {
      ...lastStatus,
      ...status,
      queueSize: store.size(),
    };
  };

  const processFlushQueue = async (): Promise<void> => {
    do {
      flushRequested = false;

      const queuedEvents = store.list();

      if (queuedEvents.length === 0) {
        setStatus({ state: "idle", error: null });
        return;
      }

      try {
        await transport(queuedEvents);
        store.remove(queuedEvents.length);
        setStatus({ state: "success", syncedAt: new Date().toISOString(), error: null });
      } catch (error) {
        setStatus({
          state: "error",
          error: error instanceof Error ? error.message : String(error),
        });
        return;
      }
    } while (flushRequested);
  };

  const flush = async (): Promise<void> => {
    flushRequested = true;

    if (!flushPromise) {
      flushPromise = Promise.resolve()
        .then(processFlushQueue)
        .finally(() => {
          flushPromise = null;
        });
    }

    await flushPromise;

    if (flushRequested && !flushPromise) {
      await flush();
    }
  };

  const log = async (
    level: FrontendLogLevel,
    event: string,
    message: string,
    meta: Record<string, unknown> = {},
  ): Promise<FrontendLogEvent> => {
    const payload: FrontendLogEvent = {
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
