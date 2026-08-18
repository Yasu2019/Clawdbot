# -*- coding: utf-8 -*-
"""Turn harvested source records into validated, searchable knowledge notes.

Materials Project JSON is parsed directly.  Other sources may use the local
LLM, but hidden reasoning, mojibake and empty responses are rejected instead
of being recorded as successful growth.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from local_agent.llm_client import OllamaClient
from local_agent.obsidian import write_note
from local_agent.text_quality import replace_replacement_chars, validate_text

DB_PATH = ROOT / "data" / "workspace" / "universal_growth.db"
OBSIDIAN_VAULT = ROOT / "data" / "workspace" / "obsidian_vault"


def _db_retry(operation, context: str, attempts: int = 5, delay: float = 0.5):
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                raise
            last_exc = exc
            if attempt < attempts:
                time.sleep(delay * attempt)
                continue
    raise last_exc


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=60000")
    try:
        con.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    con.execute("""
        CREATE TABLE IF NOT EXISTS ai_summaries_tracking (
            external_id TEXT PRIMARY KEY,
            summarized_at TEXT
        )
    """)
    return con


def get_unprocessed_materials(limit: int = 12) -> list[sqlite3.Row]:
    def _query() -> list[sqlite3.Row]:
        with _connect() as con:
            return con.execute("""
                SELECT id, external_id, source, title, url, domain_tags,
                       metadata_json, local_path, sha256
                FROM public_api_acquisitions
                WHERE COALESCE(external_id, CAST(id AS TEXT)) NOT IN
                      (SELECT external_id FROM ai_summaries_tracking
                       WHERE external_id IS NOT NULL)
                ORDER BY
                  CASE WHEN local_path IS NOT NULL AND local_path != '' THEN 0 ELSE 1 END,
                  CASE WHEN domain_tags LIKE '%north_star%' THEN 0 ELSE 1 END,
                  acquired_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

    return _db_retry(_query, "get_unprocessed_materials")


def _safe_local_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(ROOT.resolve())
        return resolved
    except (OSError, ValueError):
        return None


def _number(value: Any, digits: int = 3) -> str:
    if value is None:
        return "未取得"
    try:
        return f"{float(value):.{digits}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def summarize_materials_project(path: Path) -> tuple[str, str]:
    raw = path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        raise ValueError("Materials Project JSONが空です")
    data = json.loads(raw)
    rows = data if isinstance(data, list) else [data]
    rows = [r for r in rows if isinstance(r, dict)]
    if not rows:
        raise ValueError("Materials Project JSONに材料レコードがありません")

    header = (
        "| Material ID | 組成 | 空間群 | 安定性(eV/atom) | 密度(g/cm³) | "
        "体積弾性率(GPa) | せん断弾性率(GPa) | Young率(GPa) | Poisson比 |\n"
        "|---|---:|---|---:|---:|---:|---:|---:|---:|"
    )
    lines = []
    valid_elastic = 0
    warnings: list[str] = []
    for r in rows:
        shear = r.get("shear_modulus_GPa")
        young = r.get("youngs_modulus_GPa")
        if isinstance(shear, (int, float)) and shear < 0:
            warnings.append(f"{r.get('material_id', 'unknown')}: 負のせん断弾性率のためCAE候補から除外")
        elif young is not None:
            valid_elastic += 1
        lines.append(
            "| {material_id} | {formula} | {space_group} | {hull} | {density} | {bulk} | {shear} | {young} | {poisson} |".format(
                material_id=r.get("material_id", "未取得"), formula=r.get("formula", "未取得"),
                space_group=r.get("space_group", "未取得"), hull=_number(r.get("energy_above_hull"), 4),
                density=_number(r.get("density_g_cm3")), bulk=_number(r.get("bulk_modulus_GPa")),
                shear=_number(shear), young=_number(young), poisson=_number(r.get("poissons_ratio"), 4),
            )
        )
    formulas = sorted({str(r.get("formula")) for r in rows if r.get("formula")})
    stable = sum(1 for r in rows if isinstance(r.get("energy_above_hull"), (int, float)) and r["energy_above_hull"] <= 0.05)
    warning_text = "\n".join(f"- {w}" for w in warnings) or "- 自動検出された異常値はありません。"
    summary = f"""## 概要

- レコード数: {len(rows)}
- 組成: {', '.join(formulas) or '未取得'}
- 安定候補（energy above hull ≤ 0.05 eV/atom）: {stable}
- 弾性物性を利用可能な候補: {valid_elastic}
- 根拠ファイル: `{path.relative_to(ROOT).as_posix()}`

## 抽出物性

{header}
{chr(10).join(lines)}

## 品質上の注意

{warning_text}

## CAEでの利用判断

Materials Project値は計算由来を含むため、そのまま製造条件へ採用せず、安定相・温度・材料規格・実測値との整合を確認してから材料カード候補として使用します。
"""
    know_how = f"{len(rows)}候補中、安定候補{stable}件、弾性物性利用可能{valid_elastic}件。異常値を除外し、実測値照合後にCAE材料カードへ採用する。"
    return summary, know_how


