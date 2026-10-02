# BACKEND KNOWLEDGE BASE

## OVERVIEW

Django 5.2 + DRF 3.16 + SimpleJWT backend, single app `core`, SQLite (root-level contract/subpath/CI rules live in the repo-root AGENTS.md, not here).

## STRUCTURE

```
backend/
├── backend/    # project package: settings.py, urls.py, wsgi.py, asgi.py
│               # docstrings still say "quotes project" — stale, ignore
├── core/       # the ONLY app — all domain logic
│   ├── models.py           # 14 models
│   ├── views.py            # ~810 lines, ~39 DRF views
│   ├── serializers.py
│   ├── urls.py             # full endpoint table
│   ├── admin.py            # decorator-style @admin.register
│   ├── signals.py          # email on publish; wired via CoreConfig.ready() (apps.py)
│   ├── migrations/         # 12 migrations
│   ├── fixtures/program.json  # seed data
│   └── fonts/DejaVu*.ttf   # required by reportlab PDF generation
├── manage.py
├── Dockerfile
└── requirements.txt        # UTF-16 LE + CRLF
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Endpoint list | `core/urls.py` | explicit `path()`, no router |
| Auth config | `backend/settings.py` | SIMPLE_JWT: 1h access / 7d refresh |
| PDF generation | `core/views.py` | `generate_program_pdf` (line 28), `generate_badges_pdf` (line 255); reportlab + `core/fonts/*.ttf` |
| Publish workflow | `core/models.py` | `ParticipantSubmission.publish()` (line 210), `.delete()` (line 297) |
| Email on publish | `core/signals.py` | fires via `CoreConfig.ready()` |
| Env config | `backend/settings.py` | DJANGO_SECRET_KEY / DJANGO_DEBUG / DJANGO_ALLOWED_HOSTS / DJANGO_DB_PATH / DJANGO_STATIC_URL / DJANGO_STATIC_ROOT / DJANGO_MEDIA_ROOT / DJANGO_USE_HTTPS / DJANGO_CSRF_TRUSTED_ORIGINS, plus unprefixed RELATIVE_URL_ROOT |

## CONVENTIONS

- Views: `generics.APIView`/generic classes mixed with `@api_view` functions (`generate_*`, `publish_submission`, `update_session`, `delete_session`); named `<Noun><Action>View`.
- Serializers: `<Model>Serializer` for read, `...WriteSerializer` split for writes.
- URL paths kebab-case with trailing slash; API mounted under `/{RELATIVE_URL_ROOT}api/`, admin under `/api/admin/`.
- Global default is `AllowAny`; admin views declare `authentication_classes=[JWTAuthentication]` + `permission_classes=[IsAdminUser]` per-view — do not centralize into settings.
- Model changes require `makemigrations` (12 migrations so far).
- Media uploads via `ImageField` under MEDIA_ROOT (per-model `upload_to` subdirs: participants/, organizers/, organizingCommittee/, accommodation/, submissions/photos/, hiking/).
- `requirements.txt` encoding gotcha: see root AGENTS.md NOTES — tree annotation above is the reminder.

## ANTI-PATTERNS (THIS APP)

- `views.py` has wildcard imports + duplicate imports: match existing style, do not "clean up" casually.
- `token_blacklist` is NOT in INSTALLED_APPS despite `BLACKLIST_AFTER_ROTATION=True` — known quirk, do not "fix" blindly.
- The `media static()` route is duplicated in both urlconfs (`backend/urls.py` and `core/urls.py`) — leave it.
- `ConferenceDayDeleteView.destroy` (views.py:618) calls bare `day.delete()` with no guard; `UnscheduledTalkDeleteView` 400s on scheduled talks. Both deliberate — cascade rules and rationale live in root AGENTS.md; keep guards as they are.
- Dead `React` model + `/wel/` route are template leftovers — do not build on them.
- Single-row config tables (`ConferenceInfo`, `AccommodationInfo`) rely on `get_or_create(id=1)` by convention, not DB constraints.
- `traceback.print_exc()` debug calls and Russian comments exist in models/views/settings — leave them.
- Signals: publish email fires on status transition to approved via `_old_status` captured in pre_save — `QuerySet.update()`/bulk paths silently skip it, and `fail_silently=False` means mail errors raise inside the publish request.
- No pagination configured: list endpoints return all rows.
