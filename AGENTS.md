# PROJECT KNOWLEDGE BASE

**Generated:** 2026-10-02
**Commit:** ec29448
**Branch:** main

## OVERVIEW

Web app for organizing scientific conferences (CTU FNSPE, Dept. of Software Engineering).
Django 5.2 + DRF + SimpleJWT backend, React 19 (Create React App) frontend, SQLite DB.
Two independent deployables, coupled only via REST API. Deployed as Docker images under subpath `/conference-demo/`.

## STRUCTURE

```
scientific-conference/
├── backend/      # Django project + single app `core` (all domain logic) — see backend/AGENTS.md
├── frontend/     # CRA React SPA — see frontend/AGENTS.md
├── assets/       # PNG screenshots for ADMINISTRATOR_GUIDE.md ONLY (not app assets)
├── .github/workflows/  # single workflow: builds/pushes 2 GHCR images on push to main
├── README.md           # stack + local setup
└── ADMINISTRATOR_GUIDE.md  # 473-line admin manual; MUST be updated when app is extended
```

No root Makefile / docker-compose / package.json / requirements.txt. Each app builds itself.
`.venv/`, `.omo/`, `.codegraph/` are local tool artifacts (gitignored).

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add/change API endpoint | `backend/core/urls.py` + `backend/core/views.py` | explicit `path()`, no router |
| Change data model | `backend/core/models.py` | then `makemigrations` |
| Backend config/env vars | `backend/backend/settings.py` | single env-driven file, no dev/prod split |
| Frontend routing | `frontend/src/App.js` | one flat HashRouter route table |
| Any backend HTTP call | `frontend/src/utils/api.js` | `buildApiUrl` / `buildMediaUrl` / `fetchWithAuth` |
| New UI component | `frontend/src/components/<Name>/` | `<Name>.jsx` + `<Name>.module.css` |
| Docker images | `backend/Dockerfile`, `frontend/Dockerfile` | separate build contexts (matrix in CI) |
| Admin usage rules | `ADMINISTRATOR_GUIDE.md` | behavioral constraints on delete/publish flows |

## CODE MAP

Codegraph covers Python only (JS unindexed); refs via pyright LSP.

| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `ConferenceInfo` | model | backend/core/models.py:333 | 7 | single-row site config (`get_or_create(id=1)`) |
| `ParticipantSubmission.publish()` | method | backend/core/models.py:209 | core workflow | creates Participant + Abstract + unscheduled Talk |
| `generate_program_pdf` / `generate_badges_pdf` | function | backend/core/views.py:54,293 | 2 endpoints | reportlab PDFs; need `core/fonts/*.ttf` |
| ~39 DRF views | classes | backend/core/views.py | wired in core/urls.py | public `AllowAny` + admin `IsAdminUser` |
| `App` | component | frontend/src/App.js:35 | entry | HashRouter + all routes + layout shell |
| `fetchWithAuth` / `buildApiUrl` / `buildMediaUrl` | functions | frontend/src/utils/api.js | ~26 files | sole API client; 401-refresh queue |

## CONVENTIONS

- Cross-app contract: REST under `/{RELATIVE_URL_ROOT}api/`, JWT Bearer; frontend base URL from `REACT_APP_BACKEND_API_BASE_URL` (CRA env, baked at build).
- Subpath deployment is first-class on BOTH sides. Backend: `RELATIVE_URL_ROOT` env feeds URL prefixes, STATIC_URL, MEDIA_URL, cookie paths. Frontend: `HashRouter` + `package.json "homepage": "."`. Any new route/URL must honor both.
- Env-driven config only: backend `os.getenv(..., dev_default)`; no settings split, no django-environ.
- Commits: Conventional Commits — `<type>(<optional scope>): <imperative subject>`; types: feat / fix / docs / style / refactor / test / chore / build / ci. One logical change per commit.
- Commit message lines are ≤ 72 characters (subject and body, kernel-style); wrap body prose instead of emitting one long line.
- Commits with AI assistance carry a Linux-kernel-style trailer, after a blank line at message end: `Assisted-by: <tool>:<model>` (e.g. `Assisted-by: Opencode:kimi-k3`). Multiple trailers allowed.
- History before 2026-10-02 predates this policy (plain imperative subjects) — do not rewrite it.
- Backend has its own AGENTS.md; frontend has its own AGENTS.md. Domain detail lives there, not here.

