// Default runtime app configuration: intentionally empty. Container
// deployments overwrite this file at startup (docker-entrypoint.d/
// writes it from the BASE_PATH / API_BASE env vars); the app falls
// back to its build-time values while it stays empty.
window.__APP_CONFIG__ = {};
