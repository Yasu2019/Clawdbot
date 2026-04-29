#!/usr/bin/env bash
set -euo pipefail

PREFIX="${1:-before-julia-worker}"
TS="$(date +%Y%m%d-%H%M%S)"
NAME="${PREFIX}-${TS}"

echo "Checking git repository..."
git status

echo "Creating backup branch: ${NAME}"
git branch "${NAME}"

echo "Creating backup tag: ${NAME}"
git tag "${NAME}"

echo "Backup created: ${NAME}"
