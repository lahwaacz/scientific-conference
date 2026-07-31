let isRefreshing = false;
let failedQueue = [];

const RAW_API_BASE_URL =
  process.env.REACT_APP_BACKEND_API_BASE_URL ||
  "http://localhost:8000";

export const API_BASE_URL = RAW_API_BASE_URL.replace(/\/$/, "");

function reloadAppAtHomePage() {
  window.location.hash = "/";
  window.location.reload();
}

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

export function buildApiUrl(path) {
  if (!path) return API_BASE_URL;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function buildHeaders(options, token) {
  const isFormData = options.body instanceof FormData;

  return {
    ...options.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(isFormData
      ? {}
      : {
          "Content-Type":
            options.headers?.["Content-Type"] || "application/json",
        }),
  };
}

export function buildMediaUrl(path) {
  if (!path) return '';
  if (/^https?:\/\//i.test(path)) return path;

  const base = API_BASE_URL.replace(/\/$/, '');
  let cleanPath = path.trim().replace(/^\/+/, '');

  if (cleanPath.startsWith('conference-demo/')) {
    cleanPath = cleanPath.replace(/^conference-demo\//, '');
  }

  return `${base}/${cleanPath}`;
}

export async function refreshAccessToken() {
  const refreshToken = localStorage.getItem("refresh_token");

  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(buildApiUrl("/api/auth/refresh/"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        refresh: refreshToken,
      }),
    });

    if (!response.ok) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      reloadAppAtHomePage();
      return null;
    }

    const data = await response.json();
    localStorage.setItem("access_token", data.access);
    return data.access;
  } catch (error) {
    console.error("Token refresh failed:", error);
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    reloadAppAtHomePage();
    return null;
  }
}

export async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem("access_token");
  const finalUrl = buildApiUrl(url);

  const response = await fetch(finalUrl, {
    ...options,
    headers: buildHeaders(options, token),
  });

  if (response.status === 401) {
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(newToken => {
        return fetch(finalUrl, {
          ...options,
          headers: buildHeaders(options, newToken),
        });
      });
    }

    isRefreshing = true;

    try {
      const newToken = await refreshAccessToken();

      if (newToken) {
        processQueue(null, newToken);

        return fetch(finalUrl, {
          ...options,
          headers: buildHeaders(options, newToken),
        });
      } else {
        processQueue(new Error("Token refresh failed"), null);
        reloadAppAtHomePage();
        return response;
      }
    } finally {
      isRefreshing = false;
    }
  }

  return response;
}
