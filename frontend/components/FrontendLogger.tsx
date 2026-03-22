"use client";

import { useEffect } from "react";

import { createFrontendLogger, type FrontendLogger as FrontendLoggerClient } from "../lib/logger";

let runtimeLogger: FrontendLoggerClient | null = null;

function getRuntimeLogger(): FrontendLoggerClient {
  if (!runtimeLogger) {
    runtimeLogger = createFrontendLogger({ component: "frontend.runtime", mode: "browser" });
  }

  return runtimeLogger;
}

function toErrorMeta(value: unknown): Record<string, unknown> {
  if (value instanceof Error) {
    return {
      name: value.name,
      message: value.message,
      stack: value.stack ?? null,
    };
  }

  if (typeof value === "string") {
    return { value };
  }

  return { value: String(value) };
}

function fireAndForget(promise: Promise<unknown>): void {
  promise.catch(() => {
    return;
  });
}

export function reportFrontendRuntimeIssue(
  level: "warn" | "error",
  event: string,
  message: string,
  meta: Record<string, unknown> = {},
): void {
  try {
    const logger = getRuntimeLogger();
    const method = level === "warn" ? logger.warn.bind(logger) : logger.error.bind(logger);
    fireAndForget(method(event, message, meta));
  } catch {
    return;
  }
}

export default function FrontendLogger() {
  useEffect(() => {
    const originalConsoleError = console.error.bind(console);
    const originalConsoleWarn = console.warn.bind(console);

    console.error = (...args: unknown[]) => {
      originalConsoleError(...args);
      reportFrontendRuntimeIssue("error", "ui.console.error", "console.error emitted", {
        arguments: args.map((value) => toErrorMeta(value)),
      });
    };

    console.warn = (...args: unknown[]) => {
      originalConsoleWarn(...args);
      reportFrontendRuntimeIssue("warn", "ui.console.warn", "console.warn emitted", {
        arguments: args.map((value) => toErrorMeta(value)),
      });
    };

    const handleError = (event: ErrorEvent) => {
      reportFrontendRuntimeIssue("error", "ui.runtime.error", event.message || "window error", {
        filename: event.filename || null,
        line: event.lineno || null,
        column: event.colno || null,
        ...toErrorMeta(event.error ?? event.message),
      });
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      reportFrontendRuntimeIssue("error", "ui.runtime.unhandled_rejection", "Unhandled promise rejection", {
        ...toErrorMeta(event.reason),
      });
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      console.error = originalConsoleError;
      console.warn = originalConsoleWarn;
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleUnhandledRejection);
    };
  }, []);

  return null;
}
