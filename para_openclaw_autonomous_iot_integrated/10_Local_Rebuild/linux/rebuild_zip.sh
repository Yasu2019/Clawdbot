#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$(dirname "$ROOT")"
zip -r "$(basename "$ROOT").zip" "$(basename "$ROOT")"
echo "ZIP regenerated: $(dirname "$ROOT")/$(basename "$ROOT").zip"
