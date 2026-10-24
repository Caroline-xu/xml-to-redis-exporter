#!/usr/bin/env bash
# Usage: ./export.sh [-v] /path/to/xml
# Starts Redis with docker compose, runs the exporter once in a container
# with the given XML file mounted in, and (with -v) prints all saved keys.
set -euo pipefail

VERBOSE=""
XML_PATH=""

for arg in "$@"; do
  case "$arg" in
    -v|--verbose) VERBOSE="-v" ;;
    *) XML_PATH="$arg" ;;
  esac
done

if [ -z "$XML_PATH" ]; then
  echo "Usage: ./export.sh [-v] /path/to/xml" >&2
  exit 1
fi
if [ ! -f "$XML_PATH" ]; then
  echo "Error: file not found: $XML_PATH" >&2
  exit 1
fi

# Absolute path of the XML file, so it can be mounted into the container.
XML_ABS="$(cd "$(dirname "$XML_PATH")" && pwd)/$(basename "$XML_PATH")"

cd "$(dirname "$0")"

docker compose up -d redis
# shellcheck disable=SC2086
docker compose run --rm \
  -v "$XML_ABS:/data/input.xml:ro" \
  app python -m app.exporter $VERBOSE /data/input.xml
