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

names = {
    "AutomationLibrary": sorted([n for n in dir(unreal.AutomationLibrary) if "screenshot" in n.lower() or "render" in n.lower()]),
    "EditorLevelLibrary": sorted([n for n in dir(unreal.EditorLevelLibrary) if "level" in n.lower() or "actor" in n.lower()]),
    "SystemLibrary": sorted([n for n in dir(unreal.SystemLibrary) if "execute" in n.lower() or "console" in n.lower() or "quit" in n.lower()]),
}

(OUT_DIR / "ue5_api_probe_result.json").write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(names, ensure_ascii=False, indent=2))
