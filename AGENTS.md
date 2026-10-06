# PROJECT KNOWLEDGE BASE

**Generated:** 2026-10-02
**Updated:** 2026-10-05 — editor UX polish + landing not-found banner
**Commit:** b24fa5e
**Branch:** main

## OVERVIEW

Web app for organizing scientific conferences (CTU FNSPE, Dept. of Software Engineering).
Django 5.2 + DRF + SimpleJWT backend, React 19 (Vite 6) frontend, SQLite DB.
Two independent deployables, coupled only via REST API. Deployed as Docker images under subpath `/conference-demo/`.
Multi-conference: a `Conference` model owns every domain row; a landing page at the root lists all conferences, each conference SPA lives at `/<slug>/`, and the API is scoped under `/api/<slug>/`.

## STRUCTURE

```
scientific-conference/
├── backend/      # Django project + single app `core` (all domain logic) — see backend/AGENTS.md
├── frontend/     # Vite React SPA (landing + per-conference sites) — see frontend/AGENTS.md
├── screenshots/  # visual regression captures (gitignored; regenerate via scripts/capture-screenshots.sh)
├── scripts/      # repo-level tooling (capture-screenshots.sh: seeds backend, builds frontend, captures landing + all conference routes)
├── .github/workflows/  # single workflow: builds/pushes 2 GHCR images on push to main
├── README.md           # stack + local setup + URL anatomy
└── docs/         # admin_guide.md (admin manual; MUST be updated when app is extended) + deployment.md (container images, proxy requirements) + assets/ (guide screenshots ONLY, not app assets)
```

No root Makefile / docker-compose / package.json / requirements.txt. Each app builds itself.
`.venv/`, `.omo/`, `.codegraph/` are local tool artifacts (gitignored).

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add/change API endpoint | `backend/backend/urls.py` (global routes) + `backend/core/urls.py` (slug-scoped tails) + `backend/core/views.py` | explicit `path()`, no router; global = auth + `/api/conferences/` only |
| Change data model | `backend/core/models.py` | then `makemigrations`; every domain model carries a `conference` FK |
| Create/edit a conference | Django admin (`Conference` model) | CRUD via admin only; deletion disabled (`has_delete_permission=False`) |
| Backend config/env vars | `backend/backend/settings.py` | single env-driven file, no dev/prod split |
| Frontend routing | `frontend/src/App.jsx` | one flat HashRouter route table; renders `Landing` (no router) when no slug in path (or the slug matches no conference — with a not-found banner) |
| Conference slug resolution | `frontend/src/utils/conferenceSlug.js` | pathname-parsed module singleton; `initConferenceSlug()` in main.jsx |
| Any backend HTTP call | `frontend/src/utils/api.js` | `buildApiUrl` (slug-scoped, `GLOBAL_API_PREFIXES` allowlist) / `buildMediaUrl` / `fetchWithAuth` |
| New UI component | `frontend/src/components/<Name>/` | `<Name>.jsx` + `<Name>.module.css` |
| Docker images | `backend/Dockerfile`, `frontend/Dockerfile` | separate build contexts (matrix in CI); frontend has `VITE_BASE_PATH` ARG |
| Admin usage rules | `docs/admin_guide.md` | behavioral constraints on delete/publish/multi-conference flows |
| Deployment (images, proxy) | `docs/deployment.md` | universal frontend image + BASE_PATH/API_BASE, backend RELATIVE_URL_ROOT, reverse-proxy requirements |
| Visual regression baseline | `scripts/capture-screenshots.sh` → `screenshots/` | full-page PNGs (landing + public + admin routes), 1440x900; landing has an identical-PNG guard; rerun after UI changes and diff `screenshots/*.png` |

## CODE MAP

Codegraph covers Python only (JS unindexed); refs via pyright LSP.

| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `Conference` | model | backend/core/models.py:8 | all domain models FK to it | slug-only (`__str__` = slug); reserved slugs rejected in `clean()` |
| `ConferenceScopedMixin` | mixin | backend/core/views.py:64 | most scoped views | resolves `conference_slug` URL kwarg → eager 404, queryset filter, `perform_create`, serializer context |
| `get_conference_or_404` | function | backend/core/views.py:59 | function views + mixin | shared slug→Conference resolution |
| `ConferenceListView` | view | backend/core/views.py:95 | the ONLY unscoped API view | public card list, server-ordered running→future asc→past desc |
| `ConferenceInfo` | model | backend/core/models.py:416 | per-conference web content + logistics | `get_or_create(conference=…)`; owns title/dates/location/card_photo/hero_photo/short_description/badge_title; `year`+`status` computed; GET/PATCH `conference-info/` is the plain serializer (multipart PATCH accepted) |
| `ParticipantSubmission.publish()` | method | backend/core/models.py | core workflow | creates Participant + Abstract + unscheduled Talk, dedup scoped to `conference` |
| `generate_program_pdf` / `generate_badges_pdf` | function | backend/core/views.py | PDF endpoints | per-conference reportlab PDFs; badges header = info's `badge_title or title`, footer = info's `location`; need `core/fonts/*.ttf` |
| DRF views | classes | backend/core/views.py | scoped via core/urls.py + ConferenceListView | public `AllowAny` + admin `IsAdminUser` |
| `App` | component | frontend/src/App.jsx | entry | renders `<Landing/>` when no slug (or unknown slug, with a not-found banner), else HashRouter + all routes + layout shell |
| `Landing` / `ConferenceCard` | components | frontend/src/components/Landing/ | root page | cards grouped Running/Upcoming/Past; whole card is a plain `<a>` to `/<slug>/`; `unknownSlug` prop renders the not-found banner |
| `fetchWithAuth` / `buildApiUrl` / `buildMediaUrl` | functions | frontend/src/utils/api.js | many files | sole API client; 401-refresh queue; slug scoping via `GLOBAL_API_PREFIXES` allowlist |

## CONVENTIONS

- Cross-app contract: REST under `/{RELATIVE_URL_ROOT}api/`, JWT Bearer; frontend base URL from `VITE_BACKEND_API_BASE_URL` (Vite env, inlined at build via import.meta.env).
- Scoped API contract: only `/api/auth/login|refresh/` and `/api/conferences/` are global (registered in `backend/backend/urls.py` BEFORE the slug include); EVERYTHING else is served under `/api/<slug>/…` via `include("core.urls")` and must filter/assign by conference. New class views use `ConferenceScopedMixin`; new function views use `get_conference_or_404()`. Unknown slug → 404 for every scoped route (enforced in `initial()`).
- Per-conference singletons: config tables (`ConferenceInfo`, `AccommodationInfo`) are created with `get_or_create(conference=…)` — never `get_or_create(id=1)`.
- JWT is global across conferences: one staff account administers every conference. Intended; do not scope tokens per conference.
- Subpath deployment is first-class on BOTH sides. Backend: `RELATIVE_URL_ROOT` env feeds URL prefixes, STATIC_URL, MEDIA_URL, cookie paths. Frontend: `HashRouter` + Vite `base` from `VITE_BASE_PATH` (default `./` in dev; `frontend/Dockerfile` ARG defaults to `/conference-demo/`, making built asset URLs absolute and depth-independent). The outer proxy must serve the SPA index.html for any non-file path under the root (esp. `/<root>/<slug>/`) that is not routed to the backend. Any new route/URL must honor all of this.
- Env-driven config only: backend `os.getenv(..., dev_default)`; no settings split, no django-environ.
- Commits: Conventional Commits — `<type>(<optional scope>): <imperative subject>`; types: feat / fix / docs / style / refactor / test / chore / build / ci. One logical change per commit.
- Commit message lines are ≤ 72 characters (subject and body, kernel-style); wrap body prose instead of emitting one long line.
- Commits with AI assistance carry a Linux-kernel-style trailer, after a blank line at message end: `Assisted-by: <tool>:<model>` (e.g. `Assisted-by: Opencode:kimi-k3`). Multiple trailers allowed.
- History before 2026-10-02 predates this policy (plain imperative subjects) — do not rewrite it.
- Backend has its own AGENTS.md; frontend has its own AGENTS.md. Domain detail lives there, not here.

## ANTI-PATTERNS (THIS PROJECT)

