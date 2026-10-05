/**
 * Conference slug singleton (multi-conference support).
 *
 * The slug is captured ONCE from window.location.pathname at app startup —
 * HashRouter's useLocation only sees the hash, never the path prefix, so
 * react-router hooks must not be used here. The deploy path prefix comes
 * from import.meta.env.BASE_URL (Vite base; "./" in dev, "/conference-demo/"
 * in the subpath deployment).
 */

let conferenceSlug = null;

/**
 * Deployment base path: "/" in dev, "/<subpath>/" when built with a Vite
 * `base` like "/conference-demo/". The dev default "./" means "any
 * subpath", i.e. "/".
 */
export function getDeployedBasePath() {
  const base = import.meta.env.BASE_URL;
  if (!base || base === "/" || base === "./") {
    return "/";
  }
  const withLeadingSlash = base.startsWith("/") ? base : `/${base}`;
  return withLeadingSlash.endsWith("/")
    ? withLeadingSlash
    : `${withLeadingSlash}/`;
}

function parseSlugFromPathname(pathname) {
  const basePath = getDeployedBasePath();
  let rest = pathname;
  if (basePath !== "/") {
    if (rest.startsWith(basePath)) {
      rest = rest.slice(basePath.length);
    } else if (rest === basePath.slice(0, -1)) {
      // Bare prefix without its trailing slash ("/conference-demo").
      rest = "";
    }
  }
  // Collapse duplicate/leading/trailing slashes: first non-empty segment.
  const [firstSegment] = rest.split("/").filter((segment) => segment !== "");
  return firstSegment ?? null;
}

/**
 * Capture the conference slug from the current URL. Called once in
 * main.jsx (mirrors applyBaseUrlToFetch), before the app renders.
 */
export function initConferenceSlug() {
  // undefined-safe: api.test.js mocks location as { hash, reload } only.
  const pathname = window?.location?.pathname ?? "/";
  conferenceSlug = parseSlugFromPathname(pathname);
}

/** string | null — null means the landing page (no conference selected). */
export function getConferenceSlug() {
  return conferenceSlug;
}

/** "/api/<slug>" once a slug is captured, null on the landing page. */
export function conferenceApiPrefix() {
  const slug = getConferenceSlug();
  return slug === null ? null : `/api/${slug}`;
}

export function isLandingPage() {
  return getConferenceSlug() === null;
}

/** URL of a conference site: `${getDeployedBasePath()}${slug}/`. */
export function conferenceUrl(slug) {
  return `${getDeployedBasePath()}${slug}/`;
}
