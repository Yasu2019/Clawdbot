#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python app/archon_harness.py
python app/hermes_learning_loop.py
echo "Done."
