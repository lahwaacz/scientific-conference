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

stripped="$(echo "$BASE_PATH" | tr -d '/')"
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
printf 'window.__APP_CONFIG__ = { basePath: "%s/", apiBase: "%s" };\n' \
  "$base_path" "$api_base" \
  > /usr/share/nginx/html/app-config.js
