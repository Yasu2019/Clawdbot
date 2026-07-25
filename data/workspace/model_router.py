#!/usr/bin/env python3
"""
model_router.py — Clawstack Task Classifier & Model Router (Unified V2.2)
========================================================================
Analyzes task descriptions and context requirements to route to the optimal model.
Routes via LiteLLM proxy (http://litellm:4000).

Usage:
  CLI:    python model_router.py "Fix this bug"
  Demo:   python model_router.py --demo
  HTTP:   python model_router.py --serve
"""

from __future__ import annotations
import argparse
import sys
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Task Classification Definitions
# ---------------------------------------------------------------------------
ModelTier = Literal[
    "local_light",   # Fast, free, local (Qwen no-think)
    "local_codex",   # Coding specialized, local
    "local_quality", # IATF / audit local (Gemma4 eval or no-think fallback)
    "local_judge",   # Fast internal reasoning/routing (Gemma4)
    "cloud_medium",  # Balanced cloud (Gemini Flash / GPT-4o-mini)
    "cloud_heavy",   # Deep reasoning cloud (GPT-4o / Gemini Pro)
    "cloud_batch",   # Massive context cloud (Kimi K2.6 - 256K)
    "security_lock"  # Forced local due to sensitive data
]

LITELLM_MODEL_MAP: dict[ModelTier, str] = {
    "local_light":  "local_fast_nothink",
    "local_codex":  "codex",
    "local_quality": "local_fast_nothink",
    "local_judge":  "openai/gemma4",
    "cloud_medium": "openai/gpt-4o-mini",
    "cloud_heavy":  "openai/gpt-4o",
    "cloud_batch":  "openai/kimi-agent-primary",
    "security_lock": "local_fast_nothink",
}


def _load_api_routing_hints() -> dict:
    path = Path(__file__).resolve().parent / "api_routing_insights.json"
    if not path.exists():
        try:
            import api_routing_insights as ari

            return ari.build_insights()
        except Exception:
            return {}
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


_API_HINTS = _load_api_routing_hints()
if _API_HINTS.get("gemma4_eval_ready"):
    LITELLM_MODEL_MAP["local_quality"] = "openai/gemma4"
    LITELLM_MODEL_MAP["local_judge"] = "openai/gemma4"

