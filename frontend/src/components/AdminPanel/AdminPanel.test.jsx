import { render, screen } from "@testing-library/react";

/**
 * The cue under the title shows which conference this admin session is
 * bound to (multi-conference): the title comes from the merged
 * conference-info payload, the slug from the conferenceSlug singleton
 * captured from window.location.pathname. Tests therefore reload the
 * module graph, point the location at a slug-bearing path, init the
 * slug, and only then import the component so its whole import chain
 * binds to the fresh slug state (same pattern as programRefresh.test.js
 * and Landing.test.jsx). Both data requests (fetchWithAuth for
 * admin-panel, plain fetch for conference-info) go through the mocked
 * globalThis.fetch.
 */
function setLocation(pathname) {
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: { pathname },
  });
}

async function renderAdminPanel(pathname = "/wsc2026/") {
  vi.resetModules();
  setLocation(pathname);
  const slugModule = await import("../../utils/conferenceSlug");
  slugModule.initConferenceSlug();
  const { default: AdminPanel } = await import("./AdminPanel");
  render(<AdminPanel />);
}

function mockFetches({ title = "Workshop on Scientific Computing 2026" } = {}) {
  globalThis.fetch = vi.fn((url) => {
    if (url.includes("conference-info")) {
      return Promise.resolve({ ok: true, json: async () => ({ title }) });
    }
    return Promise.resolve({ ok: true, json: async () => ({}) });
  });
}

describe("AdminPanel conference cue", () => {
  beforeEach(() => {
    localStorage.clear();
    mockFetches();
  });

  test("renders the conference title and slug under the title", async () => {
    await renderAdminPanel();

    expect(
      await screen.findByText(
        "Conference: Workshop on Scientific Computing 2026 (wsc2026)"
      )
    ).toBeInTheDocument();
  });

  test("fetches conference-info through the slug-scoped API prefix", async () => {
    await renderAdminPanel();

    await screen.findByText(/Conference: .* \(wsc2026\)/);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/wsc2026/conference-info/"
    );
  });

  test("shows a placeholder title while conference-info loads", async () => {
    await renderAdminPanel();

    expect(screen.getByText("Conference: … (wsc2026)")).toBeInTheDocument();
    expect(
      await screen.findByText(
        "Conference: Workshop on Scientific Computing 2026 (wsc2026)"
      )
    ).toBeInTheDocument();
  });
});
