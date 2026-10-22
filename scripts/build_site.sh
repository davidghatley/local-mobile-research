#!/usr/bin/env bash
# Copy the manual into site/manual (the manual is a page fragment; wrap it so it is a real page).
set -euo pipefail
R="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$R/site/manual"; mkdir -p "$R/site/manual"
cp -r "$R/docs/manual/assets" "$R/docs/manual/pdf" "$R/site/manual/"
{ printf '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
  cat "$R/docs/manual/index.html"; echo '</html>'; } > "$R/site/manual/index.html"
