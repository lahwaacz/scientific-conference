import { renderHook, waitFor } from "@testing-library/react";
import { useConferenceInfo } from "./useConferenceInfo";
import { useLockBodyScroll } from "./useLockBodyScroll";

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
