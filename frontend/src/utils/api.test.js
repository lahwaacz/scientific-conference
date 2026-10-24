/**
 * Unit tests for the API client helpers in utils/api.js.
 *
 * buildHeaders is intentionally NOT exported; it is exercised indirectly
 * through fetchWithAuth by inspecting the headers handed to globalThis.fetch.
 *
 * isRefreshing/failedQueue are module-level singletons, so every test that
 * touches fetchWithAuth reloads the module (vi.resetModules + dynamic import) to
 * guarantee a fresh latch state.
 */

const BASE = "http://localhost:8000";

let api;
let reloadMock;

function setCsrfCookie(value = "csrf-token") {
  Object.defineProperty(document, "cookie", {
    configurable: true,
    value: `csrftoken=${value}`,
  });
}

function clearCsrfCookie() {
  Object.defineProperty(document, "cookie", {
    configurable: true,
    value: "",
  });
}

async function loadApi() {
  vi.resetModules();
  vi.stubEnv("VITE_BACKEND_API_BASE_URL", BASE);
  api = await import("./api");
}

function refreshCallCount() {
  return globalThis.fetch.mock.calls.filter(([url]) =>
    url.includes("/api/auth/refresh/")
  ).length;
}

beforeEach(() => {
  reloadMock = vi.fn();
  // The failure path in fetchWithAuth pokes window.location.hash + reload().
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: { hash: "", reload: reloadMock },
  });
  localStorage.clear();
  clearCsrfCookie();
});

afterEach(() => {
  vi.unstubAllEnvs();
  clearCsrfCookie();
});

describe("runtime app config (app-config.js)", () => {
  afterEach(() => {
    delete window.__APP_CONFIG__;
  });

  test("the runtime apiBase overrides the build-time env", async () => {
    window.__APP_CONFIG__ = { apiBase: "/conference-demo" };

    await loadApi();

    expect(api.buildApiUrl("/api/conferences/")).toBe(
      "/conference-demo/api/conferences/"
    );
  });

  test("an empty runtime config falls back to the env value", async () => {
    window.__APP_CONFIG__ = {};

    await loadApi();

    expect(api.buildApiUrl("/api/conferences/")).toBe(
      "http://localhost:8000/api/conferences/"
    );
  });
});

describe("buildApiUrl", () => {
  beforeEach(async () => loadApi());

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
  afterEach(() => {
    delete window.__APP_CONFIG__;
  });

  describe("without a deployed base path", () => {
    beforeEach(async () => loadApi());

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

    test("keeps a deployment-looking prefix that is not the API base", () => {
      expect(api.buildMediaUrl("conference-demo/media/x.png")).toBe(
        `${BASE}/conference-demo/media/x.png`
      );
    });

    test("trims surrounding whitespace before building", () => {
      expect(api.buildMediaUrl("  media/x.png  ")).toBe(`${BASE}/media/x.png`);
    });

    test("passes absolute http(s) URLs through untouched", () => {
      expect(api.buildMediaUrl("https://cdn.test/a.png")).toBe(
        "https://cdn.test/a.png"
      );
    });
  });

  describe("with a deployed base path", () => {
    test("strips the configured base path from the backend media URL", async () => {
      window.__APP_CONFIG__ = { apiBase: "/conference-demo" };
      await loadApi();

      expect(api.buildMediaUrl("conference-demo/media/x.png")).toBe(
        "/conference-demo/media/x.png"
      );
      expect(api.buildMediaUrl("/conference-demo/media/x.png")).toBe(
        "/conference-demo/media/x.png"
      );
    });

    test("strips any configured prefix, not a hardcoded one", async () => {
      window.__APP_CONFIG__ = { apiBase: "/conference" };
      await loadApi();

      expect(api.buildMediaUrl("conference/media/x.png")).toBe(
        "/conference/media/x.png"
      );
    });

    test("strips a multi-segment base path while keeping the origin", async () => {
      window.__APP_CONFIG__ = { apiBase: "https://api.test/foo/bar" };
      await loadApi();

      expect(api.buildMediaUrl("foo/bar/media/x.png")).toBe(
        "https://api.test/foo/bar/media/x.png"
      );
    });

    test("does not strip when the media path carries no prefix", async () => {
      window.__APP_CONFIG__ = { apiBase: "/conference" };
      await loadApi();

      expect(api.buildMediaUrl("media/x.png")).toBe("/conference/media/x.png");
    });
  });
});

