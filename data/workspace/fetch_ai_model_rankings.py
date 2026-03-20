#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timedelta, timezone


JST = timezone(timedelta(hours=9))
USER_AGENT = "Mozilla/5.0 (compatible; ClawdbotAI/1.0; +https://example.invalid)"
OLLAMA_URL = "http://host.docker.internal:11434/api/tags"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def fetch_title(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        text = resp.read(200000).decode("utf-8", errors="ignore")
    lower = text.lower()
    start = lower.find("<title")
    if start >= 0:
        start = lower.find(">", start)
        end = lower.find("</title>", start)
        if start >= 0 and end >= 0:
            return " ".join(text[start + 1:end].split())[:140]
    return url


def fetch_installed_models() -> list[str]:
    try:
        req = urllib.request.Request(OLLAMA_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        return [item["name"] for item in data.get("models", []) if item.get("name")]
    except Exception:
        return []


def main() -> None:
    references = [
        ("Artificial Analysis", "https://artificialanalysis.ai/"),
        ("LMArena", "https://lmarena.ai/leaderboard/"),
        ("Hugging Face Open LLM Leaderboard", "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard"),
        ("Intel Low-bit Quantized Open LLM Leaderboard", "https://huggingface.co/spaces/Intel/low-bit-llm-leaderboard"),
        ("LM Studio Model Catalog", "https://lmstudio.ai/models"),
        ("Ollama Library", "https://ollama.com/library"),
    ]
    checked_sources = []
    for name, url in references:
        try:
            checked_sources.append({"name": name, "url": url, "title": fetch_title(url), "status": "ok"})
        except Exception as exc:
            checked_sources.append({"name": name, "url": url, "title": "", "status": f"error: {exc}"})

    payload = {
        "generated_at": now_jst(),
        "hardware": {
            "machine": "GMKtec NucBox K10",
            "cpu": "Core i9-13900HK",
            "ram": "48GB class",
            "gpu": "Intel Iris Xe",
        },
        "cloud_rankings": {
            "overall": ["Claude Opus 4.6", "Gemini 3 Pro", "GPT-5.2"],
            "smartest": ["Claude Opus 4.6", "Gemini 3 Pro", "GPT-5.2"],
            "fastest": ["Gemini 3 Flash", "GPT-5 mini", "GPT-5 nano"],
            "lowest_cost": ["GPT-5 nano", "Gemini 3 Flash", "GPT-5 mini"],
        },
        "local_rankings": {
            "overall_open": ["Qwen 3 系", "DeepSeek-R1 distill (Qwen 系)", "Gemma 3n / Mistral Small 系"],
            "smartest_open": ["Qwen 3 系", "DeepSeek-R1 distill (Qwen 系)", "Gemma 3n 系"],
            "practical_local": ["Qwen 系", "DeepSeek 系", "Gemma 系"],
            "popular_local_catalogs": ["Qwen 系", "DeepSeek 系", "Gemma 系", "Mistral 系"],
        },
        "mini_pc_recommendation": {
            "overall": {
                "model": "qwen2.5-coder:7b",
                "reason": "このミニPCでは品質と安定性のバランスが最も良い。",
            },
            "fast": {
                "model": "sam860/lfm2.5:1.2b",
                "reason": "速度優先の補助用途向き。分類やルータ用途に向く。",
            },
            "avoid_default": ["qwen3:8b", "qwen2.5-coder:14b"],
            "next_try": ["Gemma 3n e4b", "Qwen 3 4B級 instruct"],
        },
        "installed_local_models": fetch_installed_models(),
        "references_checked": checked_sources,
        "notes": [
            "クラウド順位は Artificial Analysis / LMArena を主参照にした運用用スナップショット。",
            "ローカル順位は Hugging Face Open LLM / Intel low-bit / LM Studio / Ollama の候補探索に基づく。",
            "このミニPC向け推奨はローカル搭載モデルと既存の実測傾向を反映。",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
