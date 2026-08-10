# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import re
from datetime import datetime
from .ollama import chat

REQUIRED_KEYS = {"architecture", "confidence", "rationale", "reuse", "isolate", "risks", "next_steps"}


def _extract_json(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("JSON object not found")
    return json.loads(m.group(0))


def _fallback(scan_report):
    dirs = scan_report.get("directories", {})
    tools = scan_report.get("tools", {})
    reuse = []
    if dirs.get("comfyui"):
        reuse.append("ComfyUI")
    if tools.get("blender"):
        reuse.append("Blender")
    if tools.get("ffmpeg"):
        reuse.append("FFmpeg")
    if tools.get("node") or tools.get("npx"):
        reuse.append("Node/Remotion")
    architecture = "hybrid" if reuse else "standalone"
    return {
        "architecture": architecture,
        "confidence": 0.70,
        "rationale": "既存資産が検出できた場合は再利用し、モデルごとのPython/CUDA依存衝突を避けるため重いAIモデルは独立サービスとして分離するのが安全です。",
        "reuse": reuse,
        "isolate": ["SCAIL-2/ComfyUI workflow", "3D AIGC models", "TTS/music/foley models"],
        "risks": ["CUDA/PyTorch依存競合", "VRAM 16GBでの同時ロード", "モデルライセンス差異"],
        "next_steps": ["既存ComfyUIのAPI疎通確認", "FFmpeg/Blender/Node検出確認", "各モデルを個別環境または既存環境のどちらに置くか段階導入"],
        "source": "rule_fallback",
    }


def decide(scan_report, base_url: str, model: str):
    prompt = f"""
以下はWindowsローカルAI動画制作PCの検出結果です。
目的は、既存システムへ融合するか、単独アプリとして構築するか、ハイブリッドにするかを決定することです。

最優先条件:
- RTX 16GB級を想定。重いモデルは同時ロードしない。
- 既存ComfyUI/Blender/FFmpeg/Remotion/Ollamaがあれば壊さず再利用したい。
- SCAIL-2, PartCrafter, PartField, SkinTokens/TokenRig, Puppeteer, Wan2.2,
  VoxCPM2, Qwen3-TTS, ACE-Step, HunyuanVideo-Foley, Audio2Face, MediaPipe,
  WhisperX, Remotion, FFmpegなどを将来接続する。
- CUDA/PyTorch依存が競合するAIモデルは別venv/Docker/APIサービスへ隔離可能。
- ユーザーはBlenderを手操作しない。Blenderはheadless自動処理。
- AIの提案をそのまま自動適用せず、計画JSONのみ作る。

検出結果:
{json.dumps(scan_report, ensure_ascii=False, indent=2)}

次のJSONだけを返してください。architectureは integrate / standalone / hybrid のいずれか。
{{
  "architecture": "hybrid",
  "confidence": 0.0,
  "rationale": "日本語説明",
  "reuse": ["再利用するもの"],
  "isolate": ["別環境に隔離するもの"],
  "risks": ["リスク"],
  "next_steps": ["次の手順"]
}}
"""
    try:
        raw = chat(base_url, model, prompt)
        obj = _extract_json(raw)
        if not REQUIRED_KEYS.issubset(obj.keys()):
            raise ValueError("required keys missing")
        if obj["architecture"] not in {"integrate", "standalone", "hybrid"}:
            raise ValueError("invalid architecture")
        obj["source"] = f"ollama:{model}"
    except Exception as exc:
        obj = _fallback(scan_report)
        obj["fallback_reason"] = str(exc)
    obj["generated_at"] = datetime.now().isoformat(timespec="seconds")
    return obj
