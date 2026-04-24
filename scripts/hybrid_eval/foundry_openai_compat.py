import argparse
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return open(args.prompt_file, "r", encoding="utf-8").read()
    if args.prompt is not None:
        return args.prompt
    return sys.stdin.read()


def _post_json(url: str, body: dict, timeout_sec: int) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = Request(
        url=url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _get_json(url: str, timeout_sec: int) -> dict:
    req = Request(url=url, headers={"Accept": "application/json"}, method="GET")
    with urlopen(req, timeout=timeout_sec) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Foundry (OpenAI-compatible) wrapper: stdin prompt -> stdout text. Intended for hybrid_eval.py --foundry-cmd."
    )
    parser.add_argument("--base-url", default=os.getenv("FOUNDRY_BASE_URL", ""), help="Example: http://127.0.0.1:8000/v1")
    parser.add_argument("--api-key", default=os.getenv("FOUNDRY_API_KEY", "dummy"))
    parser.add_argument("--model", default=os.getenv("FOUNDRY_MODEL", ""), help="Model name/id for /v1/chat/completions")
    parser.add_argument("--timeout", type=int, default=int(os.getenv("FOUNDRY_TIMEOUT", "90")))
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--prompt-file", default=None)
    parser.add_argument("--system", default="日本語で回答。余計な説明は付けず、完成文だけ出してください。")
    parser.add_argument("--verify-model", action="store_true", help="Try GET /v1/models and exit with 0/2.")
    args = parser.parse_args()

    if not args.base_url:
        print("Error: --base-url is required (or set FOUNDRY_BASE_URL).", file=sys.stderr)
        return 2

    base = args.base_url.rstrip("/")

    if args.verify_model:
        try:
            _get_json(f"{base}/models", timeout_sec=args.timeout)
            return 0
        except Exception as e:
            print(f"verify-model failed: {type(e).__name__}: {e}", file=sys.stderr)
            return 2

    prompt = _read_prompt(args).strip("\ufeff").rstrip()
    if not prompt:
        print("Error: empty prompt.", file=sys.stderr)
        return 2
    if not args.model:
        print("Error: --model is required (or set FOUNDRY_MODEL).", file=sys.stderr)
        return 2

    body = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {args.api_key}"}

    started = time.time()
    try:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = Request(
            url=f"{base}/chat/completions",
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8", **headers},
            method="POST",
        )
        with urlopen(req, timeout=args.timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        obj = json.loads(raw)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"Error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    _elapsed = time.time() - started

    content = ""
    try:
        content = obj["choices"][0]["message"]["content"] or ""
    except Exception:
        content = ""

    if not content:
        print("Error: empty content in response.", file=sys.stderr)
        return 1

    sys.stdout.write(content.strip() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

