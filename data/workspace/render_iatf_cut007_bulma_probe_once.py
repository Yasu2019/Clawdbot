"""Render CUT_007 Bulma diagnostic frames with gentler coordinated arm motion.

Low-API PDCA rule:
- OpenCodeGo is attempted externally, but rendering/debugging stays local.
- One cut only.
- Output is diagnostic frames/contact sheet first.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SOURCE = ROOT / "data/workspace/render_iatf_cut005_bulma_probe_once.py"
STATUS = ROOT / "data/workspace/iatf_video_pdca_status.json"
CONFIG = ROOT / "data/state/openclaw.json"


def write_status(**payload: object) -> None:
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def send_telegram(text: str) -> str:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        token = cfg["channels"]["telegram"]["botToken"]
        chat_ids = [str(x) for x in cfg["channels"]["telegram"]["allowFrom"]]
        chat_id = "8173025084" if "8173025084" in chat_ids else chat_ids[0]
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as res:
            return f"sent:{res.status}"
    except Exception as exc:
        return f"failed:{exc}"


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    old_arm_block = """for frame, shoulder_z, arm_z, fore_z, hand_z in [
    (1, -18, -34, 24, 4),
    (12, -10, -20, 16, 1),
    (30, -5, -8, 10, -4),
    (60, -8, -12, 12, -2),
]:
    set_bone(bulma_arm, "mixamorig:RightShoulder", frame, rot=(0, 0, math.radians(shoulder_z)))
    set_bone(bulma_arm, "mixamorig:RightArm", frame, rot=(math.radians(2), 0, math.radians(arm_z)))
    set_bone(bulma_arm, "mixamorig:RightForeArm", frame, rot=(0, 0, math.radians(fore_z)))
    set_bone(bulma_arm, "mixamorig:RightHand", frame, rot=(0, math.radians(-8), math.radians(hand_z)))
    set_bone(bulma_arm, "mixamorig:RightHandIndex1", frame, rot=(0, 0, math.radians(-4)))
    set_bone(bulma_arm, "mixamorig:RightHandIndex2", frame, rot=(0, 0, math.radians(0)))
"""
    new_arm_block = """for frame, shoulder_z, arm_z, fore_z, hand_y, hand_z in [
    (1, -8, -16, 10, -4, 1),
    (12, -7, -13, 9, -4, 0),
    (30, -5, -10, 7, -3, -1),
    (60, -6, -11, 8, -3, 0),
]:
    set_bone(bulma_arm, "mixamorig:RightShoulder", frame, rot=(math.radians(1), 0, math.radians(shoulder_z)))
    set_bone(bulma_arm, "mixamorig:RightArm", frame, rot=(math.radians(1), 0, math.radians(arm_z)))
    set_bone(bulma_arm, "mixamorig:RightForeArm", frame, rot=(0, math.radians(1), math.radians(fore_z)))
    set_bone(bulma_arm, "mixamorig:RightHand", frame, rot=(0, math.radians(hand_y), math.radians(hand_z)))
    set_bone(bulma_arm, "mixamorig:RightHandIndex1", frame, rot=(0, 0, math.radians(-2)))
    set_bone(bulma_arm, "mixamorig:RightHandIndex2", frame, rot=(0, 0, math.radians(0)))
"""
    replacements = {
        'ROOT = Path(__file__).resolve().parents[2]': f'ROOT = Path(r"{str(ROOT)}")',
        "CUT_005": "CUT_007",
        "cut005_bulma_probe": "cut007_bulma_probe",
        "iatf_cut005_bulma_probe": "iatf_cut007_bulma_probe",
        "cut005_bulma_": "cut007_bulma_",
        "verify packaging evidence": "gentle coordinated arm motion review",
        old_arm_block: new_arm_block,
        '"arm pose may require manual tuning after visual review"': '"CUT007 reduces shoulder/elbow/wrist rotation amplitude; verify evidence is still unobstructed"',
    }
    for src, dst in replacements.items():
        if src not in text and src == old_arm_block:
            raise RuntimeError("arm block not found")
        text = text.replace(src, dst)

    write_status(
        phase="started",
        cut_id="CUT_007",
        opencode_go="attempted via LiteLLM; unavailable/500, local PDCA continued",
        rule="one cut, diagnostic frames first",
    )
    telegram = send_telegram("IATF CUT007のPDCA診断フレーム生成を開始しました。")

    with tempfile.TemporaryDirectory(prefix="iatf_cut007_bulma_") as tmp:
        script = Path(tmp) / "render_cut007.py"
        script.write_text(text, encoding="utf-8")
        result = subprocess.run(
            ["python", str(script)],
            cwd=str(ROOT),
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )

    out_dir = ROOT / "data/workspace/iatf_cut007_bulma_probe"
    ok = result.returncode == 0 and (out_dir / "contact_sheet.jpg").exists()
    final_msg = (
        "IATF CUT007診断フレーム生成OKです。"
        if ok
        else "IATF CUT007診断フレーム生成NGのため、次PDCAが必要です。"
    )
    telegram_final = send_telegram(final_msg)
    write_status(
        phase="done" if ok else "failed",
        ok=ok,
        cut_id="CUT_007",
        returncode=result.returncode,
        opencode_go="attempted via LiteLLM; unavailable/500, local PDCA continued",
        telegram_start=telegram,
        telegram_final=telegram_final,
        output_dir=str(out_dir),
        contact_sheet=str(out_dir / "contact_sheet.jpg"),
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
