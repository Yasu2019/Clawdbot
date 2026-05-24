#!/usr/bin/env bash
set -euo pipefail
python scripts/task_gate.py --task real_3d_video --config configs/acceptance_policy.yaml
python scripts/task_gate.py --task dxf_to_step --config configs/acceptance_policy.yaml
