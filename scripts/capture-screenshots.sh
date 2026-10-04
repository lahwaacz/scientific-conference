#!/usr/bin/env bash
# Capture full-page screenshots of all public frontend routes for visual
# regression comparison. Output is gitignored; re-run to regenerate.
#
# Usage: bash scripts/capture-screenshots.sh
#
# Reproducibility contract:
#   - backend: freshly migrated + loaddata core/fixtures/program.json
#   - frontend: production build against that backend, served statically
#   - browser: system chromium via @playwright/cli, 1440x900, reduced motion
#   - same tree + same fixture == comparable pixels
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
  REACT_APP_BACKEND_API_BASE_URL="http://localhost:$BACKEND_PORT" \
  npm run build >/dev/null)
python3 -m http.server "$FRONTEND_PORT" -d "$FRONTEND/build" \
  >/dev/null 2>&1 &
FRONTEND_PID=$!

# --- wait for both servers ---------------------------------------------------
for i in $(seq 1 60); do
  backend_up=false; frontend_up=false
  curl -sf "http://localhost:$BACKEND_PORT/api/conference-info/" \
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
  $PWCLI goto "http://localhost:$FRONTEND_PORT/#$2" >/dev/null
  sleep 2 # let data fetches settle
  $PWCLI screenshot --full-page --filename "$OUT/$1.png" >/dev/null
  echo "captured $1"
}

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

$PWCLI kill-all >/dev/null 2>&1 || true
echo "done: $OUT"
