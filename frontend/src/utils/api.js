import { appConfig } from "./appConfig";
import { conferenceApiPrefix } from "./conferenceSlug";

let isRefreshing = false;
let failedQueue = [];
const RUNTIME_API_BASE = appConfig().apiBase;
const RAW_API_BASE_URL =
  (RUNTIME_API_BASE ?? import.meta.env.VITE_BACKEND_API_BASE_URL) ||
  "http://localhost:8000";
export const API_BASE_URL = RAW_API_BASE_URL.replace(/\/$/, "");

const GLOBAL_API_PREFIXES = ["/api/auth/", "/api/conferences/"];
const CSRF_COOKIE_NAME = "csrftoken";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCookie(name) {
  const prefix = `${name}=`;
  const match = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  return match ? decodeURIComponent(match.slice(prefix.length)) : "";
}

function reloadAppAtHomePage() {
  window.location.hash = "/";
  window.location.reload();
}

const processQueue = (error) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });

  failedQueue = [];
};

export function buildApiUrl(path) {
  if (!path) return API_BASE_URL;
  if (/^https?:\/\//i.test(path)) return path;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  const isGlobal = GLOBAL_API_PREFIXES.some(
    (p) => normalized === p.slice(0, -1) || normalized.startsWith(p)
  );
  const prefix = conferenceApiPrefix();
  if (!isGlobal && prefix && normalized.startsWith("/api/")) {
    return `${API_BASE_URL}${prefix}${normalized.slice(4)}`;
  }
  return `${API_BASE_URL}${normalized}`;
}

function buildHeaders(options) {
  const isFormData = options.body instanceof FormData;
  const headers = { ...options.headers };
  const method = (options.method || "GET").toUpperCase();
  const csrfToken = UNSAFE_METHODS.has(method)
    ? readCookie(CSRF_COOKIE_NAME)
    : "";

  if (csrfToken && !headers["X-CSRFToken"] && !headers["x-csrftoken"]) {
    headers["X-CSRFToken"] = csrfToken;
  }

  if (!isFormData) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  return headers;
}

// Path part of the API base without the origin or surrounding slashes
// ("conference" for "/conference", "api/conference" for
// "https://host/api/conference"). Media URLs from the backend already carry
// RELATIVE_URL_ROOT ("<root>/media/x.png"), so this prefix must be stripped
// before joining onto the same base instead of hardcoding a deployment name.
const API_BASE_PATH = API_BASE_URL.replace(
  /^[a-z][a-z0-9+.-]*:\/\/[^/]+/i,
  ""
).replace(/^\/+|\/+$/g, "");

export function buildMediaUrl(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;

  const base = API_BASE_URL.replace(/\/$/, "");
  let cleanPath = path.trim().replace(/^\/+/, "");

  if (API_BASE_PATH && cleanPath.startsWith(`${API_BASE_PATH}/`)) {
    cleanPath = cleanPath.slice(API_BASE_PATH.length + 1);
  }

  return `${base}/${cleanPath}`;
}

export async function refreshAccessToken({ reloadOnFailure = true } = {}) {
  try {
    const response = await fetch(buildApiUrl("/api/auth/refresh/"), {
      method: "POST",
      credentials: "include",
      headers: buildHeaders({ method: "POST" }),
    });

    if (!response.ok) {
      if (reloadOnFailure) {
        reloadAppAtHomePage();
      }
      return false;
    }

    return true;
  } catch (error) {
    console.error("Token refresh failed:", error);
    if (reloadOnFailure) {
      reloadAppAtHomePage();
    }
    return false;
  }
}

function fetchWithCookies(url, options) {
  return fetch(url, {
    credentials: "include",
    ...options,
    headers: buildHeaders(options),
  });
}

export async function fetchWithAuth(url, options = {}) {
  const { skipRefresh = false, ...requestOptions } = options;
  const finalUrl = buildApiUrl(url);
  const response = await fetchWithCookies(finalUrl, requestOptions);

  if (response.status === 401 && !skipRefresh) {
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(() => fetchWithCookies(finalUrl, requestOptions));
    }

    isRefreshing = true;

    try {
      const refreshed = await refreshAccessToken();

      if (refreshed) {
        processQueue(null);
        return fetchWithCookies(finalUrl, requestOptions);
      }

      processQueue(new Error("Token refresh failed"));
      return response;
    } finally {
      isRefreshing = false;
    }
  }

  return response;
}
