/**
 * Unit tests for the global fetch monkeypatch in configuredFetch.js.
 *
 * The module captures originalFetch = global.fetch at import time, so each
 * test installs a sentinel global.fetch and requires the module fresh
 * (jest.resetModules) to control exactly what gets captured.
 */

describe("applyBaseUrlToFetch", () => {
  let applyBaseUrlToFetch;
  let originalFetch;

  beforeEach(() => {
    jest.resetModules();
    originalFetch = jest.fn().mockResolvedValue({ ok: true });
    global.fetch = originalFetch;
    // originalFetch is captured right here, at module import.
    applyBaseUrlToFetch = require("./configuredFetch").applyBaseUrlToFetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  test("prefixes a relative URL with the base URL", () => {
    applyBaseUrlToFetch("http://localhost:8000");
    global.fetch("/api/data", { method: "GET" });

    expect(originalFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/data",
      { method: "GET" }
    );
  });

  test("passes absolute http(s) URLs through untouched", () => {
    applyBaseUrlToFetch("http://localhost:8000");

    global.fetch("https://cdn.test/x.png");
    expect(originalFetch).toHaveBeenLastCalledWith(
      "https://cdn.test/x.png",
      undefined
    );

    global.fetch("http://localhost:9999/api/y");
    expect(originalFetch).toHaveBeenLastCalledWith(
      "http://localhost:9999/api/y",
      undefined
    );
  });

  test("forwards to the fetch captured at import, ignoring later globals", () => {
    const unrelated = jest.fn();
    global.fetch = unrelated; // swap global AFTER the import-time capture
    applyBaseUrlToFetch("http://localhost:8000"); // installs the wrapper

    global.fetch("/api/data");

    expect(unrelated).not.toHaveBeenCalled();
    expect(originalFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/data",
      undefined
    );
  });
});
