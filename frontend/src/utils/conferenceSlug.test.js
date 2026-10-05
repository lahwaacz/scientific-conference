/**
 * Unit tests for the conference slug singleton in utils/conferenceSlug.js.
 *
 * The slug is a module-level singleton captured by initConferenceSlug() from
 * window.location.pathname (HashRouter's useLocation cannot see the path
 * prefix), so every test reloads the module (vi.resetModules + dynamic
 * import) and re-runs init against a freshly stubbed window.location.
 *
 * import.meta.env.BASE_URL is stubbed with vi.stubEnv to switch between the
 * dev deployment ("./" => "/") and the subpath deployment ("/conference-demo/").
 */

const DEV_BASE = "./";
const DEPLOYED_BASE = "/conference-demo/";

let slugModule;

function setLocation(locationValue) {
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: locationValue,
  });
}

async function loadSlugModule(base = DEV_BASE) {
  vi.resetModules();
  vi.stubEnv("BASE_URL", base);
  slugModule = await import("./conferenceSlug");
}

async function initWithLocation(locationValue, base = DEV_BASE) {
  await loadSlugModule(base);
  setLocation(locationValue);
  slugModule.initConferenceSlug();
  return slugModule;
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("getDeployedBasePath", () => {
  test('maps the dev base "./" to "/"', async () => {
    await loadSlugModule(DEV_BASE);
    expect(slugModule.getDeployedBasePath()).toBe("/");
  });

  test('maps an explicit "/" base to "/"', async () => {
    await loadSlugModule("/");
    expect(slugModule.getDeployedBasePath()).toBe("/");
  });

  test("keeps a subpath base with leading and trailing slash", async () => {
    await loadSlugModule(DEPLOYED_BASE);
    expect(slugModule.getDeployedBasePath()).toBe("/conference-demo/");
  });

  test("normalizes a subpath base missing its trailing slash", async () => {
    await loadSlugModule("/conference-demo");
    expect(slugModule.getDeployedBasePath()).toBe("/conference-demo/");
  });
});

describe("initConferenceSlug / getConferenceSlug (dev base)", () => {
  test("root path yields null (landing page)", async () => {
    const m = await initWithLocation({ pathname: "/" });
    expect(m.getConferenceSlug()).toBeNull();
  });

  test("single-segment path yields the slug", async () => {
    const m = await initWithLocation({ pathname: "/wsc2026/" });
    expect(m.getConferenceSlug()).toBe("wsc2026");
  });

  test("missing trailing slash still yields the slug", async () => {
    const m = await initWithLocation({ pathname: "/wsc2026" });
    expect(m.getConferenceSlug()).toBe("wsc2026");
  });

  test("double slashes are tolerated", async () => {
    const m = await initWithLocation({ pathname: "//wsc2026/" });
    expect(m.getConferenceSlug()).toBe("wsc2026");
  });

  test("only the first non-empty segment is the slug", async () => {
    const m = await initWithLocation({ pathname: "/wsc2026/some/deep/path" });
    expect(m.getConferenceSlug()).toBe("wsc2026");
  });

  test("a window.location without a pathname property yields null", async () => {
    // api.test.js mocks location as { hash, reload } only — the module
    // must tolerate a pathname-less location object.
    const m = await initWithLocation({ hash: "#/program", reload: vi.fn() });
    expect(m.getConferenceSlug()).toBeNull();
  });

  test("getConferenceSlug is null before initConferenceSlug runs", async () => {
    await loadSlugModule();
    expect(slugModule.getConferenceSlug()).toBeNull();
  });
});

describe("initConferenceSlug / getConferenceSlug (deployed base)", () => {
  test("the bare deployment prefix yields null", async () => {
    const m = await initWithLocation(
      { pathname: "/conference-demo/" },
      DEPLOYED_BASE
    );
    expect(m.getConferenceSlug()).toBeNull();
  });

  test("the deployment prefix without trailing slash yields null", async () => {
    const m = await initWithLocation(
      { pathname: "/conference-demo" },
      DEPLOYED_BASE
    );
    expect(m.getConferenceSlug()).toBeNull();
  });

  test("slug after the deployment prefix is extracted", async () => {
    const m = await initWithLocation(
      { pathname: "/conference-demo/wsc2026/" },
      DEPLOYED_BASE
    );
    expect(m.getConferenceSlug()).toBe("wsc2026");
  });

  test("slug is extracted from a deep path under the deployment prefix", async () => {
    const m = await initWithLocation(
      { pathname: "/conference-demo/wsc2026/some/deep/path" },
      DEPLOYED_BASE
    );
    expect(m.getConferenceSlug()).toBe("wsc2026");
  });
});

describe("conferenceApiPrefix", () => {
  test("builds the scoped /api/<slug> prefix once a slug is captured", async () => {
    const m = await initWithLocation({ pathname: "/wsc2026/" });
    expect(m.conferenceApiPrefix()).toBe("/api/wsc2026");
  });

  test("is null on the landing page", async () => {
    const m = await initWithLocation({ pathname: "/" });
    expect(m.conferenceApiPrefix()).toBeNull();
  });
});

describe("isLandingPage", () => {
  test("true when no slug was captured", async () => {
    const m = await initWithLocation({ pathname: "/" });
    expect(m.isLandingPage()).toBe(true);
  });

  test("false when a slug was captured", async () => {
    const m = await initWithLocation({ pathname: "/wsc2026/" });
    expect(m.isLandingPage()).toBe(false);
  });
});

describe("conferenceUrl", () => {
  test("builds a root-relative conference URL in dev", async () => {
    await loadSlugModule(DEV_BASE);
    expect(slugModule.conferenceUrl("wsc2026")).toBe("/wsc2026/");
  });

  test("builds a prefixed conference URL when deployed under a subpath", async () => {
    await loadSlugModule(DEPLOYED_BASE);
    expect(slugModule.conferenceUrl("wsc2026")).toBe(
      "/conference-demo/wsc2026/"
    );
  });
});
