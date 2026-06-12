# -*- coding: utf-8 -*-
"""動画生成前 品質事前分析 (QC工程表・FMEA・FTA・なぜなぜ・Fishbone・ロジカルツリー)

PDF抽出後・台本生成前に必須。LLM失敗・JSON不完全時は fail-closed。
過去トラ (trouble_history.md / iatf_generation_lessons.json) をプロンプトへ注入。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[4]
TROUBLE_HISTORY = ROOT / "data" / "workspace" / "memory" / "trouble_history.md"
LESSONS_DB = ROOT / "data" / "workspace" / "iatf_generation_lessons.json"
QUALITY_KNOWLEDGE = ROOT / "data" / "workspace" / "quality_manufacturing_knowledge_inject.md"

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4001")
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "yasu-fresh-token-2026-02-01")

REQUIRED_SECTIONS = (
    "qc_process_chart",
    "production_design",
    "fmea",
    "fta_top_event",
    "fta_root_causes",
    "why_why",
    "fishbone",
    "logical_tree",
    "key_risks",
    "recommended_emphasis",
)

MIN_QC_STEPS = 2
MIN_FMEA_ROWS = 2
MIN_WHY_ROWS = 1
MIN_LOGICAL_NODES = 2
MIN_KEY_RISKS = 1

ANALYSIS_PROMPT = """\
あなたはIATF 16949の品質エンジニアです。
動画教材を生成する前に、以下の8分析 + リスク要約を実施してください。
制作レイアウト(出演者・背景・照明・カメラ)と静止画/動画の崩壊リスクを必ず含めること。

【対象】箇条: {clause} / トピック: {topic}

【PDFテキスト（先頭2500文字）】
{pdf_excerpt}

【過去トラ・教訓（必ず反映し、同種の故障を再発させない対策をFMEA/台本強調に含める）】
{past_trouble_excerpt}

以下のJSONのみ返してください（キー名は変更不可）:

{{
  "qc_process_chart": [
    {{"step": "PD01_cast_placement|工程名", "control_point": "管理ポイント", "standard": "判定基準", "risk": "リスク"}}
  ],
  "production_design": {{
    "cast_plan": [{{"character": "bulma", "role": "司会", "screen_position": "center"}}],
    "background_plan": {{"label": "箇条ラベル", "props": ["desk","clipboard"], "bg_description": "工場監査室"}},
    "lighting_plan": {{"key_light": "...", "fill": "...", "emission_check": "全マテリアルopaque+Emission"}},
    "camera_plan": {{"shot_type": "medium_wide", "movement": "slow_dolly_in", "forbidden": ["face_closeup_only"]}},
    "visual_integrity_checks": ["静止画サンプルVisual QA", "interim frame100 QA", "final visual_qa"]
  }},
  "production_fmea": [
    {{"category": "CAST_ASSET|LIGHTING|CAMERA|STILL_CORRUPTION|VIDEO_CORRUPTION",
      "failure_mode": "...", "effect": "...", "cause": "...",
      "severity": 1, "occurrence": 1, "detection": 1, "countermeasure": "..."}}
  ],
  "fmea": [
    {{"process": "工程", "failure_mode": "故障モード", "effect": "影響", "cause": "原因",
      "severity": 1, "occurrence": 1, "detection": 1, "countermeasure": "対策"}}
  ],
  "fta_top_event": "最悪シナリオ（1文）",
  "fta_root_causes": ["根本原因1", "根本原因2"],
  "why_why": [
    {{"why1": "...", "why2": "...", "why3": "...", "why4": "...", "why5": "真因", "action": "対策"}}
  ],
  "fishbone": {{
    "problem": "問題定義",
    "man": ["人的要因"],
    "machine": ["設備要因"],
    "method": ["方法要因"],
    "material": ["材料要因"],
    "environment": ["環境要因"]
  }},
  "logical_tree": {{
    "top_event": "頂上事象（動画品質または教育効果の最悪事象）",
    "nodes": [
      {{"id": "N1", "text": "中間原因", "parent": "TOP", "gate": "OR"}},
      {{"id": "N2", "text": "基本事象", "parent": "N1", "gate": "AND"}}
    ]
  }},
  "key_risks": ["動画制作上の最重要リスク"],
  "recommended_emphasis": ["台本で特に強調すべきポイント"]
}}
"""


GOLDEN_MINIMAL_PROMPT = """\
IATF 16949 内部監査の短尺ゴールデン動画（箇条 {clause} / {topic}）向けに、
以下の7分析を簡潔に実施しJSONのみ返してください。過去トラを反映すること。

