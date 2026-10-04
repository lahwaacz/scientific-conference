/**
 * Unit tests for the global fetch monkeypatch in configuredFetch.js.
 *
 * The module captures originalFetch = globalThis.fetch at import time, so each
 * test installs a sentinel globalThis.fetch and requires the module fresh
 * (vi.resetModules) to control exactly what gets captured.
 */

describe("applyBaseUrlToFetch", () => {
  let applyBaseUrlToFetch;
  let originalFetch;

  beforeEach(async () => {
    vi.resetModules();
    originalFetch = vi.fn().mockResolvedValue({ ok: true });
    globalThis.fetch = originalFetch;
    // originalFetch is captured right here, at module import.
    ({ applyBaseUrlToFetch } = await import("./configuredFetch"));
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test("prefixes a relative URL with the base URL", () => {
    applyBaseUrlToFetch("http://localhost:8000");
    globalThis.fetch("/api/data", { method: "GET" });

    expect(originalFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/data",
      { method: "GET" }
    );
  });

  test("passes absolute http(s) URLs through untouched", () => {
    applyBaseUrlToFetch("http://localhost:8000");

    globalThis.fetch("https://cdn.test/x.png");
    expect(originalFetch).toHaveBeenLastCalledWith(
      "https://cdn.test/x.png",
      undefined
    );

    globalThis.fetch("http://localhost:9999/api/y");
    expect(originalFetch).toHaveBeenLastCalledWith(
      "http://localhost:9999/api/y",
      undefined
    );
  });

  test("forwards to the fetch captured at import, ignoring later globals", () => {
    const unrelated = vi.fn();
    globalThis.fetch = unrelated; // swap global AFTER the import-time capture
    applyBaseUrlToFetch("http://localhost:8000"); // installs the wrapper

    globalThis.fetch("/api/data");

    expect(unrelated).not.toHaveBeenCalled();
    expect(originalFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/data",
      undefined
    );
  });
});
