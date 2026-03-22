export interface FrontendLogEvent {
  ts: string;
  level: "debug" | "info" | "warn" | "error";
  event: string;
  component: string;
  message: string;
  runId: string | null;
  jobId: string | null;
  mode: string;
  online: boolean | null;
  fallbackUsed: boolean;
  meta: Record<string, unknown>;
}

type StorageLike = Pick<Storage, "getItem" | "setItem">;

const memoryStorage = new Map<string, string>();

function resolveStorage(storage?: StorageLike): StorageLike {
  if (storage) {
    return storage;
  }

  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.getItem === "function" &&
    typeof window.localStorage.setItem === "function"
  ) {
    return window.localStorage;
  }

  return {
    getItem(key: string) {
      return memoryStorage.get(key) ?? null;
    },
    setItem(key: string, value: string) {
      memoryStorage.set(key, value);
    },
  };
}

export interface FrontendLogStore {
  enqueue(event: FrontendLogEvent): FrontendLogEvent[];
  list(): FrontendLogEvent[];
  remove(count: number): FrontendLogEvent[];
  replace(events: FrontendLogEvent[]): FrontendLogEvent[];
  size(): number;
}

export function createLogStore(options?: {
  storageKey?: string;
  storage?: StorageLike;
  maxQueueSize?: number;
}): FrontendLogStore {
  const storageKey = options?.storageKey ?? "urbancanopy.frontend.logs";
  const storage = resolveStorage(options?.storage);
  const maxQueueSize = options?.maxQueueSize ?? 200;

  const readQueue = (): FrontendLogEvent[] => {
    const raw = storage.getItem(storageKey);

    if (!raw) {
      return [];
    }

    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? (parsed as FrontendLogEvent[]) : [];
    } catch {
      return [];
    }
  };

  const writeQueue = (events: FrontendLogEvent[]): FrontendLogEvent[] => {
    const nextEvents = maxQueueSize > 0 ? events.slice(-maxQueueSize) : [];
    storage.setItem(storageKey, JSON.stringify(nextEvents));
    return nextEvents;
  };

  return {
    enqueue(event: FrontendLogEvent) {
      return writeQueue([...readQueue(), event]);
    },
    list() {
      return readQueue();
    },
    remove(count: number) {
      return writeQueue(readQueue().slice(count));
    },
    replace(events: FrontendLogEvent[]) {
      return writeQueue([...events]);
    },
    size() {
      return readQueue().length;
    },
  };
}
