const originalFetch = globalThis.fetch;

export const applyBaseUrlToFetch = (baseUrl) => {
  globalThis.fetch = (url, options) => {
    if (url.startsWith("http")) {
      return originalFetch(url, options);
    }
    const finalUrl = baseUrl + url;
    return originalFetch(finalUrl, options);
  };
};
