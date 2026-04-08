#!/usr/bin/env python3
"""
service_healer.py — Infrastructure Health Monitor + Auto-Restart
=================================================================
Checks Ollama, LiteLLM, Qdrant, n8n.
Outputs JSON consumed by the n8n Service Monitor workflow.
State persisted to avoid restart storms (cooldown per service).

Usage:
  python3 /home/node/clawd/service_healer.py
  python3 /home/node/clawd/service_healer.py --dry-run
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))

SERVICES = {
    "ollama": {
        "url":        "http://ollama:11434/api/tags",
        "container":  "clawstack-unified-ollama-1",
        "check_key":  None,   # just expect HTTP 200
    },
    "litellm": {
        "url":        "http://litellm:4000/health",
        "container":  "clawstack-unified-litellm-1",
        "check_key":  None,
    },
    "qdrant": {
        "url":        "http://qdrant:6333/healthz",
        "container":  "clawstack-unified-qdrant-1",
        "check_key":  None,
    },
    "n8n": {
        "url":        "http://n8n:5678/healthz",
        "container":  "clawstack-unified-n8n-1",
        "check_key":  None,
    },
}

COOLDOWN_MINUTES = 30          # don't restart same service within 30 min
STATE_FILE       = Path("/home/node/clawd/service_healer_state.json")
LOG_FILE         = Path("/home/node/clawd/service_healer.log")
TIMEOUT_SEC      = 8

DRY_RUN = "--dry-run" in sys.argv


# ── Utility ───────────────────────────────────────────────────────────────────

def now():
    return datetime.now(JST)

def log(msg: str):
    ts = now().strftime("%Y-%m-%d %H:%M:%S JST")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"WARN: Could not save state: {e}")


def check_http(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            return resp.status < 400
    except Exception:
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    state   = load_state()
    current = now()
    actions = []
    msgs    = []

    for svc_name, cfg in SERVICES.items():
        healthy = check_http(cfg["url"])
        svc_state = state.setdefault(svc_name, {})

        if healthy:
            was_down = svc_state.get("status") == "down"
            svc_state["status"]  = "up"
            svc_state["last_ok"] = current.isoformat()
            if was_down:
                msg = f"✅ [{svc_name}] 復旧を確認しました"
                log(msg)
                msgs.append(msg)
        else:
            svc_state["status"]       = "down"
            svc_state["last_fail"]    = current.isoformat()

            last_restart_iso = svc_state.get("last_restart")
            in_cooldown = False
            if last_restart_iso:
                try:
                    last_dt   = datetime.fromisoformat(last_restart_iso)
                    elapsed_m = (current - last_dt).total_seconds() / 60
                    in_cooldown = elapsed_m < COOLDOWN_MINUTES
                except Exception:
                    pass

            if in_cooldown:
                msg = f"⏳ [{svc_name}] ダウン中 (クールダウン中, 再起動スキップ)"
                log(msg)
                msgs.append(msg)
            else:
                svc_state["last_restart"] = current.isoformat()
                container = cfg["container"]
                actions.append({
                    "service":   svc_name,
                    "container": container,
                    "action":    "restart",
                })
                msg = f"🔄 [{svc_name}] ダウン検知 → 再起動: {container}"
                log(msg)
                msgs.append(msg)

    save_state(state)

    result = {
        "timestamp":  current.isoformat(),
        "dry_run":    DRY_RUN,
        "all_ok":     len(actions) == 0 and all(
                          state.get(s, {}).get("status") == "up"
                          for s in SERVICES
                      ),
        "actions":    actions,
        "messages":   msgs,
        "telegram":   "\n".join(msgs) if msgs else None,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
