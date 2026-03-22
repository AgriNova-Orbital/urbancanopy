export function createWindowErrorEventGuard() {
  return {
    shouldReport(event) {
      return event.error == null;
    },
  };
}
