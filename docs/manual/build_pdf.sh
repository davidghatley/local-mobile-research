#!/usr/bin/env bash
# Export the manual to PDF (letter) and page PNGs with headless Chromium.
# index.html is a page fragment (the Artifact publisher adds the skeleton), so it is
# wrapped in a doctype + charset first, next to the original so relative paths work.
# Usage: docs/manual/build_pdf.sh        THEME=dark for a dark export
set -euo pipefail
M="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$M/pdf"
tmp="$M/.print.html"
{ printf '<!doctype html><html lang="en" data-theme="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n' "${THEME:-light}"
  cat "$M/index.html"; echo '</html>'; } > "$tmp"
chromium --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer --virtual-time-budget=8000 \
  --print-to-pdf="$M/pdf/manual.pdf" "file://$tmp" 2>/dev/null
rm -f "$tmp"
echo "pdf/manual.pdf ($(pdfinfo "$M/pdf/manual.pdf" | awk '/^Pages/{print $2}') pages)"
