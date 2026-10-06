import { useEffect } from "react";

let activeGuard = null;

/**
 * Guards a form with unsubmitted changes against accidental loss.
 *
 * While `isDirty` is true:
 *  - closing the tab or navigating to another site triggers the
 *    browser's native leave-site confirmation (beforeunload);
 *  - in-app link clicks are intercepted in the capture phase:
 *    react-router Link navigates via history.pushState, which fires
 *    no window events, so the anchor click itself is confirmed and
 *    cancelled before React's handlers run;
 *  - browser back/forward is intercepted on popstate. This listener
 *    must be registered at module load, BEFORE the router mounts its
 *    own popstate listener: the browser has already changed the URL
 *    when popstate fires, so declining must stopImmediatePropagation
 *    (the router never sees the navigation and the form never
 *    unmounts) and put the hash back.
 *
 * The consumer must clear `isDirty` (e.g. reset the form) on successful
 * submit so the guard detaches.
 */
if (typeof window !== "undefined" && !window.__unsavedChangesGuard) {
  window.__unsavedChangesGuard = true;
  window.addEventListener("popstate", (event) => {
    if (!activeGuard) return;
    if (window.location.hash === activeGuard.guardHash) {
      // Our own restore, or a no-op popstate to the guarded hash.
      return;
    }
    if (window.confirm(activeGuard.message)) return;
    event.stopImmediatePropagation();
    window.location.hash = activeGuard.guardHash;
  });
}

export function useUnsavedChangesGuard(isDirty, message) {
  useEffect(() => {
    if (!isDirty) return undefined;

    const handleBeforeUnload = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };

    const handleClickCapture = (event) => {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }
      const anchor = event.target?.closest?.("a");
      if (!anchor) return;
      if (!anchor.getAttribute("href")?.startsWith("#")) return;
      if (window.confirm(message)) return;
      event.preventDefault();
      event.stopPropagation();
    };

    activeGuard = { message, guardHash: window.location.hash };

    window.addEventListener("beforeunload", handleBeforeUnload);
    document.addEventListener("click", handleClickCapture, true);
    return () => {
      activeGuard = null;
      window.removeEventListener("beforeunload", handleBeforeUnload);
      document.removeEventListener("click", handleClickCapture, true);
    };
  }, [isDirty, message]);
}
