from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def discover_repo_root() -> Path:
    candidates = []

    resolved = Path(__file__).resolve()
    candidates.extend(resolved.parents)

    cwd = Path.cwd().resolve()
    candidates.extend(cwd.parents)
    candidates.append(cwd)

    candidates.extend(
        [
            Path("D:/Clawdbot_Docker_20260125"),
            Path("E:/ClawstackData"),
        ]
    )

    for candidate in candidates:
        if (candidate / "AGENTS.md").exists() and (candidate / "data" / "state").exists():
            return candidate

    raise FileNotFoundError("Could not locate repository root for Gemma 4 readiness check.")


ROOT = discover_repo_root()
STATUS_PATH = ROOT / "data" / "workspace" / "gemma4_readiness_status.json"
POLICY_PATH = ROOT / "data" / "workspace" / "gemma4_adoption_policy.json"
OVERLAY_PATH = ROOT / "data" / "state" / "litellm_config.gemma4.experimental.yaml"

OLLAMA_TAG_URLS = [
    "http://127.0.0.1:11434/api/tags",
    "http://host.docker.internal:11434/api/tags",
]


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def fetch_tags(url: str) -> tuple[bool, object]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        models = data.get("models", [])
        names = [m.get("name", "") for m in models if isinstance(m, dict)]
        return True, names
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, Exception) as exc:
        return False, str(exc)


def fetch_tags_via_wsl(url: str) -> tuple[bool, object]:
    py = (
        "import json, urllib.request; "
        f"url={url!r}; "
        "req=urllib.request.Request(url, headers={'Accept':'application/json'}); "
        "resp=urllib.request.urlopen(req, timeout=5); "
        "raw=resp.read().decode('utf-8', 'replace'); "
        "data=json.loads(raw); "
        "print(json.dumps([m.get('name','') for m in data.get('models', [])]))"
    )
    cmd = ["wsl.exe", "-d", "Ubuntu", "-e", "python3", "-c", py]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=12, check=False)
        if completed.returncode != 0:
            return False, (completed.stderr or completed.stdout or f"returncode={completed.returncode}").strip()
        payload = json.loads((completed.stdout or "[]").strip())
        return True, payload
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        return False, str(exc)


def main() -> int:
    attempts = []
    gemma4_tags: list[str] = []
    reachable = False

    for url in OLLAMA_TAG_URLS:
        ok, payload = fetch_tags(url)
        attempts.append({"url": url, "ok": ok, "result": payload})
        if ok:
            reachable = True
            gemma4_tags = [name for name in payload if "gemma4" in name.lower()]
            if gemma4_tags:
                break

    if not reachable:
        for url in OLLAMA_TAG_URLS:
            ok, payload = fetch_tags_via_wsl(url)
            attempts.append({"url": f"wsl:{url}", "ok": ok, "result": payload})
            if ok:
                reachable = True
                gemma4_tags = [name for name in payload if "gemma4" in name.lower()]
                if gemma4_tags:
                    break

    policy = {}
    if POLICY_PATH.exists():
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    status = {
        "updatedAt": iso_now(),
        "ollamaReachable": reachable,
        "gemma4Detected": bool(gemma4_tags),
        "detectedTags": gemma4_tags,
        "liteLLMOverlayReady": OVERLAY_PATH.exists(),
        "policyStatus": policy.get("status", "unknown"),
        "policyMode": policy.get("mode", "unknown"),
        "activationState": "ready_to_enable" if gemma4_tags else "ready_when_pulled",
        "recommendedNextStep": (
            "Run activate_gemma4_local_aliases.py after verifying the exact Gemma 4 Ollama tags."
            if gemma4_tags
            else "Start or restore Ollama, then pull a real Gemma 4 tag before enabling aliases."
        ),
        "checks": attempts,
    }

    STATUS_PATH.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if gemma4_tags else 1


if __name__ == "__main__":
    raise SystemExit(main())
