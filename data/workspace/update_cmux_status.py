#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data" / "workspace" / "apps" / "cmux_hub" / "cmux_status.json"
OPENCLAW_CONFIG = ROOT / "data" / "state" / "openclaw.json"
MODELS_JSON = ROOT / "data" / "state" / "agents" / "main" / "agent" / "models.json"
TELEGRAM_HARNESS = ROOT / "data" / "state" / "telegram_fast" / "harness_status.json"
TELEGRAM_BRIDGE = ROOT / "scripts" / "telegram_fast_bridge.js"
SESSIONS_DIR = ROOT / "data" / "state" / "agents" / "main" / "sessions"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"


def now_jst_iso() -> str:
    return datetime.now(JST).isoformat()


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def read_text(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return fallback


def fetch_ollama_tags() -> list[str]:
    try:
        req = Request(OLLAMA_TAGS_URL, headers={"Accept": "application/json"})
        with urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return [item.get("name", "") for item in payload.get("models", []) if item.get("name")]
    except Exception:
        return []


def parse_telegram_reply_model(text: str) -> str | None:
    marker = "const ollamaModel = process.env.TELEGRAM_FAST_MODEL || "
    idx = text.find(marker)
    if idx == -1:
        return None
    tail = text[idx + len(marker):].split(";", 1)[0].strip()
    if tail.startswith(("'", '"')) and tail.endswith(("'", '"')):
        return tail[1:-1]
    return tail or None


def normalize_model_name(model_id: str | None) -> str | None:
    if not model_id:
        return None
    return model_id.split("/", 1)[1] if model_id.startswith("ollama/") else model_id


def summarize_recent_sessions(limit_files: int = 12) -> dict[str, Any]:
    if not SESSIONS_DIR.exists():
        return {
            "files_scanned": 0,
            "ollama_errors": 0,
            "fallback_provider_calls": 0,
            "providers_seen": [],
            "models_seen": [],
            "latest_error": None,
        }

    files = sorted(SESSIONS_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit_files]
    providers = Counter()
    models = Counter()
    ollama_errors = 0
    fallback_provider_calls = 0
    latest_error = None

    for file in files:
        try:
            for line in file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                msg = obj.get("message", {})
                provider = msg.get("provider")
                model = msg.get("model")
                if provider:
                    providers[provider] += 1
                if model:
                    models[model] += 1
                if provider == "ollama" and (msg.get("stopReason") == "error" or msg.get("errorMessage")):
                    ollama_errors += 1
                    latest_error = {
                        "provider": provider,
                        "model": model,
                        "error": msg.get("errorMessage") or "unknown ollama error",
                        "session": file.name,
                    }
                if provider and provider != "ollama":
                    fallback_provider_calls += 1
                if obj.get("customType") == "openclaw:prompt-error":
                    data = obj.get("data", {})
                    latest_error = {
                        "provider": data.get("provider"),
                        "model": data.get("model"),
                        "error": data.get("error"),
                        "session": file.name,
                    }
        except Exception:
            continue

    return {
        "files_scanned": len(files),
        "ollama_errors": ollama_errors,
        "fallback_provider_calls": fallback_provider_calls,
        "providers_seen": [name for name, _ in providers.most_common(5)],
        "models_seen": [name for name, _ in models.most_common(8)],
        "latest_error": latest_error,
    }


def build_status() -> dict[str, Any]:
    openclaw = read_json(OPENCLAW_CONFIG, {})
    runtime = read_json(ROOT / "data" / "state" / "workspace" / "cmux_runtime_config.json", {})
    models_json = read_json(MODELS_JSON, {})
    telegram = read_json(TELEGRAM_HARNESS, {})
    bridge_text = read_text(TELEGRAM_BRIDGE)
    ollama_models = fetch_ollama_tags()

    primary = openclaw.get("agents", {}).get("defaults", {}).get("model", {}).get("primary")
    fallbacks = openclaw.get("agents", {}).get("defaults", {}).get("model", {}).get("fallbacks", [])
    registered = [
        item.get("id")
        for item in (
            models_json.get("providers", {})
            .get("ollama", {})
            .get("models", [])
        )
        if item.get("id")
    ]
    telegram_model = telegram.get("model") or parse_telegram_reply_model(bridge_text)
    recent = summarize_recent_sessions()

    primary_normalized = normalize_model_name(primary)
    telegram_normalized = normalize_model_name(telegram_model)

    return {
        "generatedAt": now_jst_iso(),
        "runtime": {
            "mode": runtime.get("mode"),
            "roles": runtime.get("roles", {}),
            "task_routes": runtime.get("task_routes", {}),
        },
        "openclaw": {
            "primary": primary,
            "primary_installed": primary_normalized in ollama_models if primary_normalized else False,
            "fallbacks": fallbacks,
            "registered_local_models": registered,
        },
        "telegram": {
            "reply_model": telegram_model,
            "reply_model_installed": telegram_normalized in ollama_models if telegram_normalized else False,
            "state": telegram.get("state"),
            "pid": telegram.get("pid"),
            "updatedAt": telegram.get("updatedAt"),
            "lastChatId": telegram.get("lastChatId"),
        },
        "ollama": {
            "models": ollama_models,
            "count": len(ollama_models),
        },
        "recentActivity": recent,
        "statusSummary": {
            "fallback_mode": "active" if recent.get("fallback_provider_calls", 0) > 0 else "not_observed_recently",
            "ollama_health": "degraded" if recent.get("ollama_errors", 0) > 0 else "ok",
        },
    }


def main() -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(build_status(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(STATUS_PATH))


if __name__ == "__main__":
    main()
