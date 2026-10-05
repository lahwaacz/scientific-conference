#!/usr/bin/env bash
# Capture full-page screenshots of the landing page and all public frontend
# routes of the seeded conference for visual regression comparison. Output is
# gitignored; re-run to regenerate.
#
# Usage: bash scripts/capture-screenshots.sh
#
# Reproducibility contract:
#   - backend: freshly migrated + loaddata core/fixtures/program.json
#   - frontend: production build against that backend, served statically
#   - built with VITE_BASE_PATH=/ so asset URLs are absolute at the root
#     and resolve at any page depth under python3 -m http.server
#   - build/wsc2026/index.html SPA-fallback shim: python http.server has
#     no SPA fallback, so the shim serves the app at /wsc2026/ (assets
#     still resolve because the base is /)
#   - browser: system chromium via @playwright/cli, 1440x900, reduced motion
#   - same tree + same fixture == comparable pixels
#
# URL anatomy: the landing capture is the root path "/"; every conference
# capture runs under /wsc2026/#<hash-route> (slug-scoped app), and the
# backend readiness check uses the scoped API /api/wsc2026/conference-info/.
#
# Known nondeterminism: venue.png embeds an external Google Maps iframe
# whose tiles vary run-to-run; every other capture is byte-stable.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
OUT="$ROOT/screenshots"
BACKEND_PORT=8000
FRONTEND_PORT=3741
PWCLI="npx -y @playwright/cli@0.1.22"

cleanup() {
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  $PWCLI kill-all >/dev/null 2>&1 || true
}
trap cleanup EXIT

# --- backend: migrate + seed + runserver ------------------------------------
(cd "$BACKEND" && uv run python manage.py migrate --run-syncdb --noinput)
(cd "$BACKEND" && uv run python manage.py loaddata program.json)
(cd "$BACKEND" && DJANGO_ALLOWED_HOSTS=localhost \
  DJANGO_CSRF_TRUSTED_ORIGINS="http://localhost:$FRONTEND_PORT" \
  uv run python manage.py runserver "$BACKEND_PORT" \
    >/dev/null 2>&1) &
BACKEND_PID=$!

# --- frontend: production build + static serve ------------------------------
(cd "$FRONTEND" && \
  VITE_BACKEND_API_BASE_URL="http://localhost:$BACKEND_PORT" \
  VITE_BASE_PATH=/ \
  npm run build >/dev/null)
# python http.server has no SPA fallback; the shim serves the app at
# /wsc2026/ (assets resolve because base is /).
mkdir -p "$FRONTEND/build/wsc2026"
cp "$FRONTEND/build/index.html" "$FRONTEND/build/wsc2026/index.html"
python3 -m http.server "$FRONTEND_PORT" -d "$FRONTEND/build" \
  >/dev/null 2>&1 &
FRONTEND_PID=$!

# --- wait for both servers ---------------------------------------------------
for i in $(seq 1 60); do
  backend_up=false; frontend_up=false
  curl -sf "http://localhost:$BACKEND_PORT/api/wsc2026/conference-info/" \
    >/dev/null 2>&1 && backend_up=true
  curl -sf "http://localhost:$FRONTEND_PORT/" >/dev/null 2>&1 \
    && frontend_up=true
  $backend_up && $frontend_up && break
  sleep 1
done

# --- captures ----------------------------------------------------------------
mkdir -p "$OUT"
$PWCLI open "http://localhost:$FRONTEND_PORT/" >/dev/null
$PWCLI resize 1440 900 >/dev/null
$PWCLI set-reduced-motion reduce >/dev/null

capture() { # $1 = label, $2 = hash route
  $PWCLI goto "http://localhost:$FRONTEND_PORT/wsc2026/#$2" >/dev/null
  sleep 2 # let data fetches settle
  $PWCLI screenshot --full-page --filename "$OUT/$1.png" >/dev/null
  echo "captured $1"
}

# Landing page: plain root path, no hash (the landing ignores hashes).
$PWCLI goto "http://localhost:$FRONTEND_PORT/" >/dev/null
sleep 2 # let data fetches settle
$PWCLI screenshot --full-page --filename "$OUT/landing.png" >/dev/null
echo "captured landing"

capture home      /
capture program   /program
capture abstracts /abstracts
capture participants /participants
capture registration /registration
capture venue     /venue
capture accommodation /accommodation
capture hiking    /hiking

# --- admin captures (deterministic dev superuser, JWT in localStorage) ------
ADMIN_USER=screenshots
ADMIN_PASS=screenshots
(cd "$BACKEND" && uv run python manage.py shell -c \
  "from django.contrib.auth import get_user_model; U=get_user_model(); \
   u=U.objects.filter(username='$ADMIN_USER').first() or U(username='$ADMIN_USER'); \
   u.is_staff=True; u.is_superuser=True; u.set_password('$ADMIN_PASS'); u.save()")

TOKENS=$(curl -sf -X POST "http://localhost:$BACKEND_PORT/api/auth/login/" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$ADMIN_USER\",\"password\":\"$ADMIN_PASS\"}")
ACCESS=$(printf '%s' "$TOKENS" | python3 -c \
  "import json,sys; print(json.load(sys.stdin)['access'])")
REFRESH=$(printf '%s' "$TOKENS" | python3 -c \
  "import json,sys; print(json.load(sys.stdin)['refresh'])")

$PWCLI goto "http://localhost:$FRONTEND_PORT/" >/dev/null
$PWCLI eval "() => { localStorage.setItem('access_token', '$ACCESS'); \
  localStorage.setItem('refresh_token', '$REFRESH'); }" >/dev/null

capture admin-panel            /admin-panel
capture admin-participants     /admin-panel/participants-info
capture admin-edit-participants /admin-panel/edit-participants
capture admin-edit-program     /admin-panel/edit-program
capture admin-web-info         /admin-panel/edit-web-info
capture admin-web-info-home    /admin-panel/edit-web-info/home
capture admin-web-info-registration /admin-panel/edit-web-info/registration
capture admin-web-info-program /admin-panel/edit-web-info/program
capture admin-web-info-venue   /admin-panel/edit-web-info/venue
capture admin-web-info-accommodation /admin-panel/edit-web-info/accommodation
capture admin-web-info-hiking  /admin-panel/edit-web-info/hiking
capture admin-web-info-footer  /admin-panel/edit-web-info/footer

# --- identical-PNG guard: landing must differ from every other capture ------
# Catches the failure mode where the slug path or shim is broken and every
# capture silently renders the landing page instead.
for png in "$OUT"/*.png; do
  label="$(basename "$png" .png)"
  if [ "$label" = "landing" ]; then
    continue
  fi
  if cmp -s "$OUT/landing.png" "$png"; then
    echo "ERROR: $label.png is byte-identical to landing.png" >&2
    exit 1
  fi
done

$PWCLI kill-all >/dev/null 2>&1 || true
echo "done: $OUT"
