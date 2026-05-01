"""Build Motion Lab style motion table for the IATF design pilot.

This is a partial Motion Lab adoption: it consumes the approved Japanese
scene script and writes a CSV motion table plus explainable QA before any
Blender/video generation.
"""

from __future__ import annotations

import csv
import html
import json
import re
import shutil
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data/workspace/iatf_motion_table_status.json"
MOTION_LAB_TEMPLATE = ROOT / "data/workspace/apps/motion_lab/04_motion_table/templates/motion_table_template.csv"
MOTION_LAB_QA = ROOT / "data/workspace/apps/motion_lab/05_quality_check/animation_qc_checklist.md"

FIELDS = [
    "cut_id",
    "start_sec",
    "end_sec",
    "spoken_line",
    "body_action",
    "arm_action",
    "hand_action",
    "face_direction",
    "eye_direction",
    "emotion",
    "motion_source",
    "retarget_notes",
    "manual_fix_notes",
    "priority",
    "scene_id",
    "character",
    "evidence_on_screen",
    "visual_action",
]


def write_status(stage: str, **extra: object) -> None:
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "stage": stage,
        **extra,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def find_design_dir() -> Path:
    candidates = [
        path
        for path in (ROOT / "data/iatf_videos").iterdir()
        if path.is_dir() and path.name.endswith("_design_pilot")
    ]
    if not candidates:
        raise RuntimeError("No *_design_pilot directory found")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def estimate_duration(text: str) -> float:
    # Japanese narration with VOICEVOX is usually around 9-14 chars/sec.
    duration = max(3.0, min(8.0, len(text) / 11.0))
    return round(duration, 2)


def action_from_evidence(text: str, evidence: list[str], character: str) -> tuple[str, str, str, str, str]:
    joined = " ".join(evidence)
    if any(key in joined for key in ["作業カード", "QMI", "指示"]):
        return (
            "作業台に半歩近づき、文書を画面中央へ出す",
            "右腕を胸高さまで上げ、証拠文書を指す",
            "人差し指で該当欄をなぞる",
            "文書からカメラへ戻す",
            "文書の該当欄",
        )
    if any(key in joined for key in ["40個", "50個", "箱", "容器", "ラベル"]):
        return (
            "梱包箱の横に立ち、数量表示が見える位置で止まる",
            "片手で40個表示、もう片手で50個表示を順に指す",
            "手のひらを開いて比較を示す",
            "箱ラベルへ向ける",
            "40個/50個表示",
        )
    if any(key in joined for key in ["FIFO", "旧品", "不適合品"]):
        return (
            "保管棚の前で停止し、表示札が見える位置に立つ",
            "棚札と不適合品エリアを順番に指す",
            "指差し後にチェックリストへ戻す",
            "棚札へ向ける",
            "FIFOラベルと隔離表示",
        )
    if any(key in joined for key in ["是正", "再発", "記録", "責任者", "期限"]):
        return (
            "会議机で是正処置表を開く",
            "記録欄、責任者欄、期限欄を順に示す",
            "ペン先で記録欄を示す",
            "是正処置表へ向ける",
            "責任者・期限・有効性確認欄",
        )
    if character in {"bulma", "roshi"}:
        return (
            "正面で安定した説明姿勢を取る",
            "片手を胸高さへ上げて要点を示す",
            "手のひらを上向きにして説明する",
            "カメラへ向ける",
            "カメラ",
        )
    return (
        "現場証拠の横で静止し、聞き取り姿勢を取る",
        "チェックリストを持つ",
        "ペンを保持する",
        "相手から証拠へ移す",
        "監査対象の証拠",
    )


def row_priority(scene_id: str, evidence: list[str]) -> str:
    if scene_id in {"on_site_observation", "finding_risk"}:
        return "A"
    if any(item in " ".join(evidence) for item in ["40個", "50個", "QMI", "作業カード"]):
        return "A"
    return "B"


def build_rows(script: dict) -> list[dict]:
    rows: list[dict] = []
    current = 0.0
    cut_no = 1
    for scene in script.get("scenes", []):
        scene_id = scene.get("scene_id", "")
        for line in scene.get("lines", []):
            text = str(line.get("text", "")).strip()
            if not text:
                continue
            duration = estimate_duration(text)
            start = current
            end = round(current + duration, 2)
            evidence = [str(item) for item in line.get("evidence_on_screen", []) if str(item).strip()]
            character = str(line.get("character", "speaker"))
            body, arm, hand, face, eyes = action_from_evidence(text, evidence, character)
            visual_action = str(line.get("visual_action", ""))
            motion_source = "gesture_point" if evidence else "static_explain_pose"
            if re.search(r"半歩|近づき|棚|箱", body):
                motion_source = "mixamo_walk_short_or_static_pose"
            rows.append(
                {
                    "cut_id": f"CUT_{cut_no:03d}",
                    "start_sec": f"{start:.2f}",
                    "end_sec": f"{end:.2f}",
                    "spoken_line": text,
                    "body_action": body,
                    "arm_action": arm,
                    "hand_action": hand,
                    "face_direction": face,
                    "eye_direction": eyes,
                    "emotion": str(line.get("emotion", "explain")),
                    "motion_source": motion_source,
                    "retarget_notes": "rootを安定、足裏Z=0、証拠物が画面中央に入ること",
                    "manual_fix_notes": "手首・指差し・視線を証拠物へ合わせる",
                    "priority": row_priority(scene_id, evidence),
                    "scene_id": scene_id,
                    "character": character,
                    "evidence_on_screen": " / ".join(evidence),
                    "visual_action": visual_action,
                }
            )
            cut_no += 1
            current = round(end + 0.35, 2)
    return rows


