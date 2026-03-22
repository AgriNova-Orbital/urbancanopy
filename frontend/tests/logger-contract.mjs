import { createFrontendLogger } from "../lib/logger";
import { createLogStore } from "../lib/log-store";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function testOfflineTransportQueuesEvent() {
  const logger = createFrontendLogger({
    store: createLogStore({ storageKey: "contract-offline-transport" }),
    transport: async () => {
      throw new Error("offline");
    },
  });

  await logger.info("ui.loaded", "dashboard loaded", { city: "taipei" });

  assert(logger.queueSize() === 1, "expected one queued event");
}

async function testDefaultLoggerRetainsQueueWithoutBackend() {
  const logger = createFrontendLogger({
    store: createLogStore({ storageKey: "contract-default-transport" }),
  });

  await logger.info("ui.loaded", "dashboard loaded");

  assert(logger.queueSize() === 1, "expected default logger to retain queued event locally");
  assert(logger.lastSyncStatus().state === "error", "expected default logger sync status to report error");
}

async function testSuccessfulSyncClearsQueueAndUpdatesStatus() {
  const sent = [];
  const logger = createFrontendLogger({
    store: createLogStore({ storageKey: "contract-success-sync" }),
    fetch: async (_url, init) => {
      sent.push(JSON.parse(init.body));
      return {
        ok: true,
        status: 200,
      };
    },
  });

  await logger.info("ui.synced", "sent to backend", { city: "taipei" });

  assert(sent.length === 1, "expected one backend sync request");
  assert(sent[0].events.length === 1, "expected one event in backend sync payload");
  assert(logger.queueSize() === 0, "expected successful sync to clear queue");
  assert(logger.lastSyncStatus().state === "success", "expected sync status success");
  assert(logger.lastSyncStatus().syncedAt, "expected sync timestamp after success");
}

async function testConcurrentLogsDoNotDuplicateTransportPayloads() {
  const payloads = [];
  let releaseSend;
  const pendingSend = new Promise((resolve) => {
    releaseSend = resolve;
  });

  const logger = createFrontendLogger({
    store: createLogStore({ storageKey: "contract-concurrent-sync" }),
    transport: async (events) => {
      payloads.push(events.map((event) => event.event));
      await pendingSend;
    },
  });

  const first = logger.info("ui.loaded", "dashboard loaded");
  const second = logger.warn("ui.warned", "dashboard warning");

  await Promise.resolve();
  releaseSend();
  await Promise.all([first, second]);

  assert(payloads.length === 1, "expected overlapping flushes to share one transport call");
  assert(payloads[0].length === 2, "expected batched transport payload to contain two events");
  assert(payloads[0][0] === "ui.loaded", "expected first event in payload");
  assert(payloads[0][1] === "ui.warned", "expected second event in payload");
  assert(logger.queueSize() === 0, "expected queue cleared after shared flush");
}

await testOfflineTransportQueuesEvent();
await testDefaultLoggerRetainsQueueWithoutBackend();
await testSuccessfulSyncClearsQueueAndUpdatesStatus();
await testConcurrentLogsDoNotDuplicateTransportPayloads();
