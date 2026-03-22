type WindowErrorLike = {
  message?: string;
  filename?: string;
  lineno?: number;
  colno?: number;
  error?: unknown;
};

function buildSignature(event: WindowErrorLike): string {
  return JSON.stringify({
    message: event.message ?? null,
    filename: event.filename ?? null,
    lineno: event.lineno ?? null,
    colno: event.colno ?? null,
  });
}

export function createWindowErrorEventGuard() {
  return {
    shouldReport(event: WindowErrorLike): boolean {
      return event.error == null && buildSignature(event) === JSON.stringify({
        message: null,
        filename: null,
        lineno: null,
        colno: null,
      })
        ? true
        : event.error == null;
    },
  };
}
