# Deployment Guide for the Conference Management System

This document describes how the conference management system is deployed. It covers the container images, their runtime configuration, and the requirements the reverse proxy in front of them must fulfill. Administrative workflows are described separately in [admin_guide.md](./admin_guide.md).

## Container Images

The system consists of two deployables, coupled only through the REST API: the Django backend and the React frontend, both built as container images.

The frontend image is universal: it contains no deployment-specific values and works under any base path. It is configured at startup with the `BASE_PATH` environment variable (the URL prefix it is served under, for example `/conference-demo`); the optional `API_BASE` variable overrides where API requests are sent and defaults to the same origin under the base path. The image entrypoint writes these values into `app-config.js`, which the app reads before its build-time values. The bundled nginx serves the app, its assets and the media volumes at any path depth, so the same image works at the root or under any other prefix without a rebuild.

The backend image runs gunicorn (WSGI) and expects its URL prefix through the `RELATIVE_URL_ROOT` environment variable (for example `conference-demo/`); every route, the static URL, the media URL and the cookie paths are derived from it. It never serves static or media files itself. At startup it collects the static files of Django and its apps into `DJANGO_STATIC_ROOT` (for example `/data/static`), and media uploads go to `DJANGO_MEDIA_ROOT` (for example `/data/media`) — both volumes are served externally by the frontend container, the static files under the `back-static/` prefix (set `DJANGO_STATIC_URL` to `<root>/back-static/`).

The backend container runs as a non-root user (uid and gid 1000). Every volume it writes to — `DJANGO_STATIC_ROOT`, `DJANGO_MEDIA_ROOT` and the SQLite database at `DJANGO_DB_PATH` — must be writable by that user (for a host bind mount, `chown 1000:1000` the directory).

The backend also requires `DJANGO_SECRET_KEY` — the key that signs sessions and JWTs — in its environment, for example from a Kubernetes Secret. The image contains no default value: if the variable is missing, the container exits at startup instead of signing tokens with a publicly known key. `DJANGO_DEBUG` defaults to `False` and should only be enabled for debugging.

## Reverse Proxy Requirements

For the per-conference addresses to work, the reverse proxy in front of the deployment must serve the frontend entry page for every path under the application root that is not a real file. Requests to `api/`, `admin/`, and `media/` under the root must keep being routed to the backend as they are today. Every other path, especially `<root>/<slug>/`, must return the frontend `index.html`, which then opens the conference named in the address.

Example nginx rule for the demo deployment:

```nginx
location /conference-demo/ {
    try_files $uri /conference-demo/index.html;
}
```

Existing files (styles, scripts, images) are found first; everything else falls back to the entry page. Backend locations such as `location /conference-demo/api/` are longer prefixes and keep precedence automatically. Without this fallback, the landing page keeps working, but every conference address such as `<root>/wsc2026/` returns an error instead of the conference website.

## Demo Deployment

The demo runs at `https://mmg-webapps.fjfi.cvut.cz/conference-demo/`: the root shows the landing page, and each conference is available at its own address under the root, for example `https://mmg-webapps.fjfi.cvut.cz/conference-demo/wsc2026/`.