- NEVER switch `HashRouter` back to `BrowserRouter` or navigate with `window.location.href` — breaks `/conference-demo/` deployment (deliberate fix in ec29448). Use `useNavigate()` / `window.location.hash`.
- NEVER hardcode backend URLs in components — always `buildApiUrl`/`buildMediaUrl`/`fetchWithAuth` (fix 7209ddc swept many files for this).
- NEVER "fix" the dual fetch-prefixing (`configuredFetch.js` global patch + `buildApiUrl`): they coexist only via `startsWith('http')` guards; touching one side risks double-prefixed URLs.
- NEVER add an API endpoint outside the `/api/<slug>/` include without conference scoping — the route-table lock in `backend/core/test_conference_isolation.py` fails the suite for any unscoped route.
- NEVER re-enable conference deletion (Django admin `has_delete_permission=False` on `ConferenceAdmin`): all domain models cascade from `Conference`; deletion is a deliberate ops-shell-only operation, not a UI action.
- The frontend conference-slug singleton (`utils/conferenceSlug.js`) must NOT use react-router hooks — `useLocation` is hash-based and never sees the `/<slug>/` path prefix. It parses `window.location.pathname` once at startup; keep it that way.
- NEVER commit `.venv/`, `db.sqlite3`, `media/`, `staticfiles/` (a venv was once committed: 4c321da).
- `.github/workflows/quality.yml` runs ruff/pyright/pytest + biome/vitest on push to `main` and PRs. The Docker publish workflow does NOT depend on it — a red quality run does not block image pushes.
- Do not treat cascade deletes as accidental: deleting a ConferenceDay deletes its Sessions+Talks; deleting an Abstract deletes its Talk (the FK sits on Talk); deleting a HikingRoute deletes its Stops; deleting a Conference deletes everything (UI path disabled, see above). NOTE: deleting a day or an unscheduled talk ORPHANS the linked abstract — deliberate admin choice (2026-10-03); do not add cascades unilaterally. The admin guide documents these as rules (`docs/admin_guide.md:287`,`:469`); backend guards exist deliberately (e.g. `UnscheduledTalkDeleteView` 400).
- The dormant lines in `backend/Dockerfile` (RUN-time collectstatic, VOLUME declarations) are disabled on purpose — startup collectstatic lives in the active CMD; gunicorn has been the active server since 2026-10-06 (the old `manage.py runserver` prod note is obsolete). (The `frontend/Dockerfile` nginx.conf COPY used to be dormant too; it is active again since the universal-image rework — `frontend/nginx.conf` is the universal, deployment-value-free server config.)
- If the app is extended, update `docs/admin_guide.md` (guide rule, line 575); deployment changes go to `docs/deployment.md`.

## COMMANDS

```bash
# Backend (workdir backend/; uv-managed env in backend/.venv/)
uv sync                               # install deps from uv.lock
uv run python manage.py makemigrations && uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver     # :8000
uv run pytest                         # backend suite (pytest-django;
                                      #   incl. conference model/isolation/singleton/conferences-endpoint suites)
uv run ruff check . && uv run ruff format --check .
uv run pyright                        # type check via django-stubs
uv run python manage.py loaddata conferences.json participants.json program.json  # seed: demo conferences, participants with abstracts/submissions, organizers/committee, a scheduled program (day + chaired session + talk per participant) for every conference

# Frontend (workdir frontend/)
npm install
npm run start                         # :3000, uses .env.development ("/" = landing, "/wsc2026/" = conference)
CI=true npm test                      # one-shot Vitest (incl. conferenceSlug/api/programRefresh/Landing/Header suites)
npm run build                         # compile (ESLint plugin disabled)
npm run lint                          # Biome lint (0 errors gate, CSS included)
npm run format:check                  # Biome format gate
bash scripts/capture-screenshots.sh   # visual regression baseline -> screenshots/ (PNGs incl. landing; --backend-port/--frontend-port flags, fails fast on port conflicts)

# Docker (as CI does)
docker build backend/                 # -> ghcr.io/<repo>-backend
docker build frontend/                # -> ghcr.io/<repo>-frontend (universal image; configure at runtime with BASE_PATH, see frontend/docker-entrypoint.d/)
```

## NOTES

- EditProgram.jsx and api.js URL helpers are the highest-churn areas. Both have real tests now (EditProgram lifecycle + api client suites), but the component depth (DaySchedule/TalkCard interactions) is still thin territory — refactor with care.
- `.env.production` is deliberately absent: the frontend image is universal and carries no deployment values. The Vite ARGs (`VITE_BACKEND_API_BASE_URL`, `VITE_BASE_PATH`, both defaulting to empty/relative) are only build-time fallbacks; deployments configure the running container with `BASE_PATH` (and optionally `API_BASE`), which the image entrypoint writes into `app-config.js` — the app reads that file before the Vite values (see `frontend/src/utils/appConfig.js`).
- Backend prod image runs gunicorn (WSGI) behind the frontend nginx; it never serves static/media itself (the frontend nginx serves the shared volumes).
- JWT: 1h access / 7d refresh — lifetimes were a deliberate fix (f064a9e); shortening logs admins out mid-edit. Tokens are global across conferences (no per-conference scoping).
- The prod reverse proxy (mmg-webapps) must map any non-file path under `/conference-demo/` (especially `/conference-demo/<slug>/`) to the SPA index.html; `api/`, `admin/`, `media/` keep routing to the backend. Documented in README.md and docs/deployment.md.
- Old bookmarks like `/conference-demo/#/program` now land on the landing page (path, not hash, selects the conference) — deliberate "always render landing"; users click through. An unknown slug (`/typo-in-the-slug/`) also renders the landing, with a static banner naming the slug (`useConferenceExists` tri-state: unknown/exists/absent; fetch failures fail open to the conference shell so a backend hiccup cannot blank the site).
- Demo: `https://mmg-webapps.fjfi.cvut.cz/conference-demo/` (root = landing; `wsc2026` = seeded conference)
