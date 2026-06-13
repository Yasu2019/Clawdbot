# -*- coding: utf-8 -*-
"""FreeCAD 3D tolerance loop extract (Cetol L10 path — bbox/faces/holes loop closure)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _freecad_loop_script(step_path: str) -> str:
    safe = step_path.replace("\\", "/").replace("'", "\\'")
    return (
        "import json\n"
        "import Part\n"
        f"shape = Part.read('{safe}')\n"
        "bb = shape.BoundBox\n"
        "holes = []\n"
        "for i, f in enumerate(shape.Faces):\n"
        "    surf = f.Surface\n"
        "    if hasattr(surf, 'Radius'):\n"
        "        c = surf.Center\n"
        "        holes.append({'face_id': i, 'radius_mm': round(float(surf.Radius), 4),\n"
        "            'center_mm': [round(c.x, 4), round(c.y, 4), round(c.z, 4)]})\n"
        "faces = []\n"
        "for i, f in enumerate(shape.Faces[:32]):\n"
        "    faces.append({'face_id': i, 'area_mm2': round(float(f.Area), 4),\n"
        "        'surface': type(f.Surface).__name__})\n"
        "payload = {\n"
        "  'bbox_mm': {'Lx': round(bb.XLength, 4), 'Ly': round(bb.YLength, 4), 'Lz': round(bb.ZLength, 4)},\n"
        "  'face_count': len(shape.Faces),\n"
        "  'edge_count': len(shape.Edges),\n"
        "  'hole_count': len(holes),\n"
        "  'holes': holes[:24],\n"
        "  'faces_sample': faces,\n"
        "  'loop_closure': 'closed' if len(shape.Shells) >= 1 and shape.isClosed() else 'open',\n"
        "}\n"
        "print('FC_LOOP', json.dumps(payload, ensure_ascii=False))\n"
    )


def extract_freecad_3d_loop(step_path: Path, *, timeout_sec: int = 180) -> dict[str, Any]:
    """Run FreeCADCmd loop extract; return empty stub when FreeCAD unavailable."""
    if not step_path.exists():
        return {"ok": False, "reason": "step_missing", "parse_method": "none"}
    mode = os.environ.get("DXF2STEP_FREECAD_MODE", "docker").strip().lower()
    script_path = step_path.with_suffix(".fc_loop_extract.py")
    script_path.write_text(_freecad_loop_script(str(step_path)), encoding="utf-8")
    try:
        if mode in ("native", "linux"):
            fc_cmd = os.environ.get("FREECAD_CMD", "FreeCADCmd")
            cmd = [fc_cmd, str(script_path)]
            run_step = str(step_path)
        else:
            container = os.environ.get("FREECAD_DOCKER_CONTAINER", "clawstack-unified-clawdbot-gateway-1")
            c_step = f"/tmp/fc_loop_{step_path.name}"
            c_script = f"/tmp/fc_loop_{step_path.stem}.py"
            inner_script = _freecad_loop_script(c_step)
            script_path.write_text(inner_script, encoding="utf-8")
            subprocess.run(["docker", "cp", str(step_path), f"{container}:{c_step}"], check=False, timeout=60)
            subprocess.run(["docker", "cp", str(script_path), f"{container}:{c_script}"], check=False, timeout=60)
            cmd = ["docker", "exec", container, "bash", "-c", f"FreeCADCmd '{c_script}'"]
            run_step = c_step
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, encoding="utf-8", errors="replace")
        for line in (result.stdout or "").splitlines():
            if line.startswith("FC_LOOP "):
                payload = json.loads(line[8:])
                payload["ok"] = True
                payload["parse_method"] = "freecad_3d_loop_v1"
                payload["step_path"] = str(step_path)
                return payload
        return {
            "ok": False,
            "parse_method": "freecad_3d_loop_v1",
            "reason": (result.stderr or result.stdout or "no FC_LOOP output")[-300:],
            "step_path": str(step_path),
        }
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "parse_method": "freecad_3d_loop_v1", "reason": str(exc)[:200]}
    finally:
        try:
            script_path.unlink(missing_ok=True)
        except OSError:
            pass


def merge_loop_into_manifest(manifest: dict[str, Any], loop: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(manifest))
    if not loop.get("ok"):
        out["freecad_3d_loop"] = {"ok": False, "reason": loop.get("reason", "unknown")}
        return out
    fc = {
        "ok": True,
        "parse_method": loop.get("parse_method"),
        "loop_closure": loop.get("loop_closure"),
        "face_count": loop.get("face_count"),
        "hole_count": loop.get("hole_count"),
        "bbox_mm": loop.get("bbox_mm"),
    }
    out["freecad_3d_loop"] = fc
    features = out.setdefault("features", {})
    if loop.get("holes") and not features.get("holes"):
        for idx, h in enumerate(loop["holes"][:12]):
            r = float(h.get("radius_mm") or 0)
            if r <= 0:
                continue
            features.setdefault("holes", []).append(
                {
                    "name": f"fc_hole_{idx + 1}",
                    "diameter_mm": round(r * 2, 4),
                    "position_tol_mm": 0.05,
                    "source": "gdt_pmi_freecad_loop",
                }
            )
    tol = (out.get("physics_handoff") or {}).get("tolerance") or {}
    tol["freecad_loop_ready"] = True
    if loop.get("loop_closure") == "closed":
        tol["maturity_level"] = "L10_freecad_3d_loop"
    out.setdefault("physics_handoff", {})["tolerance"] = tol
    return out
