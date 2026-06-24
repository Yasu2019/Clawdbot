#!/usr/bin/env bash
set -euo pipefail
CASE_DIR="${1:?case_dir}"
INPUT="${2:-test.in}"
STEM="${INPUT%.in}"
RENDER="${3:-/home/yasu/clawstack_satellite/scripts/impact_vtk_to_png.py}"
VENV="${IMPACT_PNG_VENV:-/tmp/impact_png_venv}"

# Prefer latest surface VTK (lighter; von Mises on shell surface). Impact names: test.in_<time>.vtk
VTK="$(ls -1 "$CASE_DIR/${INPUT}"_surface_*.vtk 2>/dev/null | sort -V | tail -1 || true)"
if [ -z "$VTK" ]; then
  VTK="$(ls -1 "$CASE_DIR/${STEM}"_surface_*.vtk 2>/dev/null | sort -V | tail -1 || true)"
fi
if [ -z "$VTK" ]; then
  VTK="$(ls -1 "$CASE_DIR/${INPUT}"_*.vtk 2>/dev/null | grep -v surface | sort -V | tail -1 || true)"
fi
if [ -z "$VTK" ]; then
  VTK="$(ls -1 "$CASE_DIR/${STEM}"_*.vtk 2>/dev/null | grep -v surface | sort -V | tail -1 || true)"
fi
if [ -z "$VTK" ]; then
  echo VTK_MISSING
  exit 6
fi
echo USING="$VTK"

render_host() {
  if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q vtk matplotlib numpy
  fi
  "$VENV/bin/python" "$RENDER" "$VTK" "$CASE_DIR"
}

if docker info >/dev/null 2>&1; then
  if ! docker run --rm \
    -v "$CASE_DIR":/work \
    -v "$RENDER":/render.py:ro \
    python:3.11-slim \
    bash -lc "pip install -q vtk matplotlib numpy && python /render.py /work/$(basename "$VTK") /work"; then
    echo "[warn] docker vtk render failed; trying host venv"
    render_host
  fi
else
  render_host
fi

PNG_COUNT="$(ls -1 "$CASE_DIR"/*.png 2>/dev/null | wc -l)"
echo "FEM_IMPACT_PNG_COUNT=$PNG_COUNT"
ls -1 "$CASE_DIR"/*.png 2>/dev/null | tail -5 || true