def _clean_llm_response(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    text = re.sub(r"```(?:markdown)?\s*", "", text, flags=re.IGNORECASE).replace("```", "").strip()
    return validate_text(text, label="LLM response")


def summarize_metadata_deterministic(row: sqlite3.Row) -> tuple[str, str]:
    """Create an evidence-only note without generative text or hallucination."""
    try:
        metadata = json.loads(row["metadata_json"] or "{}")
    except (TypeError, json.JSONDecodeError):
        metadata = {"raw_metadata": str(row["metadata_json"] or "")[:4000]}
    source_text = json.dumps(metadata, ensure_ascii=False, default=str)
    had_encoding_loss = "\ufffd" in source_text or "\ufffd" in str(row["title"] or "")
    metadata = replace_replacement_chars(metadata)
    local_path = _safe_local_path(row["local_path"])
    domain_tags = replace_replacement_chars(str(row["domain_tags"] or "未分類"))
    metadata_text = json.dumps(metadata, ensure_ascii=False, indent=2, default=str)[:12000]
    encoding_note = (
        "\n- 取得メタデータに Unicode 置換文字(U+FFFD)があったため `[encoding-loss]` に置換しています。"
        if had_encoding_loss
        else ""
    )
    body = f"""## 概要

- 取得元: {row['source']}
- 分類: {domain_tags}
- ローカルファイル: `{local_path.relative_to(ROOT).as_posix() if local_path else '未取得または範囲外'}`
- このノートは生成AIを使わず、取得メタデータから決定論的に作成しています。{encoding_note}

## 確認できた事実

```json
{metadata_text}
```

## 利用上の注意

メタデータだけでは技術内容の妥当性を確定できません。原文またはローカルファイルを確認してから設計・CAEへ利用してください。
"""
    validate_text(body, label="deterministic summary")
    know_how = f"{row['source']}から取得した資料。原文確認前はメタデータ候補として扱う。"
    return body, know_how


def summarize_with_llm(row: sqlite3.Row, client: OllamaClient) -> tuple[str, str]:
    metadata = str(row["metadata_json"] or "{}")[:12000]
    prompt = f"""次の取得済み資料について、メタデータから確認できる事実だけを日本語で要約してください。
推測を事実として書かず、不明な値は「未確認」としてください。

タイトル: {row['title'] or '無題'}
取得元: {row['source']}
URL: {row['url'] or '未登録'}
メタデータ: {metadata}

次の見出しを必ず使用してください。
## 概要
## 確認できた事実
## CAE・設計への利用可能性
## 未確認事項
"""
    response = client.generate(
        prompt=prompt,
        system="あなたは工学資料の整理担当です。内部思考は出力せず、根拠のある簡潔な日本語だけを返してください。",
        temperature=0.1,
    )
    if response.startswith("[LLM_ERROR]"):
        raise RuntimeError(response[:500])
    cleaned = _clean_llm_response(response)
    return cleaned, re.sub(r"[#*`\n]+", " ", cleaned).strip()[:300]


def commit_success(row: sqlite3.Row, know_how: str) -> None:
    record_id = str(row["external_id"] or row["id"])
    primary_domain = str(row["domain_tags"] or "research").split(",")[0].strip().upper()

    def _commit() -> None:
        with _connect() as con:
            con.execute("""
                INSERT INTO growth_records
                  (domain, challenge, status, know_how, source, evidence, timestamp)
                VALUES (?, ?, 'SUCCESS', ?, 'harvested_material_processor', ?, ?)
            """, (
                primary_domain, f"Reviewed: {str(row['title'] or 'No Title')[:80]}",
                know_how[:1000], row["url"] or row["local_path"] or "", datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            con.execute(
                "INSERT OR REPLACE INTO ai_summaries_tracking (external_id, summarized_at) VALUES (?, ?)",
                (record_id, datetime.now().isoformat(timespec="seconds")),
            )

    _db_retry(_commit, f"commit_success:{record_id}")


def mark_permanent_reject(row: sqlite3.Row, reason: str) -> None:
    """Keep unusable source records out of the retry queue without recording SUCCESS."""
    record_id = str(row["external_id"] or row["id"])

    def _commit() -> None:
        with _connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO ai_summaries_tracking (external_id, summarized_at) VALUES (?, ?)",
                (record_id, datetime.now().isoformat(timespec="seconds")),
            )

    _db_retry(_commit, f"mark_permanent_reject:{record_id}:{reason[:80]}")


def is_permanent_source_failure(exc: BaseException) -> bool:
    if isinstance(exc, json.JSONDecodeError):
        return True
    if isinstance(exc, ValueError) and "Materials Project JSON" in str(exc):
        return True
    return False


def main() -> int:
    print("Starting Harvested Materials Processing Agent (validated v2)...")
    client = OllamaClient()
    rows = get_unprocessed_materials(limit=max(1, int(os.environ.get("HARVEST_AGENT_BATCH_SIZE", "12"))))
    if not rows:
        print("No unprocessed materials found.")
        return 0

    succeeded = 0
    failed = 0
    for row in rows:
        title = replace_replacement_chars(row["title"] or "No Title")
        print(f"\nProcessing: [{row['source']}] {title}")
        try:
            local_path = _safe_local_path(row["local_path"])
            if row["source"] == "materials_project" and local_path and local_path.suffix.lower() == ".json":
                response, know_how = summarize_materials_project(local_path)
                method = "deterministic_json_parser"
            elif os.environ.get("HARVEST_USE_LLM", "0") == "1":
                response, know_how = summarize_with_llm(row, client)
                method = "validated_local_llm"
            else:
                response, know_how = summarize_metadata_deterministic(row)
                method = "deterministic_metadata_parser"
            body = (
                f"# {title}\n\n**Source**: {row['source']}  \n**URL**: {row['url'] or '未登録'}  \n"
                f"**Extraction method**: `{method}`  \n**Source SHA256**: `{row['sha256'] or '未登録'}`\n\n{response}\n"
            )
            note_path = write_note(str(OBSIDIAN_VAULT), "API_Summaries", title, body)
            commit_success(row, know_how)
            succeeded += 1
            print(f" -> Validated and saved to Obsidian: {note_path}")
        except Exception as exc:
            failed += 1
            if is_permanent_source_failure(exc):
                mark_permanent_reject(row, f"{type(exc).__name__}: {exc}")
                print(f" -> REJECTED_PERMANENT (will not retry): {type(exc).__name__}: {exc}")
            else:
                print(f" -> REJECTED (not marked summarized): {type(exc).__name__}: {exc}")

    if succeeded:
        from inject_growth_data import export_stats_json
        export_stats_json()
    print(f"\nProcessing complete: success={succeeded}, rejected={failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