describe("cookie request headers (exercised via fetchWithAuth)", () => {
  beforeEach(async () => {
    setCsrfCookie();
    await loadApi();
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200 });
  });

  test("sends application/json and includes cookies for a JSON body", async () => {
    await api.fetchWithAuth("/api/x", {
      method: "POST",
      body: JSON.stringify({ a: 1 }),
    });

    const [, opts] = globalThis.fetch.mock.calls[0];
    expect(opts.headers["Content-Type"]).toBe("application/json");
    expect(opts.headers["X-CSRFToken"]).toBe("csrf-token");
    expect(opts.credentials).toBe("include");
  });

  test("omits content type for FormData and includes cookies", async () => {
    const form = new FormData();
    form.append("file", "value");

    await api.fetchWithAuth("/api/x", { method: "POST", body: form });

    const [, opts] = globalThis.fetch.mock.calls[0];
    expect(opts.headers["Content-Type"]).toBeUndefined();
    expect(opts.headers["X-CSRFToken"]).toBe("csrf-token");
    expect(opts.credentials).toBe("include");
  });

  test("never sends an Authorization header", async () => {
    await api.fetchWithAuth("/api/x", { method: "GET" });

    const [, opts] = globalThis.fetch.mock.calls[0];
    expect(opts.headers.Authorization).toBeUndefined();
    expect(opts.headers["X-CSRFToken"]).toBeUndefined();
    expect(opts.headers["Content-Type"]).toBe("application/json");
  });
});

describe("fetchWithAuth 401 refresh flow", () => {
  beforeEach(async () => {
    setCsrfCookie();
    await loadApi();
    globalThis.fetch = vi.fn();
  });

  test("serializes concurrent 401s behind a single refresh, then retries the queue", async () => {
    let protectedCalls = 0;

    globalThis.fetch = vi.fn((url) => {
      if (url.includes("/api/auth/refresh/")) {
        return Promise.resolve({ ok: true, status: 200 });
      }
      protectedCalls += 1;
      return Promise.resolve({
        ok: protectedCalls > 2,
        status: protectedCalls > 2 ? 200 : 401,
      });
    });

    const p1 = api.fetchWithAuth("/api/data");
    const p2 = api.fetchWithAuth("/api/data");
    const [r1, r2] = await Promise.all([p1, p2]);

    expect(r1.status).toBe(200);
    expect(r2.status).toBe(200);
    // Single-flight latch: exactly one refresh despite two 401s.
    expect(refreshCallCount()).toBe(1);
    // two initial 401s + one refresh + two retried requests.
    expect(globalThis.fetch).toHaveBeenCalledTimes(5);

    const refreshCall = globalThis.fetch.mock.calls.find(([url]) =>
      url.includes("/api/auth/refresh/")
    );
    expect(refreshCall[1].credentials).toBe("include");
    expect(refreshCall[1].headers["X-CSRFToken"]).toBe("csrf-token");
    expect(refreshCall[1].body).toBeUndefined();
  });

  test("reloads home when the refresh request fails", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401 });

    const consoleError = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    const res = await api.fetchWithAuth("/api/data");
    consoleError.mockRestore();

    expect(res.status).toBe(401);
    expect(reloadMock).toHaveBeenCalled();
    expect(window.location.hash).toBe("/");
  });

  test("returns a 401 probe response without refreshing", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401 });

    const res = await api.fetchWithAuth("/api/auth/user/", {
      skipRefresh: true,
    });

    expect(res.status).toBe(401);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    expect(reloadMock).not.toHaveBeenCalled();
  });

  test("soft refresh does not reload when the refresh request fails", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 401 });

    const refreshed = await api.refreshAccessToken({ reloadOnFailure: false });

    expect(refreshed).toBe(false);
    expect(reloadMock).not.toHaveBeenCalled();
  });
});