# ── Production Override (DeepSeek V4 Integration) ──────────────────────────
ROUTING_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "routing.json")
def load_routing_config():
    if os.path.exists(ROUTING_CONFIG_PATH):
        try:
            with open(ROUTING_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[router] Warning: Could not load routing.json: {e}", file=sys.stderr)
    return {}

_ROUTING_CONFIG = load_routing_config()
if _ROUTING_CONFIG:
    print(f"[router] Applying production override from routing.json", file=sys.stderr)
    if "default" in _ROUTING_CONFIG:
        LITELLM_MODEL_MAP["cloud_heavy"] = _ROUTING_CONFIG["default"]
        LITELLM_MODEL_MAP["cloud_medium"] = _ROUTING_CONFIG["default"]
    if "local_light" in _ROUTING_CONFIG:
        LITELLM_MODEL_MAP["local_light"] = _ROUTING_CONFIG["local_light"]
    if "local_quality" in _ROUTING_CONFIG:
        LITELLM_MODEL_MAP["local_quality"] = _ROUTING_CONFIG["local_quality"]
    if "local_codex" in _ROUTING_CONFIG:
        LITELLM_MODEL_MAP["local_codex"] = _ROUTING_CONFIG["local_codex"]
    elif "local_coder" in _ROUTING_CONFIG:
        LITELLM_MODEL_MAP["local_codex"] = _ROUTING_CONFIG["local_coder"]
    elif "coding_fast" in _ROUTING_CONFIG:
        LITELLM_MODEL_MAP["local_codex"] = _ROUTING_CONFIG["coding_fast"]
    if "security_lock" in _ROUTING_CONFIG:
        LITELLM_MODEL_MAP["security_lock"] = _ROUTING_CONFIG["security_lock"]
    elif "local_light" in _ROUTING_CONFIG:
        LITELLM_MODEL_MAP["security_lock"] = _ROUTING_CONFIG["local_light"]
# ───────────────────────────────────────────────────────────────────────────

# GPU load threshold: local tiers fall back to cloud when GPU utilization exceeds this
GPU_LOAD_THRESHOLD = 80.0


def get_gpu_utilization() -> float | None:
    """Returns primary GPU utilization % (0-100), or None if nvidia-smi unavailable."""
    try:
        import subprocess
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0:
            return float(r.stdout.strip().split("\n")[0])
    except Exception:
        pass
    return None


# Routing Rules (Order matters: first match wins)
_ROUTING_RULES: list[tuple[ModelTier, list[str], str]] = [
    # 1. SECURITY LOCK (Highest Priority)
    (
        "security_lock",
        [
            "機密", "confidential", "internal only", "社外秘", "password", "パスワード",
            "秘密", "private", "財務", "financial", "顧客名", "個人情報", "pii",
            "secret", "credentials", "取得したキー", "取引先", "customer name"
        ],
        "[SAFE] 秘密情報検知: 機密保護のため強制的にローカルAIへルーティング"
    ),
    
    # 2. CLOUD BATCH (Long Context)
    (
        "cloud_batch",
        [
            "大量", "全部", "全ファイル", "massive", "long context", "256k",
            "全ドキュメント", "audit logs", "プロジェクト全体", "whole project",
            "要件定義書すべて", "マニュアルすべて", "integrated summary"
        ],
        "[CLOUD BATCH] 長文処理 (256K): 大規模な情報の分析に適した Kimi K2.6 へルーティング"
    ),

    # 3. DESIGN & ILLUSTRATION (Serious Image Protocol)
    (
        "cloud_medium",
        [
            "図解", "ポスター", "チラシ", "イラスト", "概念図", "banner", "poster",
            "illustration", "layout", "監査説明図", "不具合図", "説明用ビジュアル"
        ],
        "[CLOUD VISUAL] 実務画像生成: ChatGPT Serious Image Protocol (DALL-E 3) を推奨"
    ),

    # 4. CLOUD HEAVY (Reasoning)
    (
        "cloud_heavy",
        [
            "設計", "アーキテクチャ", "方針", "構成変更", "根本原因", "root cause",
            "migration", "refactor", "リファクタ", "仕様策定", "architecture",
            "complex reasoning", "戦略", "戦略的"
        ],
        "[CLOUD HEAVY] 高度な推論: 複雑な設計思考が必要なため、高性能モデル (GPT-4o) へルーティング"
    ),

    # 4. LOCAL QUALITY (IATF / audit -- API benchmark: Gemma4 eval > qwen3:8b for JA)
    (
        "local_quality",
        [
            "iatf", "監査", "是正", "再発防止", "効果確認", "fmea", "品質保証",
            "内部監査", "不適合", "nc ", "capa", "クレーム", "8d", "qc工程",
        ],
        "[LOCAL QUALITY] IATF/品質: eval Gemma4 when ready, else qwen3-nothink (API bench)"
    ),

    # 5. LOCAL CODEX (Implementation)
    (
        "local_codex",
        [
            "実装", "implement", "coding", "コード生成", "バグ修正", "diff",
            "一括置換", "定型", "boilerplate", "scaffold", "差分", "unittest"
        ],
        "[LOCAL CODE] コード実装: ローカルのプログラミング特化モデル (Codex/Qwen) で処理"
    ),

    # 6. LOCAL LIGHT (Simple tasks)
    (
        "local_light",
        [
            "要約", "summary", "確認", "list", "一覧", "教えて", "grep", "find",
            "簡単な", "挨拶", "hello", "調子は", "status"
        ],
        "[LOCAL LIGHT] 速度とコストを優先し、ローカルの軽量モデルで処理"
    )
]

@dataclass
class RouteResult:
    tier: ModelTier
    litellm_model: str
    reason: str
    use_plan_mode: bool
    matched_keywords: list[str]
    security_flag: bool
    requires_consent: bool
    gpu_utilization: float | None = None

def route_task(task: str) -> RouteResult:
    """Analyzes task description and selects the optimal model."""
    task_lower = task.lower()
    result: RouteResult | None = None

    # 1. Security lock (always local, GPU load ignored)
    for tier, keywords, reason in _ROUTING_RULES:
        if tier == "security_lock":
            matched = [kw for kw in keywords if kw.lower() in task_lower]
            if matched:
                result = RouteResult(
                    tier="security_lock",
                    litellm_model=LITELLM_MODEL_MAP["security_lock"],
                    reason=reason,
                    use_plan_mode=True,
                    matched_keywords=matched,
                    security_flag=True,
                    requires_consent=False,
                )
                break

    # 2. Standard keyword routing
    if result is None:
        for tier, keywords, reason in _ROUTING_RULES:
            if tier == "security_lock":
                continue
            matched = [kw for kw in keywords if kw.lower() in task_lower]
            if matched:
                result = RouteResult(
                    tier=tier,
                    litellm_model=LITELLM_MODEL_MAP[tier],
                    reason=reason,
                    use_plan_mode=(tier in ["cloud_heavy", "cloud_batch"]),
                    matched_keywords=matched,
                    security_flag=False,
                    requires_consent=tier.startswith("cloud"),
                )
                break

    # 3. Default fallback
    if result is None:
        default_model = _ROUTING_CONFIG.get("default", LITELLM_MODEL_MAP["cloud_medium"])
        result = RouteResult(
            tier="cloud_medium",
            litellm_model=default_model,
            reason="[DEFAULT] 特徴未検知: 汎用バランスのモデルを使用",
            use_plan_mode=False,
            matched_keywords=[],
            security_flag=False,
            requires_consent=True,
        )

    # 4. GPU load check: downgrade local tiers to cloud when GPU is too busy
    gpu = get_gpu_utilization()
    result.gpu_utilization = gpu
    if result.tier.startswith("local_") and not result.security_flag:
        if gpu is not None and gpu >= GPU_LOAD_THRESHOLD:
            fallback = _ROUTING_CONFIG.get("default", LITELLM_MODEL_MAP["cloud_medium"])
            result.reason += f" [GPU {gpu:.0f}%≥{GPU_LOAD_THRESHOLD:.0f}%→CLOUD]"
            result.tier = "cloud_medium"
            result.litellm_model = fallback
            result.requires_consent = True

    return result

def _start_server(host: str = "0.0.0.0", port: int = 18798) -> None:
    try:
        from fastapi import FastAPI
        import uvicorn
        from pydantic import BaseModel
    except ImportError:
        print("Required: pip install fastapi uvicorn")
        sys.exit(1)

    app = FastAPI(title="Clawstack Autonomous Router", version="2.3.0")

    class RoutingRequest(BaseModel):
        task: str

    @app.post("/route")
    def route_endpoint(req: RoutingRequest):
        res = route_task(req.task)
        return {
            "tier": res.tier,
            "model": res.litellm_model,
            "reason": res.reason,
            "matched": res.matched_keywords,
            "security_lock": res.security_flag,
            "requires_consent": res.requires_consent,
            "gpu_utilization": res.gpu_utilization,
        }

    @app.get("/gpu")
    def gpu_endpoint():
        return {"gpu_utilization": get_gpu_utilization(), "threshold": GPU_LOAD_THRESHOLD}

    uvicorn.run(app, host=host, port=port)

def _cli() -> None:
    parser = argparse.ArgumentParser(description="Clawstack Model Router")
    parser.add_argument("task", nargs="?", help="Task description")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.serve:
        _start_server()
        return

    if args.demo:
        samples = [
            "ユーザーのパスワード変更機能を実装して",
            "全ファイルの依存関係を分析して要約して",
            "新しいアーキテクチャへの移行方針を立てて",
            "今日の天気を教えて",
            "簡単なコードのバグを直して",
            "機密扱いのプロジェクトAについて教えて"
        ]
        print(f"{'Target Task':<45} | {'Tier':<15} | {'Security'}")
        print("-" * 85)
        for s in samples:
            r = route_task(s)
            lock = "LOCKED" if r.security_flag else "OPEN"
            print(f"{s[:44]:<45} | {r.tier:<15} | {lock}")
        return

    if args.task:
        r = route_task(args.task)
        gpu_str = f"{r.gpu_utilization:.0f}%" if r.gpu_utilization is not None else "n/a"
        print(f"Decision: {r.tier} ({r.litellm_model})")
        print(f"Reason:   {r.reason}")
        print(f"GPU:      {gpu_str} (threshold {GPU_LOAD_THRESHOLD:.0f}%)")
        if r.requires_consent:
            print("(!) NOTICE: This task will use CLOUD API. External costs and data sharing may apply.")
        if r.security_flag:
            print("(!) WARNING: Security Lock Engaged (Local only)")

if __name__ == "__main__":
    _cli()
