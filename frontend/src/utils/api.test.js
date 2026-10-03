/**
 * Unit tests for the API client helpers in utils/api.js.
 *
 * buildHeaders is intentionally NOT exported; it is exercised indirectly
 * through fetchWithAuth by inspecting the headers handed to global.fetch.
 *
 * isRefreshing/failedQueue are module-level singletons, so every test that
 * touches fetchWithAuth reloads the module (jest.resetModules + require) to
 * guarantee a fresh latch state.
 */

const BASE = "http://localhost:8000";

let api;
let reloadMock;

function loadApi() {
  jest.resetModules();
  api = require("./api");
}

function refreshCallCount() {
  return global.fetch.mock.calls.filter(([url]) =>
    url.includes("/api/auth/refresh/")
  ).length;
}

beforeEach(() => {
  reloadMock = jest.fn();
  // The failure path in fetchWithAuth pokes window.location.hash + reload().
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: { hash: "", reload: reloadMock },
  });
  localStorage.clear();
});

describe("buildApiUrl", () => {
  beforeEach(() => loadApi());

  test("returns the bare base URL for an empty path", () => {
    expect(api.buildApiUrl("")).toBe(BASE);
    expect(api.buildApiUrl()).toBe(BASE);
  });

  test("adds a leading slash when the path omits one", () => {
    expect(api.buildApiUrl("api/auth/login/")).toBe(
      "http://localhost:8000/api/auth/login/"
    );
  });

  test("preserves an existing leading slash without doubling it", () => {
    expect(api.buildApiUrl("/api/submit/")).toBe(
      "http://localhost:8000/api/submit/"
    );
  });

  test("passes absolute http(s) URLs through untouched", () => {
    expect(api.buildApiUrl("https://elsewhere.test/x")).toBe(
      "https://elsewhere.test/x"
    );
    expect(api.buildApiUrl("http://elsewhere.test/y")).toBe(
      "http://elsewhere.test/y"
    );
  });
});

describe("buildMediaUrl", () => {
  beforeEach(() => loadApi());

  test("returns an empty string for an empty path", () => {
    expect(api.buildMediaUrl("")).toBe("");
    expect(api.buildMediaUrl()).toBe("");
  });

  test("collapses leading slashes and joins the base", () => {
    expect(api.buildMediaUrl("/media/photo.png")).toBe(
      "http://localhost:8000/media/photo.png"
    );
    expect(api.buildMediaUrl("///media/photo.png")).toBe(
      "http://localhost:8000/media/photo.png"
    );
  });

  test("strips a leading conference-demo/ segment", () => {
    expect(api.buildMediaUrl("conference-demo/media/x.png")).toBe(
      "http://localhost:8000/media/x.png"
    );
    expect(api.buildMediaUrl("/conference-demo/media/x.png")).toBe(
      "http://localhost:8000/media/x.png"
    );
  });

  test("trims surrounding whitespace before building", () => {
    expect(api.buildMediaUrl("  media/x.png  ")).toBe(
      "http://localhost:8000/media/x.png"
    );
  });

  test("passes absolute http(s) URLs through untouched", () => {
    expect(api.buildMediaUrl("https://cdn.test/a.png")).toBe(
      "https://cdn.test/a.png"
    );
  });
});

describe("buildHeaders (exercised via fetchWithAuth)", () => {
  beforeEach(() => {
    loadApi();
    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 200 });
  });

  test("sends application/json content type and Bearer for a JSON body", async () => {
    localStorage.setItem("access_token", "tok");
    await api.fetchWithAuth("/api/x", {
      method: "POST",
      body: JSON.stringify({ a: 1 }),
    });

    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.headers["Content-Type"]).toBe("application/json");
    expect(opts.headers.Authorization).toBe("Bearer tok");
  });

  test("omits content type for FormData but keeps the Bearer header", async () => {
    localStorage.setItem("access_token", "tok");
    const form = new FormData();
    form.append("file", "value");

    await api.fetchWithAuth("/api/x", { method: "POST", body: form });

    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.headers["Content-Type"]).toBeUndefined();
    expect(opts.headers.Authorization).toBe("Bearer tok");
  });

  test("omits the Authorization header when no access token is stored", async () => {
    await api.fetchWithAuth("/api/x", { method: "GET" });

    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.headers.Authorization).toBeUndefined();
    expect(opts.headers["Content-Type"]).toBe("application/json");
  });
});

describe("fetchWithAuth 401 refresh flow", () => {
  beforeEach(() => {
    loadApi();
    global.fetch = jest.fn();
  });

  test("serializes concurrent 401s behind a single refresh, then retries the queue", async () => {
    localStorage.setItem("access_token", "old");
    localStorage.setItem("refresh_token", "r");

    global.fetch = jest.fn((url, opts) => {
      if (url.includes("/api/auth/refresh/")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ access: "NEW" }),
        });
      }
      // Protected resource: only the refreshed token is accepted.
      if (opts?.headers?.Authorization === "Bearer NEW") {
        return Promise.resolve({ ok: true, status: 200 });
      }
      return Promise.resolve({ ok: false, status: 401 });
    });

    const p1 = api.fetchWithAuth("/api/data");
    const p2 = api.fetchWithAuth("/api/data");
    const [r1, r2] = await Promise.all([p1, p2]);

    expect(r1.status).toBe(200);
    expect(r2.status).toBe(200);
    // Single-flight latch: exactly one refresh despite two 401s.
    expect(refreshCallCount()).toBe(1);
    // two initial 401s + one refresh + two retried requests.
    expect(global.fetch).toHaveBeenCalledTimes(5);
  });

  test("clears tokens and reloads home when the refresh request fails", async () => {
    localStorage.setItem("access_token", "old");
    localStorage.setItem("refresh_token", "r");

    global.fetch = jest.fn((url) => {
      if (url.includes("/api/auth/refresh/")) {
        return Promise.resolve({ ok: false, status: 401 });
      }
      return Promise.resolve({ ok: false, status: 401 });
    });

    const consoleError = jest
      .spyOn(console, "error")
      .mockImplementation(() => {});
    const res = await api.fetchWithAuth("/api/data");
    consoleError.mockRestore();

    expect(res.status).toBe(401);
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
    expect(reloadMock).toHaveBeenCalled();
    expect(window.location.hash).toBe("/");
  });

  test("short-circuits the refresh request when no refresh token exists", async () => {
    localStorage.setItem("access_token", "old"); // no refresh_token

    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 401 });

    const res = await api.fetchWithAuth("/api/data");

    expect(res.status).toBe(401);
    expect(refreshCallCount()).toBe(0);
    expect(reloadMock).toHaveBeenCalled();
  });
});
