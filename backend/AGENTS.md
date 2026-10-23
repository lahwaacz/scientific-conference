# BACKEND KNOWLEDGE BASE

## OVERVIEW

Django 6.1 + DRF 3.16 + SimpleJWT backend, single app `core`, SQLite (root-level contract/subpath/CI rules live in the repo-root AGENTS.md, not here).

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
│   ├── auth/               # admin login: GitLab OAuth views (authorize/login/logout),
│   │                       # allauth adapters (no local signup; social signup open), serializers
│   ├── context_processors.py  # auth_config: login-method flags for the allauth login template
│   ├── management/commands/link_gitlab_account.py  # reassign a GitLab SocialAccount to a local user
│   ├── templates/account/login.html  # Django admin sign-in page (GitLab link + optional password form)
│   ├── migrations/         # migrations
│   ├── fixtures/            # split demo seed: conferences.json, participants.json, program.json
│   ├── conftest.py         # pytest fixtures: wsc()/other() two-conference factory + api() URL helper
│   ├── tests.py            # original suites (Django TestCase, pytest runs them)
│   ├── test_*.py           # pytest-django suites by domain (schedule, publishing,
│   │                       # timeline, signals, admin, public, PDF + conference model,
│   │                       # conferences endpoint, conference isolation, conference-info,
│   │                       # gitlab auth, cookie auth, admin login, link_gitlab_account)
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
| Auth config | `backend/settings.py` + `core/auth/` | SIMPLE_JWT: 15m access / 3d refresh; no application-level auth throttle (rate-limit at the proxy/WAF); JWT cookies are subpath-scoped and CSRF-protected; GitLab OAuth primary (dj-rest-auth SocialLoginView), password behind `AUTH_PASSWORD_LOGIN_ENABLED`; allauth login page backs the Django admin (`secure_admin_login` wrap in urls.py) |
| Reassign a GitLab account to a local user | `core/management/commands/link_gitlab_account.py` | never touches `is_staff`; `--delete-orphan` guarded by Person.user / ParticipantSubmission.linked_user |
| Conference model / admin policies | `core/models.py`, `core/admin.py` | slug reserved words in `clean()`; deletion gated by `Conference.is_referenced()` |
| PDF generation | `core/views.py` | `generate_program_pdf`, `generate_badges_pdf`; per-conference, reportlab + `core/fonts/*.ttf` |
| Publish workflow | `core/models.py` | `ParticipantSubmission.publish()`, `.unpublish()`, `.reject()`, `.restore()`, `.delete()`; status transitions are pending↔approved/rejected; dedup scoped to `conference`; `ParticipantAdmin` deletion unpublishes linked submissions first |
| Email on publish | `core/signals.py` | fires via `CoreConfig.ready()` |
| Env config | `backend/settings.py` | DJANGO_SECRET_KEY / DJANGO_DEBUG / DJANGO_ALLOWED_HOSTS / DJANGO_DB_PATH / DJANGO_STATIC_URL / DJANGO_STATIC_ROOT / DJANGO_MEDIA_ROOT / DJANGO_USE_HTTPS / DJANGO_CSRF_TRUSTED_ORIGINS, plus unprefixed RELATIVE_URL_ROOT and the login vars: AUTH_PASSWORD_LOGIN_ENABLED / AUTH_GITLAB_LOGIN_ENABLED / GITLAB_URL / GITLAB_CLIENT_ID / GITLAB_CLIENT_SECRET / GITLAB_OAUTH_CALLBACK_URL |

## CONVENTIONS

