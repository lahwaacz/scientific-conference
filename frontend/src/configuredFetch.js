const originalFetch = global.fetch;

export const applyBaseUrlToFetch = (baseUrl) => {
  global.fetch = (url, options) => {
    if (url.startsWith("http")) {
      return originalFetch(url, options);
    }
    const finalUrl = baseUrl + url;
    return originalFetch(finalUrl, options);
  };
};
