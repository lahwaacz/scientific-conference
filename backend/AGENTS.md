# BACKEND KNOWLEDGE BASE

## OVERVIEW

Django 5.2 + DRF 3.16 + SimpleJWT backend, single app `core`, SQLite (root-level contract/subpath/CI rules live in the repo-root AGENTS.md, not here).

## STRUCTURE

```
backend/
├── backend/    # project package: settings.py, urls.py, wsgi.py, asgi.py
├── core/       # the ONLY app — all domain logic
│   ├── models.py           # 13 models
│   ├── views.py            # ~830 lines, ~38 DRF views
│   ├── serializers.py
│   ├── urls.py             # full endpoint table
│   ├── admin.py            # decorator-style @admin.register
│   ├── signals.py          # email on publish; wired via CoreConfig.ready() (apps.py)
│   ├── migrations/         # 13 migrations
│   ├── fixtures/program.json  # seed data
│   └── fonts/DejaVu*.ttf   # required by reportlab PDF generation
├── manage.py
├── Dockerfile
└── requirements.txt        # UTF-8, one `pkg==version` pin per line
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Endpoint list | `core/urls.py` | explicit `path()`, no router |
| Auth config | `backend/settings.py` | SIMPLE_JWT: 1h access / 7d refresh |
| PDF generation | `core/views.py` | `generate_program_pdf` (line 53), `generate_badges_pdf` (line 291); reportlab + `core/fonts/*.ttf` |
| Publish workflow | `core/models.py` | `ParticipantSubmission.publish()` (line 209), `.delete()` (line 294) |
| Email on publish | `core/signals.py` | fires via `CoreConfig.ready()` |
| Env config | `backend/settings.py` | DJANGO_SECRET_KEY / DJANGO_DEBUG / DJANGO_ALLOWED_HOSTS / DJANGO_DB_PATH / DJANGO_STATIC_URL / DJANGO_STATIC_ROOT / DJANGO_MEDIA_ROOT / DJANGO_USE_HTTPS / DJANGO_CSRF_TRUSTED_ORIGINS, plus unprefixed RELATIVE_URL_ROOT |

## CONVENTIONS

- Views: `generics.APIView`/generic classes mixed with `@api_view` functions (`generate_*`, `publish_submission`, `update_session`, `delete_session`); named `<Noun><Action>View`.
- Serializers: `<Model>Serializer` for read, `...WriteSerializer` split for writes.
- URL paths kebab-case with trailing slash; API mounted under `/{RELATIVE_URL_ROOT}api/`, admin under `/api/admin/`.
- Global default is `AllowAny`; admin views declare `authentication_classes=[JWTAuthentication]` + `permission_classes=[IsAdminUser]` per-view — do not centralize into settings.
- Refresh-token rotation blacklists old tokens via `rest_framework_simplejwt.token_blacklist` (in INSTALLED_APPS); frontend refresh flow stores the rotated pair.
- Model changes require `makemigrations` (13 migrations so far).
- `views.py` uses explicit imports — do not reintroduce `from .models import *` / `from .serializers import *`.
- Media uploads via `ImageField` under MEDIA_ROOT (per-model `upload_to` subdirs: participants/, organizers/, organizingCommittee/, accommodation/, submissions/photos/, hiking/).

## ANTI-PATTERNS (THIS APP)

- `ConferenceDayDeleteView.destroy` (views.py:659) calls bare `day.delete()` with no guard; `UnscheduledTalkDeleteView` 400s on scheduled talks. Both deliberate — cascade rules and rationale live in root AGENTS.md; keep guards as they are.
- Single-row config tables (`ConferenceInfo`, `AccommodationInfo`) rely on `get_or_create(id=1)` by convention, not DB constraints.
- `traceback.print_exc()` debug calls and Russian comments exist in models/views/settings — leave them.
- Signals: publish email fires on status transition to approved via `_old_status` captured in pre_save — `QuerySet.update()`/bulk paths silently skip it, and `fail_silently=False` means mail errors raise inside the publish request.
- No pagination configured: list endpoints return all rows.