def qa_motion_rows(rows: list[dict]) -> dict:
    failures: list[str] = []
    warnings: list[str] = []
    for row in rows:
        cut = row["cut_id"]
        if not row["spoken_line"]:
            failures.append(f"{cut}:blank_spoken_line")
        if not row["body_action"] or not row["arm_action"] or not row["eye_direction"]:
            failures.append(f"{cut}:missing_motion_fields")
        if row["priority"] == "A" and not row["evidence_on_screen"]:
            failures.append(f"{cut}:priority_A_without_evidence")
        if "自然" in row["body_action"] or "適当に" in row["body_action"]:
            failures.append(f"{cut}:ambiguous_motion_word")
        duration = float(row["end_sec"]) - float(row["start_sec"])
        if duration < 1.0 or duration > 8.5:
            warnings.append(f"{cut}:duration_outside_preferred_range:{duration:.2f}")
        if row["scene_id"] in {"on_site_observation", "finding_risk"} and "カメラ" == row["eye_direction"]:
            warnings.append(f"{cut}:audit_scene_eye_direction_should_include_evidence")
    evidence_terms = " / ".join(row["evidence_on_screen"] for row in rows)
    required = ["作業カード", "QMI", "40個", "50個", "FIFO"]
    for term in required:
        if term not in evidence_terms:
            failures.append(f"missing_required_evidence:{term}")
    return {
        "ok": not failures,
        "failures": failures,
        "warnings": warnings,
        "row_count": len(rows),
        "priority_A_count": sum(1 for row in rows if row["priority"] == "A"),
    }


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_html(rows: list[dict], qa: dict, out_path: Path) -> None:
    headers = ["cut_id", "scene_id", "character", "start_sec", "end_sec", "spoken_line", "body_action", "arm_action", "eye_direction", "evidence_on_screen", "priority"]
    html_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(row.get(h, '')))}</td>" for h in headers)
        html_rows.append(f"<tr class='p{row['priority']}'>{cells}</tr>")
    status = "OK" if qa["ok"] else "NG"
    out_path.write_text(
        f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>IATF Motion Table</title>
<style>
body{{font-family:system-ui,'Meiryo',sans-serif;margin:24px;background:#f8fafc;color:#102033}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:white}}
th,td{{border:1px solid #d7dee8;padding:6px;vertical-align:top}}
th{{position:sticky;top:0;background:#12324d;color:white}}
.pA td:first-child{{border-left:5px solid #dc2626}}
.pB td:first-child{{border-left:5px solid #2563eb}}
.summary{{padding:12px 16px;background:white;border:1px solid #d7dee8;margin-bottom:16px}}
code{{background:#eef2f7;padding:2px 4px}}
</style></head><body>
<h1>IATF Motion Table</h1>
<div class="summary"><b>Status:</b> {status} /
Rows: {qa['row_count']} / Priority A: {qa['priority_A_count']}<br>
<b>Failures:</b> <code>{html.escape(' / '.join(qa['failures']) or 'none')}</code><br>
<b>Warnings:</b> <code>{html.escape(' / '.join(qa['warnings']) or 'none')}</code></div>
<table><thead><tr>{''.join(f'<th>{h}</th>' for h in headers)}</tr></thead>
<tbody>{''.join(html_rows)}</tbody></table>
</body></html>""",
        encoding="utf-8",
    )


def main() -> int:
    design_dir = find_design_dir()
    script_path = design_dir / "deepseek_scene_script_jp_locked.json"
    if not script_path.exists():
        raise RuntimeError(f"Missing locked Japanese script: {script_path}")

    write_status("load_script", script=str(script_path))
    script = json.loads(script_path.read_text(encoding="utf-8"))
    rows = build_rows(script)
    qa = qa_motion_rows(rows)

    out_dir = design_dir / "motion_lab_partial"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "motion_table.csv"
    qa_path = out_dir / "motion_table_qa.json"
    html_path = out_dir / "motion_table_review.html"
    write_csv(rows, csv_path)
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    write_html(rows, qa, html_path)

    if MOTION_LAB_TEMPLATE.exists():
        shutil.copy2(MOTION_LAB_TEMPLATE, out_dir / "motion_table_template_reference.csv")
    if MOTION_LAB_QA.exists():
        shutil.copy2(MOTION_LAB_QA, out_dir / "animation_qc_checklist_reference.md")

    # ASCII mirror for easier opening from chat/IDE.
    mirror = ROOT / "data/workspace/iatf_motion_table"
    mirror.mkdir(parents=True, exist_ok=True)
    shutil.copy2(csv_path, mirror / "motion_table.csv")
    shutil.copy2(qa_path, mirror / "motion_table_qa.json")
    shutil.copy2(html_path, mirror / "motion_table_review.html")

    result = {
        "ok": qa["ok"],
        "design_dir": str(design_dir),
        "motion_table": str(csv_path),
        "qa": str(qa_path),
        "review_html": str(html_path),
        "mirror_review_html": str(mirror / "motion_table_review.html"),
        "row_count": qa["row_count"],
        "failures": qa["failures"],
        "warnings": qa["warnings"],
    }
    (out_dir / "motion_table_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_status("done", **result)
    if not qa["ok"]:
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_status("error", error=str(exc))
        raise
