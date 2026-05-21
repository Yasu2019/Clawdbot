import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
from pathlib import Path
import unreal
out=Path(r"D:\\Clawdbot_Docker_20260125\\projects\\AtsugiMechaCity\\diagnostics\\ue5_local_render")
items={}
for name in ["take_high_res_screenshot","take_automation_screenshot_at_camera","take_automation_screenshot"]:
    fn=getattr(unreal.AutomationLibrary,name)
    items[name]=getattr(fn,"__doc__","")
(out/"ue5_api_docs_result.json").write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(items,ensure_ascii=False,indent=2))
