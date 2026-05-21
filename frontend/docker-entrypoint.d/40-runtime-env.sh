#!/bin/sh
set -eu

escape_js_string() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

{
  printf 'window.__TRIPLY_ENV__ = {\n'
  first=1
  env | sort | while IFS='=' read -r name value; do
    case "$name" in
      VITE_API_URL|VITE_GRAFANA_DASHBOARD_URL)
        if [ "$first" -eq 0 ]; then
          printf ',\n'
        fi
        first=0
        printf '  "%s": "%s"' "$name" "$(escape_js_string "$value")"
        ;;
    esac
  done
  printf '\n};\n'
} > /usr/share/nginx/html/env.js
