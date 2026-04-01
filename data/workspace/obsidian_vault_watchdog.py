#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE = SCRIPT_PATH.parent
ROOT = WORKSPACE.parent.parent
VAULT_ROOT = ROOT / "data" / "state" / "Obsidian Vault" / "Clawstack_Project"
STATE_DIR = VAULT_ROOT / ".openclaw"
STATUS_PATH = WORKSPACE / "obsidian_vault_watchdog_status.json"
STATE_PATH = WORKSPACE / "obsidian_vault_watchdog_state.json"
HARNESS_STATUS_PATH = ROOT / "data" / "state" / "obsidian_vault_watchdog" / "harness_status.json"
INDEX_STATUS_PATH = STATE_DIR / "obsidian_index_status.json"
INDEX_SCRIPT = WORKSPACE / "obsidian_vault_manager.py"
NOTE_EXTENSIONS = {".md", ".markdown"}


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_status(status: dict[str, Any]) -> None:
    save_json(STATUS_PATH, status)
    save_json(
        HARNESS_STATUS_PATH,
        {
            "service": "obsidian_vault_watchdog",
            "updatedAt": now_jst().isoformat(),
            "pid": os.getpid(),
            "state": status.get("stage", "unknown"),
            "cycle": status.get("cycle", 0),
            "lastRebuildAt": status.get("lastRebuildAt"),
            "lastChangeAt": status.get("lastChangeAt"),
            "lastError": status.get("lastError"),
            "lastSummary": status.get("lastSummary", {}),
        },
    )


def vault_files() -> list[Path]:
    files: list[Path] = []
    if not VAULT_ROOT.exists():
        return files
    for path in VAULT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in NOTE_EXTENSIONS:
            continue
        if ".openclaw" in path.parts:
            continue
        files.append(path)
    return sorted(files)


def vault_snapshot() -> dict[str, Any]:
    items = []
    hasher = hashlib.sha256()
    for path in vault_files():
        rel = path.relative_to(VAULT_ROOT).as_posix()
        stat = path.stat()
        token = f"{rel}|{stat.st_mtime_ns}|{stat.st_size}"
        hasher.update(token.encode("utf-8", errors="replace"))
        items.append(
            {
                "path": rel,
                "modifiedAt": datetime.fromtimestamp(stat.st_mtime, JST).strftime("%Y-%m-%d %H:%M:%S JST"),
                "size": stat.st_size,
            }
        )
    latest = items[-1]["modifiedAt"] if items else None
    return {
        "hash": hasher.hexdigest(),
        "noteCount": len(items),
        "latestModifiedAt": latest,
        "notes": items[-20:],
    }


def run_command(command: list[str], timeout_seconds: int = 300) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "command": " ".join(command),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
        }


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S JST", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            if fmt.endswith("JST"):
                return datetime.strptime(raw, fmt).replace(tzinfo=JST)
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def read_index_status() -> dict[str, Any]:
    return load_json(INDEX_STATUS_PATH, {})


def rebuild_index() -> dict[str, Any]:
    result = run_command([sys.executable, str(INDEX_SCRIPT), "build-index"], timeout_seconds=300)
    parsed = {}
    try:
        parsed = json.loads(result.get("stdout") or "{}")
    except Exception:
        parsed = {}
    return {
        "commandResult": result,
        "indexSummary": {
            "generatedAt": parsed.get("generatedAt"),
            "noteCount": parsed.get("noteCount"),
        },
        "indexStatus": read_index_status(),
    }


def should_rebuild(previous_hash: str | None, current_hash: str, cooldown_seconds: int, last_rebuild_at: str | None) -> tuple[bool, str]:
    if previous_hash != current_hash:
        last_dt = parse_dt(last_rebuild_at)
        if last_dt is None:
            return True, "changed"
        age_seconds = (now_jst() - last_dt.astimezone(JST)).total_seconds()
        if age_seconds >= cooldown_seconds:
            return True, "changed"
        return False, "cooldown"
    return False, "no_change"


def run_loop(poll_seconds: int, cooldown_seconds: int) -> int:
    state = load_json(STATE_PATH, {})
    cycle = int(state.get("cycle", 0))
    while True:
        cycle += 1
        snapshot = vault_snapshot()
        previous_hash = state.get("lastVaultHash")
        last_rebuild_at = state.get("lastRebuildAt")
        rebuild, reason = should_rebuild(previous_hash, snapshot["hash"], cooldown_seconds, last_rebuild_at)
        status: dict[str, Any] = {
            "service": "obsidian_vault_watchdog",
            "updatedAt": now_jst_text(),
            "startedAt": state.get("startedAt") or now_jst_text(),
            "cycle": cycle,
            "stage": "idle",
            "vaultRoot": str(VAULT_ROOT),
            "noteCount": snapshot["noteCount"],
            "lastVaultHash": snapshot["hash"],
            "lastChangeAt": snapshot["latestModifiedAt"],
            "lastRebuildAt": last_rebuild_at,
            "lastSummary": {
                "decision": reason,
                "noteCount": snapshot["noteCount"],
            },
            "recentNotes": snapshot["notes"],
            "pollSeconds": poll_seconds,
            "cooldownSeconds": cooldown_seconds,
        }
        if rebuild:
            status["stage"] = "rebuilding"
            write_status(status)
            rebuild_result = rebuild_index()
            command_result = rebuild_result["commandResult"]
            if command_result.get("returncode") == 0 and not command_result.get("timedOut"):
                status["stage"] = "completed"
                status["lastError"] = None
                status["lastRebuildAt"] = now_jst_text()
                status["lastSummary"] = {
                    "decision": "rebuilt",
                    "noteCount": snapshot["noteCount"],
                    "indexSummary": rebuild_result.get("indexSummary", {}),
                }
            else:
                status["stage"] = "error"
                status["lastError"] = command_result.get("stderr") or command_result.get("stdout") or "index rebuild failed"
                status["lastSummary"] = {
                    "decision": "rebuild_failed",
                    "noteCount": snapshot["noteCount"],
                    "commandResult": command_result,
                }
            status["commandResult"] = command_result
            status["indexStatus"] = rebuild_result.get("indexStatus", {})
        write_status(status)
        state = {
            "startedAt": status["startedAt"],
            "cycle": cycle,
            "lastVaultHash": snapshot["hash"],
            "lastChangeAt": snapshot["latestModifiedAt"],
            "lastRebuildAt": status.get("lastRebuildAt"),
            "lastError": status.get("lastError"),
        }
        save_json(STATE_PATH, state)
        time.sleep(max(15, poll_seconds))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Watch the shared Obsidian vault and rebuild index when notes change.")
    parser.add_argument("--poll-seconds", type=int, default=180)
    parser.add_argument("--cooldown-seconds", type=int, default=90)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    initial = {
        "service": "obsidian_vault_watchdog",
        "updatedAt": now_jst_text(),
        "startedAt": now_jst_text(),
        "stage": "starting",
        "vaultRoot": str(VAULT_ROOT),
        "pollSeconds": args.poll_seconds,
        "cooldownSeconds": args.cooldown_seconds,
    }
    write_status(initial)
    return run_loop(args.poll_seconds, args.cooldown_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
