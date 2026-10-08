#!/usr/bin/env bash
# Capture full-page screenshots of the landing page and all public frontend
# routes of the seeded conference for visual regression comparison. Output is
# gitignored; re-run to regenerate.
#
# Usage: bash scripts/capture-screenshots.sh
#        bash scripts/capture-screenshots.sh --backend-port 8001
#        bash scripts/capture-screenshots.sh --backend-port 8001 --frontend-port 3742
#        bash scripts/capture-screenshots.sh --help
#
# Reproducibility contract:
#   - backend: freshly migrated + loaddata the demo fixtures
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
usage() {
  echo "usage: $0 [--backend-port N] [--frontend-port N]"
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

BACKEND_PORT=8000
FRONTEND_PORT=3741
while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend-port)
      [[ $# -ge 2 && "$2" =~ ^[0-9]+$ ]] || die "--backend-port needs a numeric value"
      BACKEND_PORT="$2"; shift 2 ;;
    --frontend-port)
      [[ $# -ge 2 && "$2" =~ ^[0-9]+$ ]] || die "--frontend-port needs a numeric value"
      FRONTEND_PORT="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      usage >&2; die "unknown argument: $1" ;;
  esac
done
PWCLI="npx -y @playwright/cli@0.1.22"

# --- pre-flight: the ports must be free, or the captures would silently run
# against a foreign server (seen in the wild: an orphan dev server without
# this script's CORS env poisoned the whole baseline with spinners).
port_open() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
port_open "$BACKEND_PORT" && die "port $BACKEND_PORT is already in use (pass --backend-port to override)"
port_open "$FRONTEND_PORT" && die "port $FRONTEND_PORT is already in use (pass --frontend-port to override)"

# --- background servers get their own process groups so cleanup kills the
# whole tree (uv spawns python; a bare `kill $PID` only hits the subshell).
set -m
cleanup() {
  [[ -n "${BACKEND_PID:-}" ]] && kill -- "-$BACKEND_PID" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill -- "-$FRONTEND_PID" 2>/dev/null || true
  $PWCLI kill-all >/dev/null 2>&1 || true
}
trap cleanup EXIT

# --- backend: migrate + seed + runserver ------------------------------------
(cd "$BACKEND" && uv run python manage.py migrate --run-syncdb --noinput)
(cd "$BACKEND" && uv run python manage.py loaddata conferences.json participants.json program.json)

# --- demo tracking token: the fixtures seed wsc2026 submissions and the
# token is auto-generated, so resolve it from the DB to capture the public
# tracking page below. tail strips Django 5.2's shell auto-import notice
# ("N objects imported automatically"), which is printed on stdout. Fail
# loudly if the seeding yielded nothing usable.
TRACKING_TOKEN=$(cd "$BACKEND" && uv run python manage.py shell -c \
  "from core.models import ParticipantSubmission; \
   print(ParticipantSubmission.objects.filter(conference__slug='wsc2026').order_by('pk').first().tracking_token)" \
  | tail -n 1)
[[ -n "$TRACKING_TOKEN" ]] || die "no tracking token resolved from seeded wsc2026 submissions"
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
set +m

# --- wait for both servers ---------------------------------------------------
# The liveness checks matter: a server that dies (bad port, failed bind)
# must abort the run instead of letting the readiness curl hit some other
# process that happens to listen there.
for _ in $(seq 1 60); do
  backend_up=false; frontend_up=false
  curl -sf "http://localhost:$BACKEND_PORT/api/wsc2026/conference-info/" \
    >/dev/null 2>&1 && backend_up=true
  curl -sf "http://localhost:$FRONTEND_PORT/" >/dev/null 2>&1 \
    && frontend_up=true
  $backend_up && $frontend_up && break
  kill -0 "$BACKEND_PID" 2>/dev/null || die "backend server exited before becoming ready"
  kill -0 "$FRONTEND_PID" 2>/dev/null || die "frontend server exited before becoming ready"
  sleep 1
done
$backend_up || die "backend on :$BACKEND_PORT never became ready"
$frontend_up || die "frontend on :$FRONTEND_PORT never became ready"

# --- CORS contract: the browser on :$FRONTEND_PORT must be allowed to read
# the API, or every in-page fetch silently fails and all captures degrade
# to spinners and fallbacks (byte-stable, but wrong).
curl -si "http://localhost:$BACKEND_PORT/api/conferences/" \
  -H "Origin: http://localhost:$FRONTEND_PORT" \
  | grep -qi "^access-control-allow-origin:" \
  || die "backend does not send CORS headers for http://localhost:$FRONTEND_PORT"

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
capture track     "/track/$TRACKING_TOKEN"

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
capture admin-program-info     /admin-panel/edit-program/info
capture admin-web-info         /admin-panel/edit-web-info
capture admin-web-info-home    /admin-panel/edit-web-info/home
capture admin-web-info-registration /admin-panel/edit-web-info/registration
capture admin-web-info-venue  /admin-panel/edit-web-info/venue
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
