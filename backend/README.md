# Backend

## Overview

This directory contains the backend part of the scientific conference management system. The backend is implemented with Django and Django REST Framework and provides the API, authentication, administrative operations, and data processing logic required by the application.

The backend is responsible for managing conference-related data such as participants, abstracts, talks, submissions, accommodation, conference information, schedules, and administrative content. It also supports document generation and protected administration workflows.

## Tech Stack

- Django
- Django REST Framework
- Simple JWT
- SQLite
- CORS support for the React frontend

## Project Structure

- `backend/` — Django project configuration.
- `core/` — main application containing models, serializers, views, URLs, tests, and administrative logic.
- `media/` — uploaded media files.
- `db.sqlite3` — local development database.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Setup

1. Install dependencies and create the virtual environment
   (from `uv.lock`, into `backend/.venv`):
   ```bash
   uv sync
   ```

2. Apply database migrations:
   ```bash
   uv run python manage.py migrate
   ```

3. Create a superuser if needed:
   ```bash
   uv run python manage.py createsuperuser
   ```

## Running the Development Server

Start the backend server with:

```bash
uv run python manage.py runserver
```

By default, the development server runs on `http://127.0.0.1:8000/`.

## Configuration

The project uses SQLite as its development database.  
JWT authentication is configured through Simple JWT.  
CORS is enabled for the frontend running on `http://localhost:3000`.

The backend also serves media files during development.

### Required environment variables

`DJANGO_SECRET_KEY` must be set — the server refuses to start without it.
For local development it defaults from `.env.development` (committed to git,
excluded from the Docker image), which also sets `DJANGO_DEBUG=True`.
Outside that file, set the variable in the environment; in production it
should come from a secret store (for example a Kubernetes Secret).

`DJANGO_DEBUG` defaults to `False`; enable it only for debugging.

### Admin login environment variables

Administrators sign in with the university GitLab account or, when enabled, with a local username and password. The offered methods are selected at startup:

- `AUTH_PASSWORD_LOGIN_ENABLED` (default `True`) — registers `/api/auth/login/` and shows the password forms. Set to `False` to remove password sign-in.
- `AUTH_GITLAB_LOGIN_ENABLED` (default `True`) — enables the GitLab routes; only effective when `GITLAB_CLIENT_ID` and `GITLAB_CLIENT_SECRET` are set.
- `GITLAB_URL` (default `https://gitlab.fjfi.cvut.cz`), `GITLAB_CLIENT_ID`, `GITLAB_CLIENT_SECRET` — the registered GitLab OAuth application.
- `GITLAB_OAUTH_CALLBACK_URL` — the SPA callback URL; required when GitLab sign-in is enabled.

At least one method must be enabled; the server refuses to start otherwise. See `docs/deployment.md` for the full deployment procedure (application registration, rollout order, emergency access).

### Mail and notification environment variables

Participant confirmation e-mails are queued through Celery and sent by a
worker (see `docs/deployment.md` for the Redis service and the worker
container). The backend reads these environment variables:

- `MAIL_BACKEND` (default: the console backend when `DJANGO_DEBUG=True`, otherwise the SMTP backend) — mail backend path override.
- `EMAIL_HOST` (default `localhost`), `EMAIL_PORT` (default `25`), `EMAIL_HOST_USER` (empty), `EMAIL_HOST_PASSWORD` (empty), `EMAIL_USE_TLS` (default `False`), `EMAIL_TIMEOUT` (default `10`) — the SMTP connection.
- `DEFAULT_FROM_EMAIL` (default `noreply@conference.local`) — sender address of every message.
- `PUBLIC_BASE_URL` (default `http://localhost:3000/`) — public SPA root used to build the tracking link inside e-mails.
- `CELERY_BROKER_URL` (default `redis://localhost:6379/0`) — broker for the notification worker.
- `CELERY_TASK_ALWAYS_EAGER` (default `True` when `DJANGO_DEBUG=True`, otherwise `False`) — run tasks synchronously in the web process.

