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
DEFAULT_LITELLM_BASES = (
    "http://localhost:4000/v1",
    "http://localhost:4001/v1",
)


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
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
            "User-Agent": "OpenCode/1.0" if "opencode.ai" in base_url else "IATF-OpenCodeGo-Preflight/1.0",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
        data = json.loads(body)
        message = ((data.get("choices") or [{}])[0].get("message") or {})
        content = message.get("content") or ""
        reasoning = message.get("reasoning_content") or ""
        has_response = bool(content.strip() or reasoning.strip())
        return {
            "ok": has_response,
            "status": "ok" if has_response else "empty_content",
            "elapsed_sec": round(time.time() - started, 2),
            "content_sample": content[:120],
            "model": data.get("model"),
            "usage": data.get("usage"),
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
    parser.add_argument("--require-litellm", action="store_true")
    parser.add_argument("--all-models", action="store_true")
    parser.add_argument("--direct-only", action="store_true")
    args = parser.parse_args()

    load_root_env()
    configured_litellm = os.getenv("LITELLM_URL", "").rstrip("/")
    litellm_bases = []
    if configured_litellm:
        litellm_bases.append(configured_litellm + ("" if configured_litellm.endswith("/v1") else "/v1"))
    for base in DEFAULT_LITELLM_BASES:
        if base not in litellm_bases:
            litellm_bases.append(base)
    litellm_key = os.getenv("LITELLM_MASTER_KEY", "local-dev-key")
    opencode_base = os.getenv("OPENCODE_GO_API_BASE", "").rstrip("/")
    opencode_key = os.getenv("OPENCODE_GO_API_KEY", "")

    models = [
        "opencode-go/kimi-k2.6",
        "opencode-go/deepseek-v4-flash",
        "opencode-go/deepseek-v4-pro",
    ] if args.all_models else ["opencode-go/deepseek-v4-flash"]
    results: dict[str, object] = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "litellm_bases": litellm_bases,
        "opencode_env_present": bool(opencode_base and opencode_key),
        "require_litellm": args.require_litellm,
        "tests": {},
    }

    tests = results["tests"]
    assert isinstance(tests, dict)
    if not args.direct_only:
        for base in litellm_bases:
            for model in models:
                tests[f"litellm:{base}:{model}"] = chat(base, litellm_key, model, args.timeout)

    if (args.include_direct or args.direct_only) and opencode_base and opencode_key:
        direct_models = ["kimi-k2.6", "deepseek-v4-flash", "deepseek-v4-pro"] if args.all_models else ["deepseek-v4-flash"]
        for model in direct_models:
            tests["direct:" + model] = chat(opencode_base, opencode_key, model, args.timeout)

    usable = [name for name, result in tests.items() if isinstance(result, dict) and result.get("ok")]
    usable_litellm = [name for name in usable if name.startswith("litellm:")]
    results["ok"] = bool(usable_litellm if args.require_litellm else usable)
    results["usable_routes"] = usable
    results["usable_litellm_routes"] = usable_litellm

    STATUS_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
