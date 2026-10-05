import { useEffect } from "react";

export function useLockBodyScroll(isLocked) {
  useEffect(() => {
    if (!isLocked) return undefined;

    const scrollY = window.scrollY;
    document.body.style.position = "fixed";
    document.body.style.top = `-${scrollY}px`;
    document.body.style.width = "100%";
    document.body.style.overflow = "hidden";

    return () => {
      const top = parseInt(document.body.style.top || "0", 10);
      document.body.style.position = "";
      document.body.style.top = "";
      document.body.style.width = "";
      document.body.style.overflow = "";
      // Bootstrap sets `scroll-behavior: smooth` on :root; without
      // forcing instant scrolling this restore animates from the top
      // of the page after the position reset already snapped there.
      const html = document.documentElement;
      html.style.scrollBehavior = "auto";
      window.scrollTo(0, -top);
      html.style.scrollBehavior = "";
    };
  }, [isLocked]);
}