- Views: `generics.APIView`/generic classes mixed with `@api_view` functions (`generate_*`, `publish_submission`, `unpublish_submission`, `reject_submission`, `restore_submission`, `update_session`, `delete_session`); named `<Noun><Action>View`.
- Conference scoping: every view in `core/urls.py` is served under `/api/<slug>/…` and must resolve its conference. Class views inherit `ConferenceScopedMixin` (views.py: eager 404 on unknown slug in `initial()`, queryset filter, `perform_create` assignment, serializer context); function views call `get_conference_or_404(conference_slug)`. The only unscoped views are auth + `ConferenceListView`, registered globally in `backend/urls.py` BEFORE the slug include.
- Serializers: `<Model>Serializer` for read, `...WriteSerializer` split for writes. Serializer field lists are explicit and exclude `conference`; the write path gets the conference via the view's `save(conference=…)`. `TalkSerializer` narrows `session`/`day` querysets via the context conference (cross-conference FK ⇒ 400).
- Submission state changes go through the dedicated publish/unpublish/reject/restore actions; `status` and `rejection_message` are read-only in API serializers. `rejected` rows are excluded from the default submission list and cannot be edited through the tracking link; permanent deletion is Django-admin-only.
- URL paths kebab-case with trailing slash; API mounted under `/{RELATIVE_URL_ROOT}api/`, admin tails under the slug prefix (e.g. `/api/<slug>/admin/...`).
- `Conference` is the single config row: it owns the logistics (title, dates, location, card/hero/venue photos, short description, badge title), the web texts and the accommodation description; `year` and `status` are derived read-only properties. `GET conference-info/` returns the plain `ConferenceInfoSerializer` payload; `PATCH conference-info/edit/` (multipart-capable, `BlankAsNoneDateField` maps empty date strings to null) writes logistics + web fields. Read endpoints must stay side-effect free — no lazy row creation.
- Global default is `AllowAny`; admin views declare `authentication_classes=[JWTCookieAuthentication]` + `permission_classes=[IsAdminUser]` per-view — do not centralize into settings.
- JWT is global across conferences: one staff account administers every conference. Intended; do not scope tokens per conference.
- Admin login: GitLab OAuth is primary; password login stays behind `AUTH_PASSWORD_LOGIN_ENABLED` (fallback/testing/break-glass). At least one method must stay enabled — settings raise ImproperlyConfigured otherwise; do not weaken that startup guard. `AUTH_GITLAB_LOGIN_ENABLED` defaults on but is effective only with GITLAB_CLIENT_ID + GITLAB_CLIENT_SECRET; `GITLAB_OAUTH_CALLBACK_URL` (the SPA callback) is mandatory when GitLab is enabled and must match the GitLab application registration exactly. Route registration is conditional in `build_urlpatterns()` (`/api/auth/login/` and the `/api/auth/gitlab/` pair appear only when their flag is on); all auth routes stay global under `/api/auth/`, registered BEFORE the slug include, and allauth pages live under `/api/auth/allauth/`. The flags are also enforced at authentication time via `core.auth.backends.FlagAwareModelBackend` / `FlagAwareAllauthBackend` (the allauth login POST cannot bypass a disabled password method — the flag is checked at `authenticate()` time, not only by removing routes), and when GitLab is off the allauth provider is dead too: `SOCIALACCOUNT_PROVIDERS["gitlab"]["APPS"]` stays empty and an allauth provider 404 guard is registered. Session and CSRF cookies are explicitly `SameSite=Lax` (`SESSION_COOKIE_SAMESITE` / `CSRF_COOKIE_SAMESITE`). Tests toggle flags via `override_settings` + rebuilding urlpatterns (`gitlab_urls()` / `password_only_urls()` / `gitlab_only_urls()` in test_gitlab_auth.py).
- OAuth state is Django-signed (10-minute max age, own salt) and carries the conference slug for the post-login redirect; the nonce is also bound to a short-lived HttpOnly, SameSite=Lax cookie, and the code exchange (`GitLabLoginView`) validates and consumes it once (single-use, browser-bound) before any GitLab HTTP traffic. JWTs live only in HttpOnly `conference-jwt-access` / `conference-jwt-refresh` cookies (`JWT_AUTH_HTTPONLY=True`); login and refresh responses never echo tokens. Cookies are scoped to `/<RELATIVE_URL_ROOT>/`; login, refresh and config bootstrap the non-HttpOnly `csrftoken`, and `JWTCookieAuthentication` enforces `X-CSRFToken` for unsafe cookie-authenticated requests. `OptionalJWTCookieAuthentication` ignores stale cookies on public endpoints while admin views use the strict class. `CookieRefreshView` reads the refresh cookie and refreshes both cookies. Logout (`LogoutView`) requires a valid access cookie and CSRF, blacklists the refresh cookie, unsets both JWT cookies and flushes the Django session.
- `is_staff` is always manual: no GitLab group sync, no e-mail auto-connect (`SOCIALACCOUNT_EMAIL_AUTHENTICATION*` stay off; the social adapter keeps signup open but the account adapter blocks local self-signup). A first GitLab login creates a non-staff user; promotion happens in the Django admin, linking via `link_gitlab_account`. `Person.user` / `ParticipantSubmission.linked_user` are never auto-linked.
- Refresh-token rotation blacklists old tokens via `rest_framework_simplejwt.token_blacklist` (in INSTALLED_APPS); the browser stores the rotated HttpOnly refresh cookie and the SPA never reads it.
- Model changes require `makemigrations`. Every domain model carries a `conference` FK (`on_delete=CASCADE`, `preserve_default=False` in the squashed 0014); 0014 is hand-written — schema ops plus two idempotent data seeds (wsc2026 conference, fallback ConferenceInfo row).
- `views.py` uses explicit imports — do not reintroduce `from .models import *` / `from .serializers import *`.
- Media uploads via `ImageField` under MEDIA_ROOT (per-model `upload_to` subdirs: conferences/, participants/, people/, accommodation/, submissions/photos/, hiking/).
- Tests: `uv run pytest` with pytest-django (`DJANGO_SETTINGS_MODULE` from pyproject). `python_files` includes the Django-style `tests.py`; new suites go in `test_<domain>.py` with `Test*`-prefixed classes. `conftest.py` provides two conferences per test (`wsc`/`other` fixtures) — never assume `conference_id=1`. The isolation suite derives its route matrix from `core/urls.py`, so any new unscoped route fails it.
- Lint/typing: `uv run ruff check .` (extend-select I,B,SIM,BLE,EXE,RUF; RUF012 off for Django class attrs) and `uv run pyright` (django-stubs; attribute-access/function-member rules off — pyright can't run the stubs' mypy plugin; `venvPath`/`venv` also set here). Config lives in pyproject.toml.

