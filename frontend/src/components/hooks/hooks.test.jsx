import { renderHook, waitFor } from "@testing-library/react";
import { useConferenceExists } from "./useConferenceExists";
import { useConferenceInfo } from "./useConferenceInfo";
import { useLockBodyScroll } from "./useLockBodyScroll";
import { initConferenceSlug } from "../../utils/conferenceSlug";

function setLocation(pathname) {
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: { pathname, hash: "", reload: vi.fn() },
  });
}

describe("useConferenceInfo", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  test("returns the fetched conference info", async () => {
    const info = { title: "Workshop 2026" };
    globalThis.fetch.mockResolvedValueOnce({
      json: async () => info,
    });

    const { result } = renderHook(() => useConferenceInfo());
    expect(result.current).toBeNull();

    await waitFor(() => expect(result.current).toEqual(info));
  });

  test("swallows fetch failures and keeps info null", async () => {
    globalThis.fetch.mockRejectedValueOnce(new Error("offline"));

    const { result } = renderHook(() => useConferenceInfo());

    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(result.current).toBeNull();
  });
});

describe("useLockBodyScroll", () => {
  afterEach(() => {
    document.body.style.cssText = "";
  });

  test("locks the body at the current scroll offset and restores it", () => {
    Object.defineProperty(window, "scrollY", {
      configurable: true,
      writable: true,
      value: 250,
    });

    const { rerender, unmount } = renderHook(
      ({ locked }) => useLockBodyScroll(locked),
      { initialProps: { locked: true } }
    );

    expect(document.body.style.position).toBe("fixed");
    expect(document.body.style.top).toBe("-250px");
    expect(document.body.style.overflow).toBe("hidden");

    rerender({ locked: false });
    expect(document.body.style.position).toBe("");
    expect(document.body.style.top).toBe("");

    unmount();
  });
});

describe("useConferenceExists", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
    setLocation("/");
    initConferenceSlug();
  });

  afterEach(() => {
    setLocation("/");
    initConferenceSlug();
  });

  test("no slug in the path stays 'landing' without fetching", () => {
    const { result } = renderHook(() => useConferenceExists());

    expect(result.current).toBe("landing");
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  test("a slug present in the conference list resolves to 'ok'", async () => {
    setLocation("/wsc2026/");
    initConferenceSlug();
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ slug: "wsc2026" }, { slug: "other" }],
    });

    const { result } = renderHook(() => useConferenceExists());
    expect(result.current).toBe("checking");

    await waitFor(() => expect(result.current).toBe("ok"));
  });

  test("a slug missing from the conference list resolves to 'missing'", async () => {
    setLocation("/ghost-conference/");
    initConferenceSlug();
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ slug: "wsc2026" }],
    });

    const { result } = renderHook(() => useConferenceExists());

    await waitFor(() => expect(result.current).toBe("missing"));
  });

  test("an HTTP error fails open to 'ok'", async () => {
    setLocation("/wsc2026/");
    initConferenceSlug();
    globalThis.fetch.mockResolvedValueOnce({ ok: false });

    const { result } = renderHook(() => useConferenceExists());

    await waitFor(() => expect(result.current).toBe("ok"));
  });

  test("a transport error fails open to 'ok'", async () => {
    setLocation("/wsc2026/");
    initConferenceSlug();
    globalThis.fetch.mockRejectedValueOnce(new Error("offline"));

    const { result } = renderHook(() => useConferenceExists());

    await waitFor(() => expect(result.current).toBe("ok"));
  });

  test("a non-array payload fails open to 'ok'", async () => {
    setLocation("/wsc2026/");
    initConferenceSlug();
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ detail: "unexpected shape" }),
    });

    const { result } = renderHook(() => useConferenceExists());

    await waitFor(() => expect(result.current).toBe("ok"));
  });
});
