# FRONTEND KNOWLEDGE BASE

## OVERVIEW

Create React App (react-scripts 5.0.1) + React 19 SPA.

## STRUCTURE

```
frontend/
├── public/                  # static assets
├── src/
│   ├── index.js             # entry, mounts App
│   ├── App.js               # single HashRouter route table + layout shell (Header/Footer)
│   ├── configuredFetch.js   # global fetch monkeypatch
│   ├── index.css            # only global CSS (plus bootstrap)
│   ├── utils/api.js         # API client: API_BASE_URL, buildApiUrl, buildMediaUrl, fetchWithAuth
│   ├── utils/programRefresh.js  # localStorage dirty flag, re-fetch program after admin edits
│   ├── pages/               # 5 thin route wrappers (Home, Program, Abstracts, Participants, Registration)
│   └── components/          # 32 dirs, real logic lives here
├── .env.development         # REACT_APP_BACKEND_API_BASE_URL=http://localhost:8000
├── .env.production          # empty by design
├── nginx.conf               # NOT installed in image (Dockerfile:43 COPY commented out)
└── Dockerfile               # build ARG for backend URL, exported via ENV; override with --build-arg
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add/change a route | `src/App.js` | one flat route table, kebab-case paths |
| Any backend HTTP call | `src/utils/api.js` | buildApiUrl / buildMediaUrl / fetchWithAuth, used by ~26 files |
| Public site section | `src/components/<Name>/` | Home, Hero, Program, Registration, Abstracts, Venue, Hiking, Accommodation... |
| Admin feature | `src/components/Admin*`, `Edit*` | AdminPanel, AdminLoginModal, ProtectedRoute, EditProgram, EditParticipants, EditSubmissionModal, EditWebInfo + 7 section editors |
| Shared primitives | `src/components/ui/` | Modal, Loader, Separator, Title, HomeCard, AbstractCard, ParticipantsCard |
| Custom hooks | `src/components/hooks/` | useConferenceInfo, useLockBodyScroll (frontend/README.md wrongly claims src/hooks/ and src/ui/ top-level; trust the tree) |
| Styling | `<Name>/<Name>.module.css` | colocated CSS Module per component |

## CONVENTIONS

- Component colocation: `Name/Name.jsx + Name.module.css`. Sub-components reuse the parent module (Program/Talk.jsx uses Program.module.css). Bare-file exception: `ui/ScrollToTop.jsx`.
- CSS Modules only; class names 100% camelCase. No new global CSS.
- Routing: HashRouter, kebab-case paths; admin routes under `/admin-panel/*`, each wrapped in `<ProtectedRoute>`. Navigate via `useNavigate()` (react-router-dom v7).
- State: local useState/useEffect only. No Redux/Context/zustand anywhere; do not introduce one.
- Auth: JWT access_token/refresh_token in localStorage; fetchWithAuth handles 401 refresh.
- All API/media URLs through buildApiUrl/buildMediaUrl/fetchWithAuth. Never a literal URL in a component.
- Env via `REACT_APP_BACKEND_API_BASE_URL` (CRA env, baked at build). `import.meta.env` does not exist here.

## ANTI-PATTERNS (THIS APP)

Root AGENTS.md already bans BrowserRouter/`window.location.href`, hardcoded URLs, dual-prefix refactors, and typo renames — those bind here. Frontend-specific extras:

- `reloadAppAtHomePage` (api.js) pokes `window.location.hash` precisely because of HashRouter — do not "modernize" it.
- Symptom of a broken prefix guard: `http://hosthttp://host/api/...` — check `startsWith('http')` guards in configuredFetch.js/api.js first.
- `buildMediaUrl` strips a leading `conference-demo/` from media paths (api.js:55-57). Deployment-specific hack; do not remove.
- `isRefreshing`/`failedQueue` module-level singletons in api.js are a deliberate 401 refresh queue; naive cleanup breaks admin sessions mid-edit.
- Only test file: `RegistrationForm.test.jsx`. Mock pattern: jest.mock hooks + global fetch.
