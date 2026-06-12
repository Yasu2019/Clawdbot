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
    ("main", "http://127.0.0.1:11434/api/tags"),
    ("eval", "http://127.0.0.1:11435/api/tags"),
    ("main_docker", "http://host.docker.internal:11434/api/tags"),
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
    eval_gemma4_tags: list[str] = []
    reachable = False
    eval_reachable = False

    for channel, url in OLLAMA_TAG_URLS:
        ok, payload = fetch_tags(url)
        attempts.append({"channel": channel, "url": url, "ok": ok, "result": payload})
        if not ok:
            continue
        tags = [name for name in payload if "gemma4" in name.lower()]
        if channel == "eval":
            eval_reachable = True
            eval_gemma4_tags = tags
        else:
            reachable = True
            if tags:
                gemma4_tags = tags

    if not reachable and not eval_reachable:
        for channel, url in OLLAMA_TAG_URLS:
            ok, payload = fetch_tags_via_wsl(url)
            attempts.append({"channel": f"wsl_{channel}", "url": url, "ok": ok, "result": payload})
            if not ok:
                continue
            tags = [name for name in payload if "gemma4" in name.lower()]
            if channel == "eval":
                eval_reachable = True
                eval_gemma4_tags = tags
            else:
                reachable = True
                if tags:
                    gemma4_tags = tags

    all_gemma4 = sorted(set(gemma4_tags + eval_gemma4_tags))

    policy = {}
    if POLICY_PATH.exists():
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    has_eval = bool(eval_gemma4_tags)
    has_any = bool(all_gemma4)
    status = {
        "updatedAt": iso_now(),
        "ollamaReachable": reachable,
        "evalOllamaReachable": eval_reachable,
        "evalOllamaUrl": "http://127.0.0.1:11435",
        "evalContainer": "clawstack-gemma4-eval",
        "gemma4Detected": has_any,
        "gemma4OnMainOllama": bool(gemma4_tags),
        "gemma4OnEvalOllama": has_eval,
        "detectedTags": all_gemma4,
        "detectedTagsMain": gemma4_tags,
        "detectedTagsEval": eval_gemma4_tags,
        "liteLLMOverlayReady": OVERLAY_PATH.exists(),
        "policyStatus": policy.get("status", "evaluation_only"),
        "policyMode": policy.get("mode", "ADOPT_PARTIAL"),
        "activationState": "eval_ready" if has_eval else ("ready_to_enable" if gemma4_tags else "ready_when_pulled"),
        "recommendedNextStep": (
            "python scripts/k10_gemma4_eval_next_step.py --bench"
            if has_eval
            else (
                "Run activate_gemma4_local_aliases.py after verifying Gemma4 tags on main Ollama."
                if gemma4_tags
                else "Start clawstack-gemma4-eval or pull gemma4:12b-it-qat on eval Ollama :11435."
            )
        ),
        "checks": attempts,
    }

    STATUS_PATH.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if has_any else 1


if __name__ == "__main__":
    raise SystemExit(main())
