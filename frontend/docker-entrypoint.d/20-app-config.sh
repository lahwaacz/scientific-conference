#!/bin/sh
# Writes the runtime app config (app-config.js) from env vars. BASE_PATH is
# the deployment's URL prefix, e.g. "/conference-demo". API_BASE is optional
# and defaults to the same-origin prefix. Without BASE_PATH the baked
# default (an empty config) is kept and the app falls back to its
# build-time values.
set -e

if [ -z "${BASE_PATH:-}" ]; then
  exit 0
fi

# Values are embedded in a JavaScript string, so reject anything that could
# terminate it or start a new statement (quotes, backslashes, tags, control
# characters). URL paths and origins need none of those characters.
is_safe_url_value() {
  case "$1" in
    *[!A-Za-z0-9._~:/@%+-]*)
      return 1
      ;;
  esac
  return 0
}

stripped="$(printf '%s' "$BASE_PATH" | tr -d '/')"
if [ -n "$stripped" ]; then
  base_path="/$stripped"
else
  base_path=""
fi
api_base="${API_BASE:-$base_path}"
api_base="${api_base%/}"
if [ -z "$api_base" ]; then
  api_base="/"
fi

if ! is_safe_url_value "$base_path" || ! is_safe_url_value "$api_base"; then
  echo "app-config: BASE_PATH/API_BASE contain unsupported characters" >&2
  exit 1
fi

app_config_path="${APP_CONFIG_OUTPUT:-/usr/share/nginx/html/app-config.js}"
printf 'window.__APP_CONFIG__ = { basePath: "%s/", apiBase: "%s" };\n' \
  "$base_path" "$api_base" \
  > "$app_config_path"
