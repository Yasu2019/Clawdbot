from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data" / "workspace" / "iatf_opencode_go_preflight_status.json"


def load_root_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def chat(base_url: str, key: str, model: str, timeout: int) -> dict:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": 'Return exactly JSON: {"ok":true,"route":"opencode-go"}',
            }
        ],
        "max_tokens": 128,
        "temperature": 0,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
        data = json.loads(body)
        message = ((data.get("choices") or [{}])[0].get("message") or {})
        content = message.get("content") or ""
        return {
            "ok": bool(content.strip()),
            "status": "ok" if content.strip() else "empty_content",
            "elapsed_sec": round(time.time() - started, 2),
            "content_sample": content[:120],
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return {
            "ok": False,
            "status": f"http_{exc.code}",
            "elapsed_sec": round(time.time() - started, 2),
            "error": body[:500],
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": type(exc).__name__,
            "elapsed_sec": round(time.time() - started, 2),
            "error": str(exc)[:500],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="IATF OpenCode GO routing preflight")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--include-direct", action="store_true")
    args = parser.parse_args()

    load_root_env()
    litellm_base = os.getenv("LITELLM_URL", "http://localhost:4001").rstrip("/") + "/v1"
    litellm_key = os.getenv("LITELLM_MASTER_KEY", "local-dev-key")
    opencode_base = os.getenv("OPENCODE_GO_API_BASE", "").rstrip("/")
    opencode_key = os.getenv("OPENCODE_GO_API_KEY", "")

    models = [
        "opencode-go/kimi-k2.6",
        "opencode-go/deepseek-v4-flash",
        "opencode-go/deepseek-v4-pro",
    ]
    results: dict[str, object] = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "litellm_base": litellm_base,
        "opencode_env_present": bool(opencode_base and opencode_key),
        "tests": {},
    }

    tests = results["tests"]
    assert isinstance(tests, dict)
    for model in models:
        tests["litellm:" + model] = chat(litellm_base, litellm_key, model, args.timeout)

    if args.include_direct and opencode_base and opencode_key:
        for model in ["kimi-k2.6", "deepseek-v4-flash", "deepseek-v4-pro"]:
            tests["direct:" + model] = chat(opencode_base, opencode_key, model, args.timeout)

    usable = [name for name, result in tests.items() if isinstance(result, dict) and result.get("ok")]
    results["ok"] = bool(usable)
    results["usable_routes"] = usable

    STATUS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if usable else 2


if __name__ == "__main__":
    raise SystemExit(main())
