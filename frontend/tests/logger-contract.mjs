import { createFrontendLogger } from "../lib/logger";

const logger = createFrontendLogger({
  transport: async () => {
    throw new Error("offline");
  },
});

await logger.info("ui.loaded", "dashboard loaded", { city: "taipei" });

if (logger.queueSize() !== 1) {
  throw new Error("expected one queued event");
}
