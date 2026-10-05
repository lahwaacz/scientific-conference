import {
  clearProgramDirty,
  isProgramDirty,
  markProgramDirty,
} from "./programRefresh";

describe("programRefresh dirty flag", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test("is false before anything is marked", () => {
    expect(isProgramDirty()).toBe(false);
  });

  test("is true after markProgramDirty", () => {
    markProgramDirty();
    expect(isProgramDirty()).toBe(true);
    expect(localStorage.getItem("program_needs_refresh_global")).not.toBeNull();
  });

  test("is false again after clearProgramDirty", () => {
    markProgramDirty();
    clearProgramDirty();
    expect(isProgramDirty()).toBe(false);
  });
});

describe("programRefresh dirty flag per conference", () => {
  // programRefresh reads the conference slug from the conferenceSlug module
  // singleton, so each test reloads that module (vi.resetModules), points
  // window.location at a slug-bearing path, inits, then imports the fresh
  // programRefresh instance bound to it.
  function setLocation(pathname) {
    Object.defineProperty(window, "location", {
      configurable: true,
      writable: true,
      value: { pathname },
    });
  }

  async function loadDirtyModule(pathname) {
    vi.resetModules();
    setLocation(pathname);
    const slugModule = await import("./conferenceSlug");
    slugModule.initConferenceSlug();
    return import("./programRefresh");
  }

  beforeEach(() => {
    localStorage.clear();
  });

  test("keys carry the conference slug", async () => {
    const dirty = await loadDirtyModule("/wsc2026/");
    dirty.markProgramDirty();
    expect(dirty.isProgramDirty()).toBe(true);
    expect(
      localStorage.getItem("program_needs_refresh_wsc2026")
    ).not.toBeNull();
  });

  test("marking one conference does not dirty another", async () => {
    const confA = await loadDirtyModule("/wsc2026/");
    confA.markProgramDirty();
    expect(confA.isProgramDirty()).toBe(true);

    const confB = await loadDirtyModule("/wsc2027/");
    expect(confB.isProgramDirty()).toBe(false);
  });

  test("clearing one conference leaves the other intact", async () => {
    const confA = await loadDirtyModule("/wsc2026/");
    confA.markProgramDirty();
    const confB = await loadDirtyModule("/wsc2027/");
    confB.markProgramDirty();

    const againA = await loadDirtyModule("/wsc2026/");
    againA.clearProgramDirty();
    expect(againA.isProgramDirty()).toBe(false);

    const againB = await loadDirtyModule("/wsc2027/");
    expect(againB.isProgramDirty()).toBe(true);
  });
});
