# FRONTEND KNOWLEDGE BASE

## OVERVIEW

Vite 6 (vite build / vitest) + React 19 SPA.

## STRUCTURE

```
frontend/
├── public/                  # static assets + the default (empty) app-config.js
├── index.html               # Vite entry document at the project root (not public/); loads ./app-config.js before the bundle
├── vite.config.mjs          # plugins, base from VITE_BASE_PATH (default './'), vitest config
├── docker-entrypoint.d/     # 20-app-config.sh: writes app-config.js from BASE_PATH/API_BASE at container start
├── src/
│   ├── main.jsx             # entry: initConferenceSlug() + applyBaseUrlToFetch, mounts App
│   ├── App.jsx              # renders <Landing/> when isLandingPage(), else HashRouter route
│   │                        # table + layout shell (Header/Footer are per-conference only)
│   ├── configuredFetch.js   # global fetch monkeypatch
│   ├── index.css            # only global CSS (plus bootstrap)
│   ├── utils/conferenceSlug.js  # pathname-parsed slug module singleton (landing vs conference)
│   ├── utils/api.js         # API client: API_BASE_URL, buildApiUrl (slug-scoped,
│   │                        # GLOBAL_API_PREFIXES allowlist), buildMediaUrl, fetchWithAuth
│   ├── utils/programRefresh.js  # slug-scoped localStorage dirty flag, re-fetch program
│   │                        # after admin edits (key: program_needs_refresh_<slug>)
│   ├── pages/               # 5 thin route wrappers (Home, Program, Abstracts, Participants, Registration)
│   └── components/          # 33 dirs incl. Landing, real logic lives here
├── .env.development         # VITE_BACKEND_API_BASE_URL=http://localhost:8000
├── nginx.conf               # NOT installed in image (Dockerfile COPY commented out)
└── Dockerfile               # build ARGs for backend URL + base path, exported via ENV;
                             # override with --build-arg (VITE_BASE_PATH defaults to /conference-demo/)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add/change a route | `src/App.jsx` | one flat route table, kebab-case paths |
| Landing page / conference cards | `src/components/Landing/` | `Landing.jsx` groups by status; `ConferenceCard.jsx` is the whole-card anchor |
| Which conference is active | `src/utils/conferenceSlug.js` | module singleton; `getConferenceSlug()` (null on landing), `isLandingPage()`, `conferenceUrl(slug)` |
| Any backend HTTP call | `src/utils/api.js` | buildApiUrl / buildMediaUrl / fetchWithAuth, used by ~26 files; only `/api/auth/*` and `/api/conferences/` pass through unscoped (`GLOBAL_API_PREFIXES`) |
| Public site section | `src/components/<Name>/` | Home, Hero, Program, Registration, Abstracts, Venue, Hiking, Accommodation... |
| Admin feature | `src/components/Admin*`, `Edit*` | AdminPanel (shows `Conference: <title> (<slug>)` cue), AdminLoginModal, ProtectedRoute, EditProgram, EditProgramInfo (program page text at `/admin-panel/edit-program/info`, opened by Edit Program's Edit Page Text button), EditParticipants, EditSubmissionModal, EditWebInfo + 6 section editors |
| Shared primitives | `src/components/ui/` | Modal, Loader, Separator, Title, HomeCard, AbstractCard, ParticipantsCard |
| Custom hooks | `src/components/hooks/` | useConferenceInfo, useLockBodyScroll, useConferenceExists, useUnsavedChangesGuard (beforeunload + hashchange guard for dirty forms) |
| Styling | `<Name>/<Name>.module.css` | colocated CSS Module per component |

## CONVENTIONS

- Component colocation: `Name/Name.jsx + Name.module.css`. Sub-components reuse the parent module (Program/Talk.jsx uses Program.module.css; Landing/ConferenceCard.jsx uses Landing.module.css). Bare-file exception: `ui/ScrollToTop.jsx`.
- CSS Modules only; class names 100% camelCase. No new global CSS.
- Routing: HashRouter, kebab-case paths; admin routes under `/admin-panel/*`, each wrapped in `<ProtectedRoute>`. Navigate via `useNavigate()` (react-router-dom v7).
- Landing vs conference: `App.jsx` renders `<Landing/>` (no router, no Header/Footer) when `isLandingPage()` is true; the router shell renders only inside a conference. A conference is selected by the PATH (`/<slug>/`), never the hash. A slug matching no real conference also renders `<Landing/>`, with a static not-found banner naming the slug — `App.jsx` gates the shell on `useConferenceExists` (tri-state unknown/exists/absent; checks the allowlisted `/api/conferences/` list, fails open to the conference shell on any fetch error so a backend hiccup cannot blank the site). Do not remove that guard: without it every scoped call 404s and component fallbacks fake a ghost conference.
- Conference slug singleton: `utils/conferenceSlug.js` parses `window.location.pathname` once at startup via `initConferenceSlug()` (called in main.jsx beside `applyBaseUrlToFetch`). It must NOT use react-router hooks (`useLocation` is hash-based and never sees the `/<slug>/` prefix) and must not become React Context (project has none).
- API scoping: `buildApiUrl` inserts `/api/<slug>` into every `/api/...` path except the `GLOBAL_API_PREFIXES` allowlist (`/api/auth/`, `/api/conferences/`). On the landing page (slug null) non-allowlisted paths pass through unscoped — landing code must only call allowlisted paths.
- Dirty flag scoping: `utils/programRefresh.js` keys the flag per conference (`program_needs_refresh_<slug>`); `EditProgram.jsx` reads it via `isProgramDirty()`, never a raw `localStorage.getItem`.
- State: local useState/useEffect only. No Redux/Context/zustand anywhere; do not introduce one.
- Auth: JWT access_token/refresh_token in localStorage; fetchWithAuth handles 401 refresh. Tokens are global across conferences (one login administers every conference).
- All API/media URLs through buildApiUrl/buildMediaUrl/fetchWithAuth. Never a literal URL in a component.
- Landing cards are plain `<a href={conferenceUrl(slug)}>` elements — full navigation. NEVER a react-router `<Link>` for cross-conference navigation (HashRouter would hash-prefix the href).
- `EditWebInfoHome` edits web content AND conference logistics (title, dates, location, short description, badge title, photo): logistics live on `ConferenceInfo` and are PATCHed as multipart FormData (photo file appended only when selected; `year` is derived and never sent).
- Env via `VITE_BACKEND_API_BASE_URL` and `VITE_BASE_PATH` (Vite env, inlined at build via `import.meta.env`; the Dockerfile ARGs export them, defaulting to empty/relative so the image is universal). At runtime these are only FALLBACKS: the container entrypoint (`docker-entrypoint.d/20-app-config.sh`) writes `public/app-config.js` from the `BASE_PATH`/`API_BASE` env vars, and `utils/appConfig.js` reads it first (`getDeployedBasePath`, API base). `process.env` does not exist in app code — only `vite.config.mjs` (Node context) reads it for `base`.
- Tooling: Biome handles both format and lint (`biome.json` here; runs over `src/`, JS/JSX and CSS Modules — CSS linting is on). `npm run lint` is a 0-errors gate (info-level diagnostics do not fail the command; keep them at zero too); `npm run format:check` the format gate. Biome and Vite are independent — no bundler-internal linter needs disabling.
- Lint debt (known, accepted): `noLabelWithoutControl` and `useButtonType` are off — labels are not always programmatically associated with controls, and `<button>`s may lack an explicit `type`. Re-enable either only after fixing the underlying markup.
- react-router-dom: imported as `react-router-dom` throughout `src/`. Upstream removes this package in RR v8 (the code moves to `react-router`); an import rewrite will be needed when upgrading past v7.

## ANTI-PATTERNS (THIS APP)

Root AGENTS.md already bans BrowserRouter/`window.location.href`, hardcoded URLs, dual-prefix refactors, unscoped endpoints, and typo renames — those bind here. Frontend-specific extras:

- `utils/conferenceSlug.js` must keep parsing `window.location.pathname` directly. React-router hooks never see the path prefix (hash-based router); a Context-based slug would violate the no-Context rule. Also do not break the undefined-pathname tolerance (`api.test.js` mocks location without one).
- Do not touch the `GLOBAL_API_PREFIXES` allowlist in `api.js` casually: a blanket slug prefix would 404 `/api/auth/*` and kill login/refresh; dropping the scoping breaks every conference endpoint.
- Landing cards must stay plain anchors (see conventions); a `<Link>` would produce `/#/wsc2026/`-style URLs that the slug parser ignores.
- `reloadAppAtHomePage` (api.js) pokes `window.location.hash` precisely because of HashRouter — do not "modernize" it.
- Symptom of a broken prefix guard: `http://hosthttp://host/api/...` — check `startsWith('http')` guards in configuredFetch.js/api.js first.
- `buildMediaUrl` strips a leading `conference-demo/` from media paths (api.js). Deployment-specific hack; do not remove.
- `isRefreshing`/`failedQueue` module-level singletons in api.js are a deliberate 401 refresh queue; naive cleanup breaks admin sessions mid-edit.
- Tests run via `CI=true npm test` (Vitest) across 17 suites (120 tests), including `conferenceSlug.test.js`, `api.test.js` (allowlist scoping), `programRefresh.test.js` (slug key), `Landing.test.jsx` (grouping + not-found banner), `Header.test.jsx` (nav emptiness gating), `AdminPanel.test.jsx` (conference cue), and `EditWebInfoHome.test.jsx` (logistics + FormData PATCH, year never sent, photo only when selected). Mocking pattern: vi.mock on `utils/api` (fetchWithAuth) + globalThis.fetch; localStorage/location mocked inline; jsdom environment + jest-dom matchers wired in vite.config.mjs test.setupFiles. Tests keep using `src/testUtils/reactRouterDomStub.jsx` via the vitest `react-router-dom` test alias (not real router rendering) — extend the stub when a test needs more router surface. When a test needs a form submit on an uncontrolled form, dispatch `fireEvent.submit`, not a button click — jsdom blocks native HTML5 validation before React's custom validators run. Tests that depend on the slug re-init the module (`initConferenceSlug()`) after setting `window.location.pathname`.
