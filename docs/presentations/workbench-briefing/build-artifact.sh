#!/bin/sh
# Build the claude.ai Artifact copy of this deck into OUT_DIR.
#
# The deck loads Reveal.js from ../vendor/reveal.js/<version>/. The Artifact host wraps the page
# in its own <html>/<head>/<body>, cannot serve a path above the page, and its CSP blocks
# stylesheets from CDNs. So this strips the document skeleton, copies the vendored reveal.min.css
# beside the page as reveal.css, and points the scripts at the same version on cdnjs.
#
# It also warns when npm has a newer Reveal.js release than the vendored one. The warning never
# fails the build; upgrading is a deliberate step (../fetch-reveal.sh <version>, then edit index.html).
#
# Usage: sh build-artifact.sh OUT_DIR
# Writes: OUT_DIR/workbench-deck.html, OUT_DIR/theme.css, OUT_DIR/reveal.css
# Then publish OUT_DIR/workbench-deck.html with reveal.css and theme.css as supporting files.
set -eu

if [ $# -ne 1 ]; then
  echo "usage: sh build-artifact.sh OUT_DIR" >&2
  exit 2
fi
OUT_DIR=$1
SRC_DIR=$(cd "$(dirname "$0")" && pwd)

VERSION=$(sed -n 's#.*\.\./vendor/reveal\.js/\([0-9][0-9.]*\)/reveal\.min\.css.*#\1#p' "$SRC_DIR/index.html" | head -n 1)
if [ -z "$VERSION" ]; then
  echo "index.html does not load ../vendor/reveal.js/<version>/reveal.min.css" >&2
  exit 1
fi
VENDOR="$SRC_DIR/../vendor/reveal.js/$VERSION"
if [ ! -s "$VENDOR/reveal.min.css" ]; then
  echo "Reveal.js $VERSION is not vendored; run: sh $SRC_DIR/../fetch-reveal.sh $VERSION" >&2
  exit 1
fi

# Newer release? Warn only; a network failure is reported, not fatal.
LATEST=$(curl -fsS --max-time 10 https://registry.npmjs.org/-/package/reveal.js/dist-tags 2>/dev/null \
  | sed -n 's/.*"latest":"\([^"]*\)".*/\1/p' || true)
if [ -z "$LATEST" ]; then
  echo "warning: could not check npm for the latest Reveal.js release" >&2
elif [ "$LATEST" != "$VERSION" ]; then
  echo "warning: Reveal.js $LATEST is available; this deck uses $VERSION." >&2
  echo "         To upgrade: sh $SRC_DIR/../fetch-reveal.sh $LATEST, then change $VERSION in index.html" >&2
fi

mkdir -p "$OUT_DIR"
sed -e '/^<!doctype html>$/d' \
    -e '/^<html lang="en">$/d' \
    -e '/^<\/\{0,1\}head>$/d' \
    -e '/^<\/\{0,1\}body>$/d' \
    -e '/^<\/html>$/d' \
    -e '/^<meta charset/d' \
    -e '/^<meta name="viewport"/d' \
    -e "s#\.\./vendor/reveal\.js/$VERSION/reveal\.min\.css#reveal.css#" \
    -e "s#\.\./vendor/reveal\.js/$VERSION/#https://cdnjs.cloudflare.com/ajax/libs/reveal.js/$VERSION/#g" \
    "$SRC_DIR/index.html" > "$OUT_DIR/workbench-deck.html"

if grep -qE '<(html|head|body)[ >]' "$OUT_DIR/workbench-deck.html"; then
  echo "document skeleton left in workbench-deck.html; check index.html's tag lines" >&2
  exit 1
fi
if grep -q '\.\./vendor/' "$OUT_DIR/workbench-deck.html"; then
  echo "a ../vendor/ path is left in workbench-deck.html; check index.html's Reveal.js paths" >&2
  exit 1
fi

cp "$SRC_DIR/theme.css" "$OUT_DIR/theme.css"
cp "$VENDOR/reveal.min.css" "$OUT_DIR/reveal.css"

echo "built $OUT_DIR/workbench-deck.html (Reveal.js $VERSION, $(grep -c '<section' "$OUT_DIR/workbench-deck.html") sections)"
