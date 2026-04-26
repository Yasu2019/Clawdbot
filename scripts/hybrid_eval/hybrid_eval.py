import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_STATUS_PATH = Path("hybrid_eval_harness.json")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def update_status(status_path: Path, status: str, message: str, **extra) -> None:
    payload = {
        "status": status,
        "message": message,
        "last_updated": time.time(),
        **extra,
    }
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    if args.prompt is not None:
        return args.prompt
    return sys.stdin.read()


def http_post_json(url: str, body: dict, timeout_sec: int) -> dict:
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


def run_ollama_generate(
    ollama_url: str,
    model: str,
    prompt: str,
    timeout_sec: int,
    temperature: float | None,
    num_predict: int | None,
    think: bool | None,
) -> dict:
    url = f"{ollama_url.rstrip('/')}/api/generate"
    body: dict = {"model": model, "prompt": prompt, "stream": False}
    if think is not None:
        body["think"] = bool(think)
    options: dict = {}
    if temperature is not None:
        options["temperature"] = temperature
    if num_predict is not None:
        options["num_predict"] = num_predict
    if options:
        body["options"] = options
    return http_post_json(url, body, timeout_sec=timeout_sec)


def run_foundry_cmd(cmd: list[str], prompt: str, timeout_sec: int) -> dict:
    started = time.time()
    proc = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    elapsed = time.time() - started
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "elapsed_sec": elapsed,
    }


def write_run_files(out_dir: Path, files: dict[str, str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out_dir / name).write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid eval harness: Ollama primary + optional Foundry comparison")
    parser.add_argument("--prompt", default=None, help="Prompt text. If omitted, reads stdin unless --prompt-file is set.")
    parser.add_argument("--prompt-file", default=None, help="UTF-8 text file containing the prompt.")
    parser.add_argument("--out-root", default="tmp/hybrid_eval", help="Output root directory for runs.")
    parser.add_argument("--status-file", default=str(DEFAULT_STATUS_PATH), help="Status JSON path (progress/last run).")

    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--ollama-model", default=os.getenv("OLLAMA_MODEL", ""), help="Required if OLLAMA_MODEL not set.")
    parser.add_argument("--ollama-timeout", type=int, default=int(os.getenv("OLLAMA_TIMEOUT", "60")))
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--num-predict", type=int, default=None, help="Max tokens to generate (Ollama num_predict).")
    think_group = parser.add_mutually_exclusive_group()
    think_group.add_argument("--think", dest="think", action="store_true", help="Enable model thinking output (if supported).")
    think_group.add_argument("--no-think", dest="think", action="store_false", help="Disable thinking output (if supported).")
    parser.set_defaults(think=None)

    parser.add_argument(
        "--foundry-cmd",
        nargs=argparse.REMAINDER,
        help="Optional command to run Foundry comparison. Prompt is sent via stdin. Example: --foundry-cmd python scripts/foundry_wrapper.py",
    )
    parser.add_argument("--foundry-timeout", type=int, default=int(os.getenv("FOUNDRY_TIMEOUT", "90")))

    args = parser.parse_args()

    status_path = Path(args.status_file)
    prompt = read_prompt(args).strip("\ufeff").rstrip()
    if not prompt:
        print("Error: empty prompt (provide --prompt / --prompt-file / stdin).", file=sys.stderr)
        return 2
    if not args.ollama_model:
        print("Error: --ollama-model is required (or set OLLAMA_MODEL).", file=sys.stderr)
        return 2

    run_id = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    out_dir = Path(args.out_root) / run_id
    prompt_hash = _sha256_text(prompt)

    update_status(status_path, "running", "Starting hybrid eval", run_id=run_id, out_dir=str(out_dir))

    meta = {
        "run_id": run_id,
        "created_at": _now_iso(),
        "prompt_sha256": prompt_hash,
        "ollama": {
            "url": args.ollama_url,
            "model": args.ollama_model,
            "timeout_sec": args.ollama_timeout,
            "temperature": args.temperature,
            "num_predict": args.num_predict,
            "think": args.think,
        },
        "foundry": {
            "enabled": bool(args.foundry_cmd),
            "cmd": args.foundry_cmd or [],
            "timeout_sec": args.foundry_timeout,
        },
    }

    ollama_result: dict
    foundry_result: dict

    try:
        update_status(status_path, "running", "Calling Ollama", run_id=run_id)
        started = time.time()
        ollama_result = run_ollama_generate(
            ollama_url=args.ollama_url,
            model=args.ollama_model,
            prompt=prompt,
            timeout_sec=args.ollama_timeout,
            temperature=args.temperature,
            num_predict=args.num_predict,
            think=args.think,
        )
        meta["ollama"]["elapsed_sec"] = time.time() - started
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
        update_status(status_path, "failed", f"Ollama call failed: {type(e).__name__}: {e}", run_id=run_id)
        ollama_result = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    if args.foundry_cmd:
        try:
            update_status(status_path, "running", "Calling Foundry command", run_id=run_id)
            foundry_result = run_foundry_cmd(args.foundry_cmd, prompt=prompt, timeout_sec=args.foundry_timeout)
        except subprocess.TimeoutExpired as e:
            foundry_result = {
                "ok": False,
                "error": f"TimeoutExpired: {e}",
                "returncode": None,
                "stdout": e.stdout or "",
                "stderr": e.stderr or "",
            }
        except Exception as e:
            foundry_result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    else:
        foundry_result = {"ok": None, "skipped": True, "reason": "No --foundry-cmd provided"}

    ollama_text = ""
    if isinstance(ollama_result, dict):
        ollama_text = str(ollama_result.get("response", "")) if ollama_result.get("response") is not None else ""
    foundry_text = ""
    if isinstance(foundry_result, dict) and foundry_result.get("stdout"):
        foundry_text = str(foundry_result.get("stdout", ""))

    comparison_md = "\n".join(
        [
            "# Hybrid Eval Run",
            "",
            f"- run_id: {run_id}",
            f"- created_at: {meta['created_at']}",
            f"- prompt_sha256: `{prompt_hash}`",
            f"- ollama_model: `{args.ollama_model}`",
            f"- foundry_enabled: `{bool(args.foundry_cmd)}`",
            "",
            "## Quick Stats",
            f"- ollama_chars: {len(ollama_text)}",
            f"- foundry_chars: {len(foundry_text)}",
            "",
            "## Human Scoring (fill in)",
            "- correctness: ",
            "- relevance: ",
            "- safety: ",
            "- edit_effort: ",
            "- notes: ",
            "",
        ]
    )

    write_run_files(
        out_dir,
        {
            "input_prompt.txt": prompt + "\n",
            "run_meta.json": json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            "ollama_raw.json": json.dumps(ollama_result, ensure_ascii=False, indent=2) + "\n",
            "foundry_raw.json": json.dumps(foundry_result, ensure_ascii=False, indent=2) + "\n",
            "comparison.md": comparison_md,
        },
    )

    update_status(status_path, "done", "Hybrid eval complete", run_id=run_id, out_dir=str(out_dir))

    print(str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
