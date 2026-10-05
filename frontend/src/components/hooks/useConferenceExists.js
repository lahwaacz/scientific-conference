import { useEffect, useState } from "react";
import { buildApiUrl } from "../../utils/api";
import { getConferenceSlug } from "../../utils/conferenceSlug";

/**
 * Resolves whether the path slug matches a real conference. States:
 *  - "unknown": the check has not resolved yet
 *  - "exists":  the conference is confirmed real
 *  - "absent":  the conference list loaded and lacks the slug
 *
 * "absent" is decided ONLY when the public conference list loads and
 * lacks the slug; every failure mode (HTTP error, bad payload, offline)
 * fails open to "exists" so a backend hiccup keeps the site rendering
 * instead of blanking it. A missing path slug is not this hook's
 * concern — App renders the landing page before consulting it.
 */
export function useConferenceExists() {
  const [state, setState] = useState("unknown");

  useEffect(() => {
    const slug = getConferenceSlug();
    if (slug === null) return undefined;

    let cancelled = false;
    // Global allowlisted endpoint: served unscoped even with a slug set.
    fetch(buildApiUrl("/api/conferences/"))
      .then((response) => (response.ok ? response.json() : null))
      .then((cards) => {
        if (cancelled) return;
        const absent =
          Array.isArray(cards) && !cards.some((c) => c?.slug === slug);
        setState(absent ? "absent" : "exists");
      })
      .catch(() => {
        if (!cancelled) setState("exists");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
