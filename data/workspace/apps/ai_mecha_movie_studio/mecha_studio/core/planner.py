# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import re
from datetime import datetime
from .ollama import chat

REQUIRED_KEYS = {"architecture", "confidence", "rationale", "reuse", "isolate", "risks", "next_steps"}

# reuse候補の名称 → 検出フラグのキー
MATCH_TERMS = {
    "comfyui": ("comfyui", "comfy"),
    "blender": ("blender",),
    "ffmpeg": ("ffmpeg", "ffprobe"),
    "node": ("node", "npm", "npx"),
    "remotion": ("remotion",),
    "ollama": ("ollama",),
    "git": ("git",),
    "python": ("python",),
}


def availability(scan_report):
    """検出結果を『再利用できると言い切れるか』のフラグへ落とす。"""
    tools = scan_report.get("tools", {}) or {}
    dirs = scan_report.get("directories", {}) or {}
    services = scan_report.get("services", {}) or {}
    return {
        # フォルダが無くてもAPIが応答していれば再利用可能とみなす（Docker稼働等）
        "comfyui": bool(dirs.get("comfyui") or services.get("comfyui_api")),
        "blender": bool(tools.get("blender")),
        "ffmpeg": bool(tools.get("ffmpeg")),
        "node": bool(tools.get("node") or tools.get("npx")),
        "remotion": bool(dirs.get("remotion") or tools.get("npx")),
        "ollama": bool(tools.get("ollama") or services.get("ollama_api")),
        "git": bool(tools.get("git")),
        "python": bool(tools.get("python") or tools.get("py")),
        "nvidia_gpu": bool(scan_report.get("gpu")),
    }


def _verify_reuse(items, avail):
    """AIが挙げた再利用候補を検出結果と突合する。
    検出済みと確認できたものだけを reuse に残し、残りは未検証として分離する。"""
    verified, unverified = [], []
    for item in items or []:
        text = str(item).lower()
        keys = [k for k, terms in MATCH_TERMS.items() if any(t in text for t in terms)]
        if keys and all(avail.get(k) for k in keys):
            verified.append(item)
        else:
            unverified.append(item)
    return verified, unverified


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
    avail = availability(scan_report)
    reuse = []
    if avail["comfyui"]:
        reuse.append("ComfyUI")
    if avail["blender"]:
        reuse.append("Blender")
    if avail["ffmpeg"]:
        reuse.append("FFmpeg")
    if avail["node"]:
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

    # AIの回答をそのまま信用せず、検出結果と突合する
    avail = availability(scan_report)
    verified, unverified = _verify_reuse(obj.get("reuse", []), avail)
    obj["reuse"] = verified
    obj["reuse_unverified"] = unverified
    obj["detected"] = avail
    if unverified:
        obj.setdefault("risks", []).append(
            "未検出のまま再利用候補に挙がった項目があります: " + ", ".join(str(x) for x in unverified)
            + "。導入前に実体の有無を確認してください。"
        )
    obj["generated_at"] = datetime.now().isoformat(timespec="seconds")
    return obj
