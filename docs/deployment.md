# Deployment Guide for the Conference Management System

This document describes how the conference management system is deployed. It covers the container images, their runtime configuration, and the requirements the reverse proxy in front of them must fulfill. Administrative workflows are described separately in [admin_guide.md](./admin_guide.md).

## Container Images

The system consists of two deployables, coupled only through the REST API: the Django backend and the React frontend, both built as container images.

The frontend image is universal: it contains no deployment-specific values and works under any base path. It is configured at startup with the `BASE_PATH` environment variable (the URL prefix it is served under, for example `/conference`); the optional `API_BASE` variable overrides where API requests are sent and defaults to the same origin under the base path. The image entrypoint writes these values into `app-config.js`, which the app reads before its build-time values. The bundled nginx serves the app, its assets and the media volumes at any path depth, so the same image works at the root or under any other prefix without a rebuild. `BASE_PATH` and `API_BASE` are restricted to URL path/origin characters: the entrypoint exits instead of writing `app-config.js` if either value contains quotes, backslashes, angle brackets, whitespace or control characters.

The backend image runs gunicorn (WSGI) and expects its URL prefix through the `RELATIVE_URL_ROOT` environment variable (for example `conference/`); every route, the static URL, the media URL and the cookie paths are derived from it. It never serves static or media files itself. At startup it collects the static files of Django and its apps into `DJANGO_STATIC_ROOT` (for example `/data/static`), and media uploads go to `DJANGO_MEDIA_ROOT` (for example `/data/media`) — both volumes are served externally by the frontend container, the static files under the `back-static/` prefix (set `DJANGO_STATIC_URL` to `<root>/back-static/`).

The backend container runs as a non-root user (uid and gid 1000). Every volume it writes to — `DJANGO_STATIC_ROOT`, `DJANGO_MEDIA_ROOT` and the SQLite database at `DJANGO_DB_PATH` — must be writable by that user (for a host bind mount, `chown 1000:1000` the directory).

The backend also requires `DJANGO_SECRET_KEY` — the key that signs sessions and JWTs — in its environment, for example from a Kubernetes Secret. The image contains no default value: if the variable is missing, the container exits at startup instead of signing tokens with a publicly known key. `DJANGO_DEBUG` defaults to `False` and should only be enabled for debugging.

## Admin Login Configuration

Administrators sign in to the conference admin panel and to the Django administration with their university GitLab account. Username and password sign-in exists as a fallback and can be switched off per deployment. The backend selects the offered methods at startup from these environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `AUTH_PASSWORD_LOGIN_ENABLED` | `True` | Registers `/api/auth/login/` and shows the password forms in the SPA and on the Django administration sign-in page. Set to `False` to remove password sign-in everywhere. |
| `AUTH_GITLAB_LOGIN_ENABLED` | `True` | Enables the GitLab sign-in routes. Only takes effect when `GITLAB_CLIENT_ID` and `GITLAB_CLIENT_SECRET` are set; set to `False` to force GitLab off even when credentials are present. |
| `GITLAB_URL` | `https://gitlab.fjfi.cvut.cz` | The GitLab instance used for sign-in. |
| `GITLAB_CLIENT_ID` | (empty) | Client ID of the OAuth application registered in GitLab. |
| `GITLAB_CLIENT_SECRET` | (empty) | Client secret of the OAuth application; store it in the backend secret store next to `DJANGO_SECRET_KEY`. |
| `GITLAB_OAUTH_CALLBACK_URL` | (empty) | The SPA OAuth callback URL, for example `https://mmg-webapps.fjfi.cvut.cz/conference/oauth/callback`. Required when GitLab sign-in is enabled. |

At least one login method must be enabled: with both disabled the backend refuses to start, so a misconfigured deployment fails fast instead of locking every administrator out. Disabling a method is authoritative end to end: with `AUTH_PASSWORD_LOGIN_ENABLED=False` the allauth password backend is blocked too (the Django administration login form cannot authenticate with a password), and with `AUTH_GITLAB_LOGIN_ENABLED=False` the allauth GitLab provider routes return 404 even if credentials remain configured.

### GitLab Application Registration

Register one OAuth application in the university GitLab (`GITLAB_URL`, by default `https://gitlab.fjfi.cvut.cz`):