## ANTI-PATTERNS (THIS PROJECT)

- NEVER switch `HashRouter` back to `BrowserRouter` or navigate with `window.location.href` — breaks `/conference-demo/` deployment (deliberate fix in ec29448). Use `useNavigate()` / `window.location.hash`.
- NEVER hardcode backend URLs in components — always `buildApiUrl`/`buildMediaUrl`/`fetchWithAuth` (fix 7209ddc swept 20+ files for this).
- NEVER "fix" the dual fetch-prefixing (`configuredFetch.js` global patch + `buildApiUrl`): they coexist only via `startsWith('http')` guards; touching one side risks double-prefixed URLs.
- NEVER commit `.venv/`, `db.sqlite3`, `media/`, `staticfiles/` (a venv was once committed: 4c321da).
- Do not assume CI verifies anything: the only workflow builds+pushes Docker images on push to `main`. No test/lint gate — run both test suites locally before pushing.
- Do not treat cascade deletes as accidental: deleting a ConferenceDay deletes its Sessions+Talks; deleting an Abstract deletes its Talk (the FK sits on Talk); deleting a HikingRoute deletes its Stops. NOTE: deleting a day or an unscheduled talk ORPHANS the linked abstract — deliberate admin choice (2026-10-03); do not add cascades unilaterally. The admin guide documents these as rules (`ADMINISTRATOR_GUIDE.md:196`,`:375`); backend guards exist deliberately (e.g. `UnscheduledTalkDeleteView` 400).
- Do not uncomment dormant Docker lines blindly: `backend/Dockerfile` collectstatic/gunicorn and `frontend/Dockerfile` nginx.conf COPY are disabled on purpose.
- If the app is extended, update `ADMINISTRATOR_GUIDE.md` (guide rule, line 471).

## COMMANDS

```bash
# Backend (workdir backend/; uv-managed env in backend/.venv/)
uv sync                               # install deps from uv.lock
uv run python manage.py makemigrations && uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver     # :8000
uv run pytest                         # backend suite (pytest-django)
uv run ruff check . && uv run ruff format --check .
uv run pyright                        # type check via django-stubs
uv run python manage.py loaddata program.json  # seed (undocumented fixture)

# Frontend (workdir frontend/)
npm install
npm run start                         # :3000, uses .env.development
CI=true npm test                      # one-shot Jest
npm run build                         # compile (ESLint plugin disabled)
npm run lint                          # Biome lint (0 errors, 0 warnings gate)
npm run format:check                  # Biome format gate

# Docker (as CI does)
docker build backend/                 # -> ghcr.io/<repo>-backend
docker build frontend/                # -> ghcr.io/<repo>-frontend
```

## NOTES

- EditProgram.jsx (~1100 lines) and api.js URL helpers are the highest-churn areas. Both have real tests now (EditProgram lifecycle + api client suites), but the component depth (DaySchedule/TalkCard interactions) is still thin territory — refactor with care.
- `.env.production` is intentionally EMPTY; prod backend URL comes from the frontend Dockerfile `ARG`, exported as `ENV` to `npm run build` (default still hardcoded, flagged FIXME — override with `--build-arg`).
- Backend prod image runs `manage.py runserver`, not gunicorn. Media files in prod must be served externally; Django serves media only in DEBUG.
- JWT: 1h access / 7d refresh — lifetimes were a deliberate fix (f064a9e); shortening logs admins out mid-edit.
- Demo: `https://mmg-webapps.fjfi.cvut.cz/conference-demo/`
