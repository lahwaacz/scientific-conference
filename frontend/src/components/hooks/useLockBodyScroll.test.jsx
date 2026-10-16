import { renderHook } from "@testing-library/react";
import { useLockBodyScroll } from "./useLockBodyScroll";

function setScrollY(value) {
  Object.defineProperty(window, "scrollY", {
    configurable: true,
    writable: true,
    value,
  });
}

describe("useLockBodyScroll", () => {
  beforeEach(() => {
    // jsdom implements neither window.scrollTo nor a real scroll offset.
    window.scrollTo = vi.fn();
    setScrollY(0);
    document.body.style.cssText = "";
    document.documentElement.style.scrollBehavior = "";
  });

  afterEach(() => {
    document.body.style.cssText = "";
    document.documentElement.style.scrollBehavior = "";
  });

  test("locks the body at the current scroll offset and restores it", () => {
    setScrollY(250);

    const { rerender, unmount } = renderHook(
      ({ locked }) => useLockBodyScroll(locked),
      { initialProps: { locked: true } }
    );

    expect(document.body.style.position).toBe("fixed");
    expect(document.body.style.top).toBe("-250px");
    expect(document.body.style.width).toBe("100%");
    expect(document.body.style.overflow).toBe("hidden");

    rerender({ locked: false });

    expect(document.body.style.position).toBe("");
    expect(document.body.style.top).toBe("");
    expect(document.body.style.width).toBe("");
    expect(document.body.style.overflow).toBe("");

    unmount();
  });

  test("unlocks by restoring the saved offset without smooth scrolling", () => {
    setScrollY(250);

    const { rerender } = renderHook(({ locked }) => useLockBodyScroll(locked), {
      initialProps: { locked: true },
    });

    rerender({ locked: false });

    expect(window.scrollTo).toHaveBeenCalledWith(0, 250);
    // The instant-scroll override must not leak past the restore.
    expect(document.documentElement.style.scrollBehavior).toBe("");
  });

  test("preserves an outer lock written before mounting", () => {
    // EditSubmissionModal sets `overflow: hidden` on its own mount;
    // unmounting a nested lock (PhotoCropModal) must not destroy it.
    document.body.style.overflow = "hidden";

    const { unmount } = renderHook(() => useLockBodyScroll(true));
    unmount();

    expect(document.body.style.overflow).toBe("hidden");
  });

  test("does nothing when isLocked is false", () => {
    const { unmount } = renderHook(() => useLockBodyScroll(false));

    expect(document.body.style.cssText).toBe("");
    expect(window.scrollTo).not.toHaveBeenCalled();

    unmount();

    expect(document.body.style.cssText).toBe("");
    expect(window.scrollTo).not.toHaveBeenCalled();
  });
});