Local development needs neither Redis nor a worker: with `DJANGO_DEBUG=True`
mail is printed to the server console and Celery runs eagerly, so tasks execute
inside the request. Note that eager mode does not retry failed sends, unlike
production — but only because `CELERY_TASK_EAGER_PROPAGATES=True` propagates
the retry exception instead of letting Celery re-run the task in-process (do
not remove that setting as if it were cosmetic). `PUBLIC_BASE_URL` is what
makes the tracking link in a local e-mail point at
`http://localhost:3000/<slug>/#/track/<token>`.

## API Overview

The backend exposes endpoints for:

- administrator sign-in (GitLab OAuth, optional password login, token refresh and logout),
- public conference information,
- conference program,
- participants,
- abstracts,
- talks,
- people (organisers and committee members),
- accommodation,
- conference information editing,
- submissions,
- submission publishing,
- schedules,
- hiking routes and stops,
- badge and program PDF generation.

Administrative endpoints are protected and require authentication.

## Authentication

Administrators sign in with the university GitLab account or, when enabled, with a local username and password. Two surfaces share one sign-in:

- The REST API issues HttpOnly JWT cookies (Simple JWT, 15 min access / 3 d refresh) for the conference admin panel. Application-level auth throttling is intentionally not configured; rate-limit login and admin paths at the reverse proxy/WAF. Cookies are scoped to the deployment subpath and cookie-authenticated unsafe requests require `X-CSRFToken`; `/api/auth/config/`, login and refresh bootstrap the non-HttpOnly `csrftoken` cookie. GitLab sign-in is an OAuth2 code flow: `GET /api/auth/gitlab/authorize/?next=<slug>` returns the GitLab authorization URL together with a signed state valid for 10 minutes; the SPA exchanges the returned code at `POST /api/auth/gitlab/` and receives the user and admin-panel address, while the response sets HttpOnly `conference-jwt-access` and `conference-jwt-refresh` cookies. No JWT is returned in JSON. The state is bound to a short-lived HttpOnly cookie and consumed once at the exchange, so only the browser that started the sign-in can finish it. Password sign-in uses `POST /api/auth/login/`, registered only while `AUTH_PASSWORD_LOGIN_ENABLED` is enabled, and sets the same cookies. `GET /api/auth/config/` reports which methods are enabled; `GET /api/auth/user/` is the JWT-cookie auth probe.
- The Django administration authenticates with a browser session. Its sign-in page is served by django-allauth under `/api/auth/allauth/` and offers the same methods. Signing in through either surface establishes both the session and the JWT cookies, and logging out of either surface clears both.

`POST /api/auth/logout/` requires a valid access cookie; it reads and blacklists the refresh cookie, clears both JWT cookies and flushes the Django session. `POST /api/auth/refresh/` reads the refresh cookie and sets fresh cookies without echoing a token.

Administrative API actions require an authenticated user who is a manager of the conference in the URL, or a superuser. A conference-manager grant (`ConferenceManagers`) is created per conference, manually, by a superuser in the Django administration; `is_staff` alone no longer grants conference access, and GitLab groups are never consulted. Accounts are never connected by matching e-mail addresses, and a first GitLab sign-in creates a user with no grants. To reassign a GitLab social account to an existing local user (for example after the first GitLab login auto-created a separate account), run:

```bash
uv run python manage.py link_gitlab_account <gitlab-username> <local-username> [--delete-orphan]
```

## Testing

The backend contains automated tests for core data and API behavior, including:

- participant submission model behavior,
- serializer validation,
- submission creation API,
- submission publishing workflow,
- talk scheduling logic,
- administrator login (GitLab OAuth flow and flags, Django admin login gating, GitLab account linking).

Run the test suite with:

```bash
uv run pytest
```

Lint and type checks:

```bash
uv run ruff check .
uv run pyright
```
