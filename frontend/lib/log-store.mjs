const memoryStorage = new Map();

function resolveStorage(storage) {
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
    getItem(key) {
      return memoryStorage.get(key) ?? null;
    },
    setItem(key, value) {
      memoryStorage.set(key, value);
    },
  };
}

export function createLogStore(options = {}) {
  const storageKey = options.storageKey ?? "urbancanopy.frontend.logs";
  const storage = resolveStorage(options.storage);
  const maxQueueSize = options.maxQueueSize ?? 200;

  const readQueue = () => {
    const raw = storage.getItem(storageKey);

    if (!raw) {
      return [];
    }

    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  };

  const writeQueue = (events) => {
    const nextEvents = maxQueueSize > 0 ? events.slice(-maxQueueSize) : [];
    storage.setItem(storageKey, JSON.stringify(nextEvents));
    return nextEvents;
  };

  return {
    enqueue(event) {
      return writeQueue([...readQueue(), event]);
    },
    list() {
      return readQueue();
    },
    remove(count) {
      return writeQueue(readQueue().slice(count));
    },
    replace(events) {
      return writeQueue([...events]);
    },
    size() {
      return readQueue().length;
    },
  };
}