describe("buildApiUrl conference scoping", () => {
  // conferenceSlug is a module singleton shared with api.js, so initializing
  // the real module (fresh after vi.resetModules) before importing ./api is
  // the least-mock way to drive the scoping branch.
  async function loadApiWithPathname(pathname) {
    vi.resetModules();
    window.location.pathname = pathname;
    const slugModule = await import("./conferenceSlug");
    slugModule.initConferenceSlug();
    api = await import("./api");
  }

  describe("with a conference slug captured", () => {
    beforeEach(async () => loadApiWithPathname("/wsc2026/"));

    test("scopes a regular /api path under /api/<slug>/", () => {
      expect(api.buildApiUrl("/api/program/")).toBe(
        `${BASE}/api/wsc2026/program/`
      );
    });

    test("scopes an /api path given without a leading slash", () => {
      expect(api.buildApiUrl("api/program/")).toBe(
        `${BASE}/api/wsc2026/program/`
      );
    });

    test("passes the global auth endpoints through unscoped", () => {
      expect(api.buildApiUrl("/api/auth/login/")).toBe(
        `${BASE}/api/auth/login/`
      );
      expect(api.buildApiUrl("/api/auth/refresh/")).toBe(
        `${BASE}/api/auth/refresh/`
      );
    });

    test("passes the conferences endpoint through unscoped", () => {
      expect(api.buildApiUrl("/api/conferences/")).toBe(
        `${BASE}/api/conferences/`
      );
    });

    test("treats allowlist prefixes without a trailing slash as global", () => {
      expect(api.buildApiUrl("/api/conferences")).toBe(
        `${BASE}/api/conferences`
      );
      expect(api.buildApiUrl("/api/auth")).toBe(`${BASE}/api/auth`);
    });

    test("passes absolute http(s) URLs through untouched", () => {
      expect(api.buildApiUrl("https://elsewhere.test/api/x")).toBe(
        "https://elsewhere.test/api/x"
      );
      expect(api.buildApiUrl("http://elsewhere.test/api/y")).toBe(
        "http://elsewhere.test/api/y"
      );
    });

    test("does not slug-prefix non-/api paths", () => {
      expect(api.buildApiUrl("/media/x.png")).toBe(`${BASE}/media/x.png`);
    });
  });

  describe("without a conference slug (landing page)", () => {
    beforeEach(async () => loadApiWithPathname("/"));

    test("passes non-allowlisted /api paths through unscoped", () => {
      expect(api.buildApiUrl("/api/program/")).toBe(`${BASE}/api/program/`);
    });

    test("keeps the global allowlist unscoped", () => {
      expect(api.buildApiUrl("/api/conferences/")).toBe(
        `${BASE}/api/conferences/`
      );
      expect(api.buildApiUrl("/api/auth/login/")).toBe(
        `${BASE}/api/auth/login/`
      );
    });
  });

  test("tolerates the pathname-less window.location mock", async () => {
    vi.resetModules();
    const slugModule = await import("./conferenceSlug");
    expect(() => slugModule.initConferenceSlug()).not.toThrow();
    expect(slugModule.getConferenceSlug()).toBeNull();

    api = await import("./api");
    expect(api.buildApiUrl("/api/program/")).toBe(`${BASE}/api/program/`);
  });

  describe("fetchWithAuth under a captured slug", () => {
    beforeEach(async () => loadApiWithPathname("/wsc2026/"));

    test("requests hit the slug-scoped URL", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200 });

      await api.fetchWithAuth("/api/admin/days/");

      expect(globalThis.fetch.mock.calls[0][0]).toBe(
        `${BASE}/api/wsc2026/admin/days/`
      );
    });

    test("refresh stays global and the retry hits the scoped URL", async () => {
      let protectedCalls = 0;

      globalThis.fetch = vi.fn((url) => {
        if (url === `${BASE}/api/auth/refresh/`) {
          return Promise.resolve({ ok: true, status: 200 });
        }
        protectedCalls += 1;
        return Promise.resolve({
          ok: protectedCalls > 1,
          status: protectedCalls > 1 ? 200 : 401,
        });
      });

      const res = await api.fetchWithAuth("/api/data");

      expect(res.status).toBe(200);
      expect(refreshCallCount()).toBe(1);
      const [retriedUrl, retriedOpts] = globalThis.fetch.mock.calls.at(-1);
      expect(retriedUrl).toBe(`${BASE}/api/wsc2026/data`);
      expect(retriedOpts.credentials).toBe("include");
      expect(retriedOpts.headers.Authorization).toBeUndefined();
    });
  });
});