## ANTI-PATTERNS (THIS APP)

- NEVER add an endpoint outside the `/api/<slug>/` include without conference scoping — `test_conference_isolation.py` builds its route matrix from `core/urls.py` and fails the suite for any unscoped route.
- NEVER include `dj_rest_auth.urls` wholesale at `/api/auth/` — it shadows the custom login/logout/gitlab registration and reintroduces routes the flags are supposed to remove. Register the specific views, as `build_urlpatterns()` does.
- NEVER move the auth routes behind the slug include, and never weaken the startup guard that requires at least one login method — a deployment with both methods off bricks every admin.
- NEVER remove or bypass the flag-aware auth backends (`core.auth.backends.FlagAwareModelBackend` / `FlagAwareAllauthBackend`): swapping in an always-on `ModelBackend` or plain allauth backend would let the allauth login POST authenticate with password even when `AUTH_PASSWORD_LOGIN_ENABLED=False`.
- NEVER let the allauth GitLab provider routes bypass `AUTH_GITLAB_LOGIN_ENABLED`: with the flag off, `SOCIALACCOUNT_PROVIDERS["gitlab"]["APPS"]` must stay empty and the provider 404 guard must stay registered, or the allauth GitLab URLs would keep serving sign-ins with credentials still configured.
- NEVER put JWTs back into auth JSON or localStorage. Keep `JWT_AUTH_COOKIE` / `JWT_AUTH_REFRESH_COOKIE` HttpOnly, keep the token-free serializers, and keep refresh/logout cookie-aware.
- NEVER change `GITLAB_OAUTH_CALLBACK_URL` without updating the GitLab application registration (exact-match redirect URIs, no trailing-slash tolerance).
- NEVER auto-provision admin rights from GitLab (no group authorization, no e-mail auto-connect, no automatic `is_staff`); promotion and linking are manual. `link_gitlab_account` must keep never touching `is_staff`.
- NEVER allow deleting a Conference while any row references it: all domain models cascade from `Conference`, so `ConferenceAdmin` hides the delete action when `Conference.is_referenced()` is true, re-checks in `delete_model`/`delete_queryset`, and keeps `actions = None`. `is_referenced()` walks `_meta.get_fields(include_hidden=True)`, so a new conference FK (even a hidden one) is covered automatically; do not filter relations out of that check.
- `AccommodationOptionListView` (views.py) is dead code — defined but never routed. Deliberate minimal diff; do not wire it up or delete it casually.
- `ConferenceDayDeleteView.destroy` calls bare `day.delete()` with no guard; `UnscheduledTalkDeleteView` 400s on scheduled talks. Both deliberate — cascade rules and rationale live in root AGENTS.md; keep guards as they are. Beware: Talk→Abstract FK direction means day/talk deletes orphan the Abstract row.
- `AccommodationOptionEditView` and `HikingStopEditView` call `objects.get(pk, conference=…)` unguarded in patch/delete: unknown or cross-conference pks surface as 500, never 404. Deliberate security choice — keep; tests pin the 500.
- `ParticipantListView` and `AbstractListView` are public `ListAPIView`s: reads are anonymous, writes are not exposed. Do not reintroduce public POSTs; only registration (`/submit/`) and token-based tracking edits (`/track/<token>/`) are public writes.
- Do not expose permanent `DELETE` for `ParticipantSubmission` in the API: the frontend uses reject/restore, and permanent deletion is Django-admin-only. Rejected submissions must not be editable through the tracking link.
- `Abstract.participant` is required with `CASCADE`; null-participant abstracts are deleted by migration `0037`. Do not make it nullable again.
- `ParticipantAdmin.delete_model`/`delete_queryset` call `ParticipantSubmission.unpublish()` first. Do not bypass this with a raw participant `QuerySet.delete()`, or linked submissions keep stale public links.
- Shared `published_participant`/`published_abstract` links are possible through Django admin, raw ORM, legacy rows, or a concurrent publish race, even though the frontend publish flow guards against them. The ownership branches in `unpublish()` and `delete()` must stay until a decision is made: either deny sharing and harden the model (unique constraints/locking) or allow it and add frontend controls.
- Deleting a conference day or an unscheduled talk orphans the linked `Abstract` (FK sits on Talk). Deliberate admin choice (2026-10-03); do not add delete cascades.
- PDF generators (`generate_program_pdf`, `generate_badges_pdf`) build into `io.BytesIO`, then write bytes into the response — do not pass the HttpResponse to canvas directly (pyright compatibility, bytes unchanged). Both filter every queryset by conference; badges header is `badge_title or title`, footer is `location`.
- `traceback.print_exc()` debug calls and Russian comments exist in models/views/settings — leave them.
- Signals: publish email fires on status transition to approved via `_old_status` captured in pre_save — `QuerySet.update()`/bulk paths silently skip it, and `fail_silently=False` means mail errors raise inside the publish request.
- No pagination configured: list endpoints return all rows.