- Scope: `read_user` — the only scope the backend requests.
- Type: confidential client — the client secret never leaves the backend.
- Redirect URIs, exactly these (one per line; no wildcards, no trailing-slash mismatch):

```
https://mmg-webapps.fjfi.cvut.cz/conference/oauth/callback
https://mmg-webapps.fjfi.cvut.cz/conference/api/auth/allauth/gitlab/login/callback/
http://localhost:3000/oauth/callback
http://localhost:8000/api/auth/allauth/gitlab/login/callback/
```

The first URI of each pair serves the conference admin panel sign-in: it must equal `GITLAB_OAUTH_CALLBACK_URL`, because the backend sends it to GitLab as the redirect URI and GitLab rejects mismatches. The second URI serves the Django administration sign-in page (the allauth callback). The `localhost` entries are for local development. Copy the application's client ID and secret into the backend environment; the secret belongs in the backend secret store.

### How the Sign-In Works

Two administrative interfaces exist, and one GitLab sign-in opens both:

- The conference admin panel (the React application) authenticates with HttpOnly JWT cookies issued by the backend.
- The Django administration (used for creating conferences and similar tasks) authenticates with a browser session.

The admin panel flow: the login window asks the backend which methods are enabled (`GET /api/auth/config/`). For GitLab it fetches the authorization URL from `GET /api/auth/gitlab/authorize/?next=<slug>`, redirects the browser to GitLab, and GitLab redirects back to `<root>/oauth/callback` with an authorization code and state in the query string. The SPA exchanges the code at `POST /api/auth/gitlab/` and receives the user and the address of the conference admin panel; the response sets HttpOnly `conference-jwt-access` and `conference-jwt-refresh` cookies instead of returning tokens. The authorize response also sets a 10-minute HttpOnly nonce cookie; the code exchange verifies and consumes it, tying the sign-in to the browser that started it. The exchange also creates a Django session, so the Django administration at `<root>admin/` works in the same browser without signing in again. Conversely, signing in through the Django administration issues the same JWT cookies, so the website admin panel recognizes that session. Opening the Django administration directly redirects anonymous visitors to its own sign-in page, which offers the same methods.

Password sign-in (`POST /api/auth/login/`) sets the same HttpOnly cookies. When it is disabled, the route is not registered at all and both sign-in forms hide it.

Logout from the admin panel calls `POST /api/auth/logout/` with cookies only: the request must carry a valid access cookie, the backend reads and blacklists the refresh cookie, clears both JWT cookies and flushes the Django session. Logout from the Django administration clears and blacklists the JWT cookies too, so either sign-out ends both sessions. The SPA has no tokens to clear. The JWT cookies are HttpOnly and SameSite=Lax, scoped to the deployment subpath, and are Secure whenever `DJANGO_DEBUG` is false; the SPA sends them with `credentials: "include"`. Cookie-authenticated unsafe requests must also send `X-CSRFToken`, which the SPA reads from the non-HttpOnly `csrftoken` cookie. Keep SameSite at `Lax` or `Strict`; do not set it to `None` without adding explicit CSRF tokens.

No application-level login throttle is configured. Rate-limit both `/api/auth/...` sign-in paths and `<root>admin/` at the reverse proxy or WAF, keyed on the real client address. Refresh-token rotation writes rows to the blacklist table, so schedule `python manage.py flushexpiredtokens` periodically (for example daily).

### Authorizing Administrators

Sign-in only proves identity. Administrator rights are the `is_staff` flag on the user account, set manually in the Django administration; GitLab groups or projects are never consulted, and accounts are never connected by matching e-mail addresses. A first GitLab sign-in creates a non-staff user; promote it in the Django administration (**Users**, enable **Staff status**).

An existing staff user whose first GitLab sign-in created a separate new account can be linked back with the management command, run in the backend container:

```bash
uv run python manage.py link_gitlab_account <gitlab-username> <local-username> [--delete-orphan]
```

The command reassigns the GitLab social account to the local user and never modifies `is_staff`. `--delete-orphan` additionally deletes the account created by the first GitLab sign-in, unless a `Person` or a participant submission still references it (the command keeps the account and prints a warning in that case). The same reassignment can be done by hand in the Django administration under **Social accounts**.

