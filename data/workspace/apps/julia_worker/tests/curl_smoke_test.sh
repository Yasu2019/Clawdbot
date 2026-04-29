#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://localhost:8096/health
echo
curl -fsS http://localhost:8097/health
echo

curl -fsS -X POST http://localhost:8097/leveler/estimate \
  -H "Content-Type: application/json" \
  -d '{"thickness_mm":0.8,"yield_mpa":85,"roller_diameter_mm":12,"pitch_mm":16,"entry_gap_mm":0.7,"exit_gap_mm":1.1,"stages":11,"friction":0.05}'
echo
