import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from pathlib import Path

import unreal

OUT_DIR = Path(r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render")
OUT_DIR.mkdir(parents=True, exist_ok=True)

result = {
    "ok": True,
    "engine_version": str(unreal.SystemLibrary.get_engine_version()),
    "project_dir": str(unreal.Paths.project_dir()),
    "content_dir": str(unreal.Paths.project_content_dir()),
}

(OUT_DIR / "ue5_probe_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