### Rollout Order

Password sign-in remains usable for testing and demo deployments and as a break-glass path. When moving a deployment to GitLab-only sign-in:

1. Deploy with both methods enabled (`AUTH_PASSWORD_LOGIN_ENABLED=True`, GitLab credentials set, `GITLAB_OAUTH_CALLBACK_URL` configured).
2. Have every administrator sign in with GitLab once, and promote or link their accounts (see **Authorizing Administrators**).
3. Verify each administrator can reach both the admin panel and the Django administration through GitLab.
4. Set `AUTH_PASSWORD_LOGIN_ENABLED=False` and restart the backend. The password route, the SPA password form, and the Django administration password form disappear.

If GitLab becomes unavailable, re-enable the variable and restart the backend to restore password sign-in; the passwords of existing local accounts keep working.

## Upgrades and Backups

The backend entrypoint applies `manage.py migrate` every time the container starts. A new image therefore upgrades the database automatically, and an older image started against an already-upgraded database can fail: migrations may remove tables or columns that the old code still queries.

Always back up the SQLite database before deploying an image that contains new migrations. With the container stopped, copy the file at `DJANGO_DB_PATH`; a consistent copy can also be taken while it runs with `sqlite3 <db> ".backup <copy>"`. Migration `0031` merges the conference configuration into the `Conference` row and is irreversible — its reverse migration raises an error by design. Rolling back to an older image therefore means restoring the backup, not reversing the migration.

The GitLab sign-in adds the django-allauth and `django.contrib.sites` tables. Their migrations are additive (new tables only), run automatically at container start like every other migration, and do not touch existing conference data. Back up the database before deploying the image that introduces them, as with any image carrying new migrations; rolling back means restoring that backup (or the previous image) as usual.

## Reverse Proxy Requirements

For the per-conference addresses to work, the reverse proxy in front of the deployment must serve the frontend entry page for every path under the application root that is not a real file. Requests to `api/`, `admin/`, and `media/` under the root must keep being routed to the backend as they are today. Every other path, especially `<root>/<slug>/`, must return the frontend `index.html`, which then opens the conference named in the address.

Example nginx rule for a subpath deployment:

```nginx
location /conference/ {
    try_files $uri /conference/index.html;
}
```

Existing files (styles, scripts, images) are found first; everything else falls back to the entry page. Backend locations such as `location /conference/api/` are longer prefixes and keep precedence automatically. Without this fallback, the landing page keeps working, but every conference address such as `<root>/wsc2026/` returns an error instead of the conference website.

### GitLab Sign-In Routes

The GitLab sign-in adds one path that must reach the frontend: `<root>/oauth/callback`. GitLab redirects there with the authorization code and state in the query string (`GET <root>/oauth/callback?code=…&state=…`). The proxy must:

- serve the frontend `index.html` for this path (the SPA reads the query parameters and exchanges the code),
- pass the query string through unchanged, and
- not rewrite the path in any way (no trailing-slash redirect, no hostname canonicalization), because the redirect URI is registered in GitLab exactly and a mismatch makes GitLab reject the sign-in.

With the `try_files` rule above this works out of the box, as long as no other rule captures `oauth/` first. `/conference/api/auth/...` keeps routing to the backend through the existing `api/` rule.

The proxy must preserve the `Host` header and pass the original protocol in `X-Forwarded-Proto`. Set `DJANGO_USE_HTTPS=True` in production: the backend then trusts `X-Forwarded-Proto`, marks its cookies secure, and the sign-in pages generate HTTPS redirect URLs. `DJANGO_ALLOWED_HOSTS` must include the deployment host (`mmg-webapps.fjfi.cvut.cz`), and `DJANGO_CSRF_TRUSTED_ORIGINS` must include the site origin (`https://mmg-webapps.fjfi.cvut.cz`), or the Django administration sign-in form rejects the sign-in.

## Deployment

The application is deployed at `https://mmg-webapps.fjfi.cvut.cz/conference/`: the root shows the landing page, and each conference is available at its own address under the root, for example `https://mmg-webapps.fjfi.cvut.cz/conference/wsc2026/`. The legacy `/conference-demo/` prefix permanently redirects to `/conference/`.
