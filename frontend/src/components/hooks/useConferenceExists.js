import { useEffect, useState } from "react";
import { buildApiUrl } from "../../utils/api";
import { getConferenceSlug } from "../../utils/conferenceSlug";

/**
 * Guards the conference shell against path slugs that match no real
 * conference. States:
 *  - "landing":  no slug in the path (the landing page)
 *  - "checking": slug present, existence not resolved yet
 *  - "missing":  slug matches no conference -> render the landing page
 *  - "ok":       slug is a real conference
 *
 * "missing" is decided ONLY when the public conference list loads and
 * lacks the slug; every failure mode (HTTP error, bad payload, offline)
 * fails open to "ok" so a backend hiccup keeps the site rendering as
 * before instead of blanking it.
 */
export function useConferenceExists() {
  const [state, setState] = useState(() =>
    getConferenceSlug() === null ? "landing" : "checking"
  );

  useEffect(() => {
    const slug = getConferenceSlug();
    if (slug === null) return undefined;

    let cancelled = false;
    // Global allowlisted endpoint: served unscoped even with a slug set.
    fetch(buildApiUrl("/api/conferences/"))
      .then((response) => (response.ok ? response.json() : null))
      .then((cards) => {
        if (cancelled) return;
        const missing =
          Array.isArray(cards) && !cards.some((c) => c?.slug === slug);
        setState(missing ? "missing" : "ok");
      })
      .catch(() => {
        if (!cancelled) setState("ok");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
