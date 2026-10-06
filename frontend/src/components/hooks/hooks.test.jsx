import {
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
} from "@testing-library/react";
import { Link } from "react-router-dom";
import { useConferenceExists } from "./useConferenceExists";
import { useConferenceInfo } from "./useConferenceInfo";
import { useLockBodyScroll } from "./useLockBodyScroll";
import { useUnsavedChangesGuard } from "./useUnsavedChangesGuard";
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

  test("unlocks by restoring the saved offset without smooth scrolling", () => {
    Object.defineProperty(window, "scrollY", {
      configurable: true,
      writable: true,
      value: 250,
    });
    const scrollTo = vi.fn();
    window.scrollTo = scrollTo;

    const { rerender } = renderHook(({ locked }) => useLockBodyScroll(locked), {
      initialProps: { locked: true },
    });

    rerender({ locked: false });

    expect(scrollTo).toHaveBeenCalledWith(0, 250);
    // The instant-scroll override must not leak past the restore.
    expect(document.documentElement.style.scrollBehavior).toBe("");
  });

  test("does not touch the scroll position while unlocked", () => {
    const scrollTo = vi.fn();
    window.scrollTo = scrollTo;

    renderHook(({ locked }) => useLockBodyScroll(locked), {
      initialProps: { locked: false },
    });

    expect(scrollTo).not.toHaveBeenCalled();
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

  test("no slug in the path stays 'unknown' without fetching", () => {
    const { result } = renderHook(() => useConferenceExists());

    expect(result.current).toBe("unknown");
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  test("a slug present in the conference list resolves to 'exists'", async () => {
    setLocation("/wsc2026/");
    initConferenceSlug();
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ slug: "wsc2026" }, { slug: "other" }],
    });

    const { result } = renderHook(() => useConferenceExists());
    expect(result.current).toBe("unknown");

    await waitFor(() => expect(result.current).toBe("exists"));
  });

  test("a slug missing from the conference list resolves to 'absent'", async () => {
    setLocation("/ghost-conference/");
    initConferenceSlug();
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ slug: "wsc2026" }],
    });

    const { result } = renderHook(() => useConferenceExists());

    await waitFor(() => expect(result.current).toBe("absent"));
  });

  test("an HTTP error fails open to 'exists'", async () => {
    setLocation("/wsc2026/");
    initConferenceSlug();
    globalThis.fetch.mockResolvedValueOnce({ ok: false });

    const { result } = renderHook(() => useConferenceExists());

    await waitFor(() => expect(result.current).toBe("exists"));
  });

  test("a transport error fails open to 'exists'", async () => {
    setLocation("/wsc2026/");
    initConferenceSlug();
    globalThis.fetch.mockRejectedValueOnce(new Error("offline"));

    const { result } = renderHook(() => useConferenceExists());

    await waitFor(() => expect(result.current).toBe("exists"));
  });

  test("a non-array payload fails open to 'exists'", async () => {
    setLocation("/wsc2026/");
    initConferenceSlug();
    globalThis.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ detail: "unexpected shape" }),
    });

    const { result } = renderHook(() => useConferenceExists());

    await waitFor(() => expect(result.current).toBe("exists"));
  });
});

describe("useUnsavedChangesGuard", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.location.hash = "";
  });

  function renderGuard(dirty) {
    return renderHook(
      ({ isDirty }) =>
        useUnsavedChangesGuard(
          isDirty,
          "Leave the form? Unsaved changes will be lost."
        ),
      { initialProps: { isDirty: dirty } }
    );
  }

  test("a dirty form prevents beforeunload", () => {
    const { rerender } = renderGuard(false);
    rerender({ isDirty: true });

    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
  });

  test("a clean form does not prevent beforeunload", () => {
    renderGuard(false);

    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
  });

  test("declining browser back stops the navigation before the router", () => {
    window.location.hash = "#/registration";
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const routerListener = vi.fn();
    window.addEventListener("popstate", routerListener);

    const { rerender } = renderGuard(false);
    rerender({ isDirty: true });

    // The module-level guard listener is registered before this test's
    // listener, mirroring the router: jsdom fires no popstate on hash
    // assignment, so dispatch like the browser would for a back press.
    window.location.hash = "#/program";
    window.dispatchEvent(new Event("popstate"));
    expect(window.location.hash).toBe("#/registration");
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(routerListener).not.toHaveBeenCalled();

    // The restore fires its own popstate: consumed, no confirm loop.
    window.dispatchEvent(new Event("popstate"));
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(window.location.hash).toBe("#/registration");
    window.removeEventListener("popstate", routerListener);
  });

  test("accepting browser back lets the router process the navigation", () => {
    window.location.hash = "#/registration";
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const routerListener = vi.fn();
    window.addEventListener("popstate", routerListener);

    const { rerender } = renderGuard(false);
    rerender({ isDirty: true });

    window.location.hash = "#/program";
    window.dispatchEvent(new Event("popstate"));

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(routerListener).toHaveBeenCalledTimes(1);
    expect(window.location.hash).toBe("#/program");
    window.removeEventListener("popstate", routerListener);
  });

  test("a clean form lets popstate run without confirming", () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const routerListener = vi.fn();
    window.addEventListener("popstate", routerListener);

    renderGuard(false);

    window.location.hash = "#/program";
    window.dispatchEvent(new Event("popstate"));

    expect(confirm).not.toHaveBeenCalled();
    expect(routerListener).toHaveBeenCalledTimes(1);
    window.removeEventListener("popstate", routerListener);
  });

  test("declining a link click cancels the navigation", () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const onNavigate = vi.fn();

    const { rerender } = renderGuard(false);
    rerender({ isDirty: true });

    render(
      <Link to="#/program" onClick={onNavigate}>
        Program
      </Link>
    );
    fireEvent.click(screen.getByRole("link", { name: "Program" }));

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(onNavigate).not.toHaveBeenCalled();
  });

  test("accepting a link click lets the navigation run", () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const onNavigate = vi.fn();

    const { rerender } = renderGuard(false);
    rerender({ isDirty: true });

    render(
      <Link to="#/program" onClick={onNavigate}>
        Program
      </Link>
    );
    fireEvent.click(screen.getByRole("link", { name: "Program" }));

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(onNavigate).toHaveBeenCalledTimes(1);
  });

  test("a clean form lets link clicks run without confirming", () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const onNavigate = vi.fn();

    renderGuard(false);

    render(
      <Link to="#/program" onClick={onNavigate}>
        Program
      </Link>
    );
    fireEvent.click(screen.getByRole("link", { name: "Program" }));

    expect(confirm).not.toHaveBeenCalled();
    expect(onNavigate).toHaveBeenCalledTimes(1);
  });
});
