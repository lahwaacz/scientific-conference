/**
 * Runtime app configuration, served from public/app-config.js. The
 * container image's entrypoint overwrites that file at startup from the
 * BASE_PATH / API_BASE env vars; in dev and non-containerized builds it
 * stays empty and the Vite env values remain the source of truth.
 */
export function appConfig() {
  return globalThis.__APP_CONFIG__ ?? {};
}
