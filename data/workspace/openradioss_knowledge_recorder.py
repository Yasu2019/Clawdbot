from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


ROOT = Path(__file__).resolve().parents[2]
KNOW_DIR = ROOT / "data" / "workspace" / "knowledge" / "openradioss"
LESSONS_PATH = KNOW_DIR / "lessons.md"
FMEA_PATH = KNOW_DIR / "fmea_log.md"
QC_PATH = KNOW_DIR / "qc_process_chart.md"
BRV_DIR = ROOT / ".brv" / "context-tree" / "infrastructure" / "openradioss"


def _append_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)


def _json_block(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        return json.dumps({"repr": repr(obj)}, ensure_ascii=False, indent=2)


def _replace_block(existing: str, start: str, end: str, body: str) -> str:
    if start in existing and end in existing:
        pre = existing.split(start, 1)[0] + start
        post = existing.split(end, 1)[1]
        return pre + "\n" + body.rstrip() + "\n" + end + post
    return existing.rstrip() + "\n\n" + start + "\n" + body.rstrip() + "\n" + end + "\n"


def _brv_run_path(analysis_type: str, run_number: int) -> Path:
    BRV_DIR.mkdir(parents=True, exist_ok=True)
    return BRV_DIR / f"{analysis_type}_run{run_number}.md"


def _ensure_brv_run_doc(analysis_type: str, run_number: int) -> str:
    path = _brv_run_path(analysis_type, run_number)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    created_at = datetime.now().isoformat()
    return f"""---
title: OpenRadioss — {analysis_type} Run{run_number}
tags: [openradioss, cae, doe, qc, fmea]
created_at: {created_at}
analysis_type: {analysis_type}
run_number: {run_number}
---

# OpenRadioss run summary (integrated)

<!--QC_START-->
TBD
<!--QC_END-->

<!--FMEA_START-->
TBD
<!--FMEA_END-->

<!--LESSONS_START-->
TBD
<!--LESSONS_END-->
"""


def _update_brv_run_summary(
    analysis_type: str,
    run_number: int,
    qc_md: str | None = None,
    fmea_md: str | None = None,
    lessons_md: str | None = None,
    status: str | None = None,
) -> Path:
    path = _brv_run_path(analysis_type, run_number)
    doc = _ensure_brv_run_doc(analysis_type, run_number)

    if status:
        stamp = datetime.now().isoformat(timespec="seconds")
        status_line = f"\n\nLast status: {status} (updated_at={stamp})\n"
        if "Last status:" in doc:
            parts = doc.split("Last status:", 1)
            tail = parts[1].split("\n", 1)[1] if "\n" in parts[1] else ""
            doc = parts[0] + "Last status: " + status + f" (updated_at={stamp})\n" + tail
        else:
            doc = doc.rstrip() + status_line

    if qc_md is not None:
        doc = _replace_block(doc, "<!--QC_START-->", "<!--QC_END-->", qc_md)
    if fmea_md is not None:
        doc = _replace_block(doc, "<!--FMEA_START-->", "<!--FMEA_END-->", fmea_md)
    if lessons_md is not None:
        doc = _replace_block(doc, "<!--LESSONS_START-->", "<!--LESSONS_END-->", lessons_md)

    path.write_text(doc, encoding="utf-8")
    return path


def record_qc_process_chart(
    analysis_type: str,
    run_number: int,
    parameters: dict[str, Any],
    solver_meta: dict[str, Any] | None = None,
    record_to_brv: bool = True,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    solver_meta = solver_meta or {}
    content = f"""
## QC工程表 — {analysis_type} Run{run_number} ({ts})

| # | 工程 | 管理特性 | 管理方法 | 判定基準 | パラメータ |
|---|---|---|---|---|---|
| 1 | DOE点読み込み | 設計点妥当性 | required keys | VC/Eps_eff/Inacti/TSTOP | {parameters} |
| 2 | deckパッチ | パラメータ注入 | 置換/検証 | verify一致 | starter_patch=on |
| 3 | starter実行 | 入力整合 | starter log | error=0 | threads={solver_meta.get('threads','?')} |
| 4 | engine実行 | 進捗 | NC/T監視 | termination検知 | timeout_s={solver_meta.get('timeout_s','?')} |
| 5 | 結果パース | 指標抽出 | log grep/regex | t_final取得 | term={solver_meta.get('termination_type','?')} |
| 6 | 記録 | 監査性 | md常時追記 | 追記成功 | lessons/fmea/qc |

"""
    _append_md(QC_PATH, content)

    if record_to_brv:
        try:
            qc_md = (
                f"Generated at: {ts}\n\n"
                f"Parameters:\n```json\n{_json_block(parameters)}\n```\n\n"
                f"Solver meta:\n```json\n{_json_block(solver_meta)}\n```\n"
            )
            _update_brv_run_summary(
                analysis_type=analysis_type,
                run_number=run_number,
                qc_md=qc_md,
                status="qc_recorded",
            )
        except Exception as exc:
            print(f"[OpenRadiossKnowledge] ByteRover QC write failed: {exc}", flush=True)


def record_lesson(
    analysis_type: str,
    run_number: int,
    status: str,
    parameters: dict[str, Any],
    results: dict[str, Any] | None = None,
    lesson: str = "",
    record_to_brv: bool = True,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    results = results or {}
    tag = "PASS" if status == "success" else "FAIL"
    content = f"""
### {ts} — {analysis_type} Run{run_number} [{tag}]

**status**: {status}

**再現パラメータ**:
- {parameters}

**主要結果**:
- {results}

**教訓**: {lesson or "TBD"}

"""
    _append_md(LESSONS_PATH, content)

    # ByteRover integrated run summary for success/failed.
    # Also keep the legacy "success-only timestamped file" for quick browsing.
    if record_to_brv:
        try:
            lessons_md = (
                f"Status: {status}\n\n"
                f"Parameters:\n```json\n{_json_block(parameters)}\n```\n\n"
                f"Results:\n```json\n{_json_block(results or {})}\n```\n\n"
                f"Lessons:\n{lesson or 'TBD'}\n"
            )
            _update_brv_run_summary(
                analysis_type=analysis_type,
                run_number=run_number,
                lessons_md=lessons_md,
                status=status,
            )

            if status == "success":
                _record_to_brv_success_snapshot(
                    analysis_type=analysis_type,
                    run_number=run_number,
                    status=status,
                    parameters=parameters,
                    results=results,
                    lesson=lesson,
                )
        except Exception as exc:
            print(f"[OpenRadiossKnowledge] ByteRover write failed: {exc}", flush=True)


def record_fmea(
    analysis_type: str,
    run_number: int,
    status: str,
    failure_mode: str | None,
    recommended_action: str = "",
    record_to_brv: bool = True,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    sev = 8 if status != "success" else 2
    occ = 4 if status != "success" else 1
    det = 4
    rpn = sev * occ * det
    content = f"""
## FMEA — {analysis_type} Run{run_number} ({ts})

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---:|---:|---:|---:|---|
| engine | {failure_mode or "-"} | 解析停止/精度低下 | deck/接触/境界/刻み | {sev} | {occ} | {det} | **{rpn}** | {recommended_action or "TBD"} |

"""
    _append_md(FMEA_PATH, content)

    if record_to_brv:
        try:
            fmea_md = (
                f"Generated at: {ts}\n\n"
                f"Status: {status}\n\n"
                f"Failure mode: {failure_mode or '-'}\n\n"
                f"RPN: {rpn} (S={sev}, O={occ}, D={det})\n\n"
                f"Recommended action:\n{recommended_action or 'TBD'}\n"
            )
            _update_brv_run_summary(
                analysis_type=analysis_type,
                run_number=run_number,
                fmea_md=fmea_md,
                status=status,
            )
        except Exception as exc:
            print(f"[OpenRadiossKnowledge] ByteRover FMEA write failed: {exc}", flush=True)


def _record_to_brv_success_snapshot(
    analysis_type: str,
    run_number: int,
    status: str,
    parameters: dict[str, Any],
    results: dict[str, Any] | None,
    lesson: str,
) -> Path:
    BRV_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = BRV_DIR / f"{analysis_type}_run{run_number}_{ts}.md"
    results = results or {}
    content = f"""---
title: OpenRadioss — {analysis_type} Run{run_number}
tags: [openradioss, doe, cae, mfg-sim]
created_at: {datetime.now().isoformat()}
status: {status}
---

# OpenRadioss run summary

## Run
- analysis_type: {analysis_type}
- run_number: {run_number}
- status: {status}

## Parameters
```json
{_json_block(parameters)}
```

## Results
```json
{_json_block(results)}
```

## Lessons
{lesson or "TBD"}
"""
    path.write_text(content, encoding="utf-8")
    print(f"[OpenRadiossKnowledge] ByteRover recorded: {path.name}", flush=True)
    return path

