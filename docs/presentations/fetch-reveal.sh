#!/bin/sh
# Download one Reveal.js release into vendor/reveal.js/<VERSION>/, the copy every deck here loads.
#
# Usage: sh fetch-reveal.sh VERSION        e.g. sh fetch-reveal.sh 5.1.0
# Fetches the core CSS and JS, the four plugins the decks use, and the licence, from cdnjs
# (licence from the project's own GitHub). An existing version folder is left untouched.
# After fetching, point a deck at it by changing the version in its index.html paths.
set -eu

if [ $# -ne 1 ]; then
  echo "usage: sh fetch-reveal.sh VERSION" >&2
  exit 2
fi
VERSION=$1
HERE=$(cd "$(dirname "$0")" && pwd)
DEST="$HERE/vendor/reveal.js/$VERSION"
CDN="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/$VERSION"

if [ -e "$DEST" ]; then
  echo "$DEST already exists; delete it first to re-fetch" >&2
  exit 1
fi

TMP="$DEST.partial"
rm -rf "$TMP"
for f in reveal.min.css reveal.min.js \
         plugin/highlight/highlight.min.js plugin/notes/notes.min.js \
         plugin/zoom/zoom.min.js plugin/search/search.min.js; do
  mkdir -p "$TMP/$(dirname "$f")"
  curl -fsS -o "$TMP/$f" "$CDN/$f" || { echo "failed: $CDN/$f" >&2; rm -rf "$TMP"; exit 1; }
done
curl -fsS -o "$TMP/LICENSE" "https://raw.githubusercontent.com/hakimel/reveal.js/$VERSION/LICENSE" \
  || { echo "failed: LICENSE for $VERSION" >&2; rm -rf "$TMP"; exit 1; }
mv "$TMP" "$DEST"
echo "fetched Reveal.js $VERSION into $DEST"