【参照テキスト】
{pdf_excerpt}

【過去トラ・教訓】
{past_trouble_excerpt}

キー: qc_process_chart, fmea, fta_top_event, fta_root_causes, why_why, fishbone,
logical_tree (top_event + nodes 2件以上), key_risks, recommended_emphasis
"""


class QualityPreflightError(RuntimeError):
    """品質事前分析ゲート不合格。"""


def is_preflight_required() -> bool:
    return os.getenv("IATF_VIDEO_QUALITY_PREFLIGHT_REQUIRED", "1").strip() != "0"


def load_past_trouble_excerpt(max_chars: int = 3500) -> str:
    parts: list[str] = []
    if TROUBLE_HISTORY.exists():
        text = TROUBLE_HISTORY.read_text(encoding="utf-8", errors="replace")
        parts.append("=== trouble_history.md (末尾優先) ===\n" + text[-max_chars:])
    if LESSONS_DB.exists():
        try:
            data = json.loads(LESSONS_DB.read_text(encoding="utf-8"))
            lessons = data.get("lessons_learned", [])[-8:]
            fmea = data.get("fmea_log", [])[-5:]
            if lessons:
                parts.append("=== lessons_learned (直近) ===")
                for row in lessons:
                    parts.append(f"- [{row.get('ts', '?')}] {row.get('reason', '')[:400]}")
            if fmea:
                parts.append("=== fmea_log (直近) ===")
                for row in fmea:
                    parts.append(
                        f"- [{row.get('ts', '?')}] {row.get('video_title', '')}: "
                        f"{row.get('description', '')[:300]}"
                    )
        except Exception as exc:
            parts.append(f"(lessons load error: {exc})")
    if QUALITY_KNOWLEDGE.exists():
        qk = QUALITY_KNOWLEDGE.read_text(encoding="utf-8", errors="replace")
        parts.append("=== quality_manufacturing_knowledge_inject (API harvest) ===\n" + qk[:2000])
    if not parts:
        return "(過去トラファイル未検出 -- 一般的なIATF動画制作リスクを想定すること)"
    blob = "\n".join(parts)
    return blob[:max_chars]


def validate_preflight_result(result: dict, *, minimal: bool = False) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not result or result.get("_skipped"):
        errors.append("empty_or_skipped_result")
        return False, errors

    skip_keys = {"production_design"} if minimal else set()
    for key in REQUIRED_SECTIONS:
        if key in skip_keys:
            continue
        if key not in result:
            errors.append(f"missing_section:{key}")

    qc = result.get("qc_process_chart") or []
    if not isinstance(qc, list) or len(qc) < MIN_QC_STEPS:
        errors.append(f"qc_process_chart_too_short:{len(qc) if isinstance(qc, list) else 0}")

    fmea = result.get("fmea") or []
    if not isinstance(fmea, list) or len(fmea) < MIN_FMEA_ROWS:
        errors.append(f"fmea_too_short:{len(fmea) if isinstance(fmea, list) else 0}")

    if not str(result.get("fta_top_event", "")).strip():
        errors.append("fta_top_event_empty")
    roots = result.get("fta_root_causes") or []
    if not isinstance(roots, list) or len(roots) < 1:
        errors.append("fta_root_causes_empty")

    why = result.get("why_why") or []
    if not isinstance(why, list) or len(why) < MIN_WHY_ROWS:
        errors.append(f"why_why_too_short:{len(why) if isinstance(why, list) else 0}")

    fish = result.get("fishbone") or {}
    if not isinstance(fish, dict) or not str(fish.get("problem", "")).strip():
        errors.append("fishbone_invalid")

    lt = result.get("logical_tree") or {}
    nodes = lt.get("nodes") if isinstance(lt, dict) else None
    if not isinstance(lt, dict) or not str(lt.get("top_event", "")).strip():
        errors.append("logical_tree_top_empty")
    elif not isinstance(nodes, list) or len(nodes) < MIN_LOGICAL_NODES:
        errors.append(f"logical_tree_nodes_too_short:{len(nodes) if isinstance(nodes, list) else 0}")

    risks = result.get("key_risks") or []
    if not isinstance(risks, list) or len(risks) < MIN_KEY_RISKS:
        errors.append(f"key_risks_too_short:{len(risks) if isinstance(risks, list) else 0}")

    emphasis = result.get("recommended_emphasis") or []
    if not isinstance(emphasis, list) or len(emphasis) < MIN_KEY_RISKS:
        errors.append(f"recommended_emphasis_too_short:{len(emphasis) if isinstance(emphasis, list) else 0}")

    if not minimal:
        pd = result.get("production_design") or {}
        if not isinstance(pd, dict):
            errors.append("production_design_invalid")
        else:
            for key in ("cast_plan", "background_plan", "lighting_plan", "camera_plan"):
                if key not in pd or not pd.get(key):
                    errors.append(f"production_design_missing:{key}")
            vic = pd.get("visual_integrity_checks") or []
            if not isinstance(vic, list) or len(vic) < 2:
                errors.append("production_design_visual_checks_too_short")

        qc_steps = result.get("qc_process_chart") or []
        pd_step_ids = ("PD01", "PD02", "PD03", "PD04", "PD05", "出演", "背景", "照明", "カメラ")
        has_production_step = any(
            isinstance(row, dict)
            and any(tok in str(row.get("step", "")) for tok in pd_step_ids)
            for row in qc_steps
        )
        if not has_production_step:
            errors.append("qc_process_chart_missing_production_layout_steps")

    return len(errors) == 0, errors


def load_valid_preflight(save_path: Path) -> dict | None:
    if not save_path.exists():
        return None
    try:
        data = json.loads(save_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    ok, _ = validate_preflight_result(data, minimal=bool(data.get("_minimal")))
    return data if ok else None


def assert_quality_preflight(
    pdf_text: str,
    clause: str,
    topic: str,
    save_path: Path,
    *,
    minimal: bool = False,
) -> dict:
    """Run analysis and raise QualityPreflightError if gate fails."""
    if not is_preflight_required():
        stub = {"_skipped": True, "_reason": "IATF_VIDEO_QUALITY_PREFLIGHT_REQUIRED=0"}
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(stub, ensure_ascii=False, indent=2), encoding="utf-8")
        return stub

    existing = load_valid_preflight(save_path)
    if existing:
        print(f"  [QualityPreflight] 既存OK: {save_path.name}", flush=True)
        return existing

    excerpt = (pdf_text or "").strip()
    if len(excerpt) < 20 and not minimal:
        raise QualityPreflightError(
            f"PDF text too short for quality preflight ({len(excerpt)} chars). "
            "Use a text-bearing PDF or set IATF_VIDEO_QUALITY_PREFLIGHT_REQUIRED=0 for debug only."
        )

    result = run_quality_preflight(
        excerpt or topic,
        clause,
        topic,
        save_path=save_path,
        minimal=minimal,
        raise_on_fail=True,
    )
    return result


def run_quality_preflight(
    pdf_text: str,
    clause: str,
    topic: str,
    save_path: Path | None = None,
    *,
    minimal: bool = False,
    raise_on_fail: bool = False,
) -> dict:
    past = load_past_trouble_excerpt()
    template = GOLDEN_MINIMAL_PROMPT if minimal else ANALYSIS_PROMPT
    prompt = template.format(
        clause=clause,
        topic=topic,
        pdf_excerpt=(pdf_text or "")[:2500],
        past_trouble_excerpt=past,
    )

    result = _call_llm(prompt)
    result["_clause"] = clause
    result["_topic"] = topic
    result["_past_trouble_loaded"] = TROUBLE_HISTORY.exists() or LESSONS_DB.exists()
    if minimal:
        result["_minimal"] = True

    ok, errors = validate_preflight_result(result, minimal=minimal)
    result["_validation"] = {"ok": ok, "errors": errors}

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [QualityPreflight] 保存: {save_path.name} ok={ok}", flush=True)

    if not ok:
        msg = "Quality preflight validation failed: " + "; ".join(errors)
        print(f"  [QualityPreflight] FAIL: {msg}", flush=True)
        if raise_on_fail:
            raise QualityPreflightError(msg)
        return result

    _print_summary(result)
    return result


_GEMINI_DIRECT_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
_GEMINI_DIRECT_MODELS = ["gemini-2.5-flash"]


def _extract_json_from_text(text: str) -> dict:
    """マークダウンフェンスや前後・後続テキストを除去してJSONを抽出する。
    Geminiがフェンス後に説明文を追記する場合でも1つ目のJSONオブジェクトのみ取得する。
    """
    import re
    text = text.strip()
    # ```json ... ``` フェンスを優先して試みる
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", text)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    # 先頭の { から raw_decode で最初の有効JSONオブジェクトだけをパース
    start = text.find("{")
    if start != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(text, start)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    return json.loads(text)  # 最終フォールバック（失敗時はそのまま例外を投げる）


def _call_llm_direct_gemini(prompt: str) -> dict | None:
    """LiteLLM迂回: 直接Gemini APIを呼ぶ。成功したらdictを返し、失敗したらNone。"""
    import urllib.request

    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        return None
    for model in _GEMINI_DIRECT_MODELS:
        try:
            payload = json.dumps(
                {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 8192,
                }
            ).encode()
            req = urllib.request.Request(
                _GEMINI_DIRECT_URL,
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                raw = data["choices"][0]["message"]["content"]
                result = _extract_json_from_text(raw)
                result["_model_used"] = f"direct/{model}"
                result["_completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                print(f"  [QualityPreflight] Gemini direct OK (model={model})", flush=True)
                return result
        except Exception as e:
            print(f"  [QualityPreflight] Gemini direct {model} failed: {e}", flush=True)
    return None


def _call_llm(prompt: str) -> dict:
    import urllib.request

    timeout = int(os.getenv("IATF_QUALITY_PREFLIGHT_TIMEOUT_SEC", "15"))
    models = [
        "google/gemini-2.5-flash",
        "opencode-go/deepseek-v4-flash",
        "local_fast",
    ]
    last_err = ""

    for model in models:
        try:
            payload = json.dumps(
                {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 3500,
                    "response_format": {"type": "json_object"},
                }
            ).encode()

            req = urllib.request.Request(
                f"{LITELLM_URL.rstrip('/')}/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {LITELLM_KEY}",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                raw = data["choices"][0]["message"]["content"]
                result = json.loads(raw)
                result["_model_used"] = model
                result["_completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                print(f"  [QualityPreflight] LLM OK via LiteLLM (model={model})", flush=True)
                return result
        except Exception as e:
            last_err = str(e)
            print(f"  [QualityPreflight] LiteLLM {model} failed: {e}", flush=True)
            time.sleep(0.5)

    # LiteLLM全滅時は直接Gemini APIを試みる
    print("  [QualityPreflight] LiteLLM全ルート失敗 → Gemini直接APIを試みます", flush=True)
    result = _call_llm_direct_gemini(prompt)
    if result is not None:
        return result

    return {
        "_llm_failed": True,
        "_error": last_err or "all models failed",
    }


def _print_summary(result: dict) -> None:
    risks = result.get("key_risks", [])
    emphasis = result.get("recommended_emphasis", [])
    fmea = result.get("fmea", [])

    if risks:
        print("  [QualityPreflight] --- key risks ---", flush=True)
        for r in risks:
            print(f"    ! {r}", flush=True)

    if fmea:
        high_rpn = sorted(
            fmea,
            key=lambda x: int(x.get("severity", 0))
            * int(x.get("occurrence", 0))
            * int(x.get("detection", 0)),
            reverse=True,
        )[:3]
        print("  [QualityPreflight] --- FMEA top RPN ---", flush=True)
        for f in high_rpn:
            rpn = int(f.get("severity", 0)) * int(f.get("occurrence", 0)) * int(f.get("detection", 0))
            print(f"    RPN={rpn} [{f.get('failure_mode', '')}]", flush=True)

    if emphasis:
        print("  [QualityPreflight] --- script emphasis ---", flush=True)
        for e in emphasis:
            print(f"    * {e}", flush=True)


def build_risk_context(preflight: dict) -> str:
    if not preflight or preflight.get("_skipped") or preflight.get("_llm_failed"):
        return ""

    lines = [
        "\n【品質事前分析（QC工程表・FMEA・FTA・なぜなぜ・Fishbone・ロジカルツリー）】",
    ]

    qc = preflight.get("qc_process_chart") or []
    if qc:
        lines.append("■ QC工程表（管理ポイント）:")
        for row in qc[:5]:
            lines.append(
                f"  - {row.get('step', '?')}: {row.get('control_point', '')} "
                f"[{row.get('standard', '')}] risk={row.get('risk', '')}"
            )

    risks = preflight.get("key_risks", [])
    if risks:
        lines.append("■ 主要リスク（台本で必ず触れる）:")
        for r in risks:
            lines.append(f"  - {r}")

    emphasis = preflight.get("recommended_emphasis", [])
    if emphasis:
        lines.append("■ 強調ポイント:")
        for e in emphasis:
            lines.append(f"  - {e}")

    fmea = preflight.get("fmea", [])
    if fmea:
        high = sorted(
            fmea,
            key=lambda x: int(x.get("severity", 0))
            * int(x.get("occurrence", 0))
            * int(x.get("detection", 0)),
            reverse=True,
        )[:3]
        lines.append("■ FMEA 重大故障:")
        for f in high:
            lines.append(
                f"  - [{f.get('failure_mode', '')}] cause={f.get('cause', '')} "
                f"-> {f.get('countermeasure', '')}"
            )

    why = preflight.get("why_why", [])
    if why:
        lines.append("■ なぜなぜ 真因:")
        for w in why[:2]:
            lines.append(f"  - {w.get('why5', '')} -> {w.get('action', '')}")

    lt = preflight.get("logical_tree") or {}
    if lt:
        lines.append(f"■ ロジカルツリー頂上: {lt.get('top_event', '')}")
        for node in (lt.get("nodes") or [])[:4]:
            lines.append(f"  - [{node.get('id', '?')}] {node.get('text', '')}")

    if preflight.get("_past_trouble_loaded"):
        lines.append("■ 過去トラ参照: trouble_history.md + iatf_generation_lessons.json")

    pd = preflight.get("production_design") or {}
    if pd:
        lines.append("■ 制作レイアウト(出演者/背景/照明/カメラ):")
        for c in (pd.get("cast_plan") or [])[:4]:
            lines.append(f"  - cast: {c}")
        bg = pd.get("background_plan") or {}
        lines.append(f"  - bg: {bg.get('label', '')} props={bg.get('props', [])}")
        cam = pd.get("camera_plan") or {}
        lines.append(f"  - camera: {cam.get('shot_type', '')} {cam.get('movement', '')}")

    return "\n".join(lines)
