"use client";

import { createFrontendLogger, type FrontendLogger as FrontendLoggerClient } from "../lib/logger";
import { createWindowErrorEventGuard } from "../lib/runtime-error-dedupe";

let runtimeLogger: FrontendLoggerClient | null = null;
let frontendLoggerInstalled = false;

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

function normalizeRuntimeMeta(meta: Record<string, unknown>): Record<string, unknown> {
  const normalized: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(meta)) {
    if (Array.isArray(value)) {
      normalized[key] = value.map((item) => toErrorMeta(item));
      continue;
    }

    if (value && typeof value === "object" && !(value instanceof Error)) {
      normalized[key] = Object.fromEntries(
        Object.entries(value).map(([nestedKey, nestedValue]) => [nestedKey, toErrorMeta(nestedValue)]),
      );
      continue;
    }

    normalized[key] = toErrorMeta(value);
  }

  return normalized;
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
    fireAndForget(method(event, message, normalizeRuntimeMeta(meta)));
  } catch {
    return;
  }
}

export function ensureFrontendLoggerInstalled(): void {
  if (frontendLoggerInstalled || typeof window === "undefined") {
    return;
  }

  frontendLoggerInstalled = true;

  const originalConsoleError = console.error.bind(console);
  const originalConsoleWarn = console.warn.bind(console);
  const previousWindowOnError = window.onerror;
  const windowErrorEventGuard = createWindowErrorEventGuard();

  console.error = (...args: unknown[]) => {
    originalConsoleError(...args);
    reportFrontendRuntimeIssue("error", "ui.console.error", "console.error emitted", {
      arguments: args,
    });
  };

  console.warn = (...args: unknown[]) => {
    originalConsoleWarn(...args);
    reportFrontendRuntimeIssue("warn", "ui.console.warn", "console.warn emitted", {
      arguments: args,
    });
  };

  const handleWindowError = (
    message: string | Event,
    source?: string,
    lineno?: number,
    colno?: number,
    error?: Error,
  ) => {
    reportFrontendRuntimeIssue("error", "ui.runtime.error", typeof message === "string" ? message : "window error", {
      message,
      filename: source ?? null,
      line: lineno ?? null,
      column: colno ?? null,
      error: error ?? null,
    });

    if (typeof previousWindowOnError === "function") {
      return previousWindowOnError(message, source, lineno, colno, error);
    }

    return false;
  };

  const handleErrorEvent = (event: ErrorEvent) => {
    if (!windowErrorEventGuard.shouldReport(event)) {
      return;
    }

    handleWindowError(event.message || "window error", event.filename, event.lineno, event.colno, event.error);
  };

  const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
    reportFrontendRuntimeIssue("error", "ui.runtime.unhandled_rejection", "Unhandled promise rejection", {
      reason: event.reason,
    });
  };

  window.onerror = handleWindowError;
  window.addEventListener("error", handleErrorEvent);
  window.addEventListener("unhandledrejection", handleUnhandledRejection);
}

export default function FrontendLogger() {
  ensureFrontendLoggerInstalled();

  return null;
}
