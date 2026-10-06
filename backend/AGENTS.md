# BACKEND KNOWLEDGE BASE

## OVERVIEW

Django 5.2 + DRF 3.16 + SimpleJWT backend, single app `core`, SQLite (root-level contract/subpath/CI rules live in the repo-root AGENTS.md, not here).

## STRUCTURE

```
backend/
├── backend/    # project package: settings.py, urls.py, wsgi.py, asgi.py
│               # urls.py: global routes ONLY (admin/, api/auth/*, api/conferences/)
│               # + the slug include: api/<slug:conference_slug>/ -> core.urls
├── core/       # the ONLY app — all domain logic
│   ├── models.py           # models (Conference + domain models FK'd to it)
│   ├── views.py            # views (scoped + ConferenceListView)
│   ├── serializers.py
│   ├── urls.py             # slug-scoped endpoint tails (full table)
│   ├── admin.py            # decorator-style @admin.register
│   ├── signals.py          # email on publish; wired via CoreConfig.ready() (apps.py)
│   ├── migrations/         # migrations
│   ├── fixtures/            # split demo seed: conferences.json, participants.json, program.json
│   ├── conftest.py         # pytest fixtures: wsc()/other() two-conference factory + api() URL helper
│   ├── tests.py            # original suites (Django TestCase, pytest runs them)
│   ├── test_*.py           # pytest-django suites by domain (schedule, publishing,
│   │                       # timeline, signals, admin, public, PDF + conference model,
│   │                       # conferences endpoint, conference isolation, singletons)
│   └── fonts/DejaVu*.ttf   # required by reportlab PDF generation
├── manage.py
├── Dockerfile
├── pyproject.toml          # deps + dev group + ruff/pyright/pytest config
├── uv.lock                 # locked dependency set (uv)
└── .python-version         # pinned interpreter (3.13)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Endpoint list | `backend/urls.py` (global + slug include) + `core/urls.py` (scoped tails) | explicit `path()`, no router |
| Add a scoped endpoint | `core/views.py` | new class views use `ConferenceScopedMixin`; new function views call `get_conference_or_404()` |
| Auth config | `backend/settings.py` | SIMPLE_JWT: 1h access / 7d refresh |
| Conference model / admin policies | `core/models.py`, `core/admin.py` | slug reserved words in `clean()`; deletion forbidden (`has_delete_permission=False`) |
| PDF generation | `core/views.py` | `generate_program_pdf` (line 128), `generate_badges_pdf` (line 369); per-conference, reportlab + `core/fonts/*.ttf` |
| Publish workflow | `core/models.py` | `ParticipantSubmission.publish()` (line 279), `.delete()`; dedup scoped to `conference` |
| Email on publish | `core/signals.py` | fires via `CoreConfig.ready()` |
| Env config | `backend/settings.py` | DJANGO_SECRET_KEY / DJANGO_DEBUG / DJANGO_ALLOWED_HOSTS / DJANGO_DB_PATH / DJANGO_STATIC_URL / DJANGO_STATIC_ROOT / DJANGO_MEDIA_ROOT / DJANGO_USE_HTTPS / DJANGO_CSRF_TRUSTED_ORIGINS, plus unprefixed RELATIVE_URL_ROOT |

## CONVENTIONS

- Views: `generics.APIView`/generic classes mixed with `@api_view` functions (`generate_*`, `publish_submission`, `update_session`, `delete_session`); named `<Noun><Action>View`.
- Conference scoping: every view in `core/urls.py` is served under `/api/<slug>/…` and must resolve its conference. Class views inherit `ConferenceScopedMixin` (views.py:64: eager 404 on unknown slug in `initial()`, queryset filter, `perform_create` assignment, serializer context); function views call `get_conference_or_404(conference_slug)`. The only unscoped views are auth + `ConferenceListView`, registered globally in `backend/urls.py` BEFORE the slug include.
- Serializers: `<Model>Serializer` for read, `...WriteSerializer` split for writes. Serializer field lists are explicit and exclude `conference`; the write path gets the conference via the view's `save(conference=…)`. `TalkSerializer` narrows `session`/`day` querysets via the context conference (cross-conference FK ⇒ 400).
- URL paths kebab-case with trailing slash; API mounted under `/{RELATIVE_URL_ROOT}api/`, admin tails under the slug prefix (e.g. `/api/<slug>/admin/...`).
- Config tables (`ConferenceInfo`, `AccommodationInfo`) are per-conference singletons: read/edit views do `get_or_create(conference=self.conference)` — never `get_or_create(id=1)`. `ConferenceInfo` owns the logistics (title, dates, location, card_photo, hero_photo, venue_photo, short_description, badge_title; `year` derived read-only): `GET conference-info/` returns the plain `ConferenceInfoSerializer` payload; `PATCH conference-info/edit/` (multipart-capable, `BlankAsNoneDateField` maps empty date strings to null) writes logistics + web fields.
- Global default is `AllowAny`; admin views declare `authentication_classes=[JWTAuthentication]` + `permission_classes=[IsAdminUser]` per-view — do not centralize into settings.
- JWT is global across conferences: one staff account administers every conference. Intended; do not scope tokens per conference.
- Refresh-token rotation blacklists old tokens via `rest_framework_simplejwt.token_blacklist` (in INSTALLED_APPS); frontend refresh flow stores the rotated pair.
- Model changes require `makemigrations`. Every domain model carries a `conference` FK (`on_delete=CASCADE`, `preserve_default=False` in the squashed 0014); 0014 is hand-written — schema ops plus two idempotent data seeds (wsc2026 conference, fallback ConferenceInfo row).
- `views.py` uses explicit imports — do not reintroduce `from .models import *` / `from .serializers import *`.
- Media uploads via `ImageField` under MEDIA_ROOT (per-model `upload_to` subdirs: conferences/, participants/, organizers/, organizingCommittee/, accommodation/, submissions/photos/, hiking/).
- Tests: `uv run pytest` with pytest-django (`DJANGO_SETTINGS_MODULE` from pyproject). `python_files` includes the Django-style `tests.py`; new suites go in `test_<domain>.py` with `Test*`-prefixed classes. `conftest.py` provides two conferences per test (`wsc`/`other` fixtures) — never assume `conference_id=1`. The isolation suite derives its route matrix from `core/urls.py`, so any new unscoped route fails it.
- Lint/typing: `uv run ruff check .` (extend-select I,B,SIM,BLE,EXE,RUF; RUF012 off for Django class attrs) and `uv run pyright` (django-stubs; attribute-access/function-member rules off — pyright can't run the stubs' mypy plugin; `venvPath`/`venv` also set here). Config lives in pyproject.toml.

## ANTI-PATTERNS (THIS APP)

- NEVER add an endpoint outside the `/api/<slug>/` include without conference scoping — `test_conference_isolation.py` builds its route matrix from `core/urls.py` and fails the suite for any unscoped route.
- NEVER re-enable conference deletion: `ConferenceAdmin.has_delete_permission` is deliberately `False`; all domain models cascade from `Conference`, so deletion is an ops-shell decision, not a UI action.
- `AccommodationOptionListView` (views.py:321) is dead code — defined but never routed. Deliberate minimal diff; do not wire it up or delete it casually.
- `ConferenceDayDeleteView.destroy` calls bare `day.delete()` with no guard; `UnscheduledTalkDeleteView` 400s on scheduled talks. Both deliberate — cascade rules and rationale live in root AGENTS.md; keep guards as they are. Beware: Talk→Abstract FK direction means day/talk deletes orphan the Abstract row.
- `AccommodationOptionEditView` and `HikingStopEditView` call `objects.get(pk, conference=…)` unguarded in patch/delete: unknown or cross-conference pks surface as 500, never 404. Deliberate security choice — keep; tests pin the 500.
- `ParticipantListView` and `AbstractListView` are `ListCreateAPIView` under the global `AllowAny`: POST creates rows for ANYONE. Deliberate public surface (admin decision 2026-10-03, may be revisited for security); do not add permission_classes without a fresh decision.
- Deleting a conference day or an unscheduled talk orphans the linked `Abstract` (FK sits on Talk). Deliberate admin choice (2026-10-03); do not add delete cascades.
- PDF generators (`generate_program_pdf`, `generate_badges_pdf`) build into `io.BytesIO`, then write bytes into the response — do not pass the HttpResponse to canvas directly (pyright compatibility, bytes unchanged). Both filter every queryset by conference; badges header is the info's `badge_title or title`, footer is the info's `location`.
- `traceback.print_exc()` debug calls and Russian comments exist in models/views/settings — leave them.
- Signals: publish email fires on status transition to approved via `_old_status` captured in pre_save — `QuerySet.update()`/bulk paths silently skip it, and `fail_silently=False` means mail errors raise inside the publish request.
- No pagination configured: list endpoints return all rows.
