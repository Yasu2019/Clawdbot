#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()


def detect_root() -> Path:
    env_root = os.environ.get("CLAWDBOT_REPO_ROOT")
    candidates: list[Path] = []
    if env_root:
        candidates.append(Path(env_root))
    cwd = Path.cwd()
    candidates.append(cwd)
    candidates.extend(cwd.parents)
    candidates.append(SCRIPT_PATH.parent)
    candidates.extend(SCRIPT_PATH.parents)

    for candidate in candidates:
        if (candidate / "AGENTS.md").exists() and (candidate / "docs" / "INCIDENT_LOG.md").exists():
            return candidate
    return cwd


ROOT = detect_root()
WORKSPACE = ROOT / "data" / "workspace"

CLAUDIAN_ROOT = ROOT / "data" / "state" / "Obsidian Vault"
PLUGIN_DIR = CLAUDIAN_ROOT / ".obsidian" / "plugins" / "claudian"
SETTINGS_PATH = CLAUDIAN_ROOT / ".claudian" / "claudian-settings.json"
PLUGIN_DATA_PATH = PLUGIN_DIR / "data.json"
EXPECTED_CLI_PATH = PLUGIN_DIR / "codex.cmd"
EXPECTED_BRIDGE_PATH = PLUGIN_DIR / "codex_bridge.js"

DEBUG_DIR = Path.home() / ".claude" / "debug"
SPAWN_LOG_PATH = DEBUG_DIR / "claudian-spawn.log"
BRIDGE_LOG_PATH = DEBUG_DIR / "claudian-bridge.log"

STATUS_PATH = WORKSPACE / "claudian_watchdog_status.json"
STATE_PATH = WORKSPACE / "claudian_watchdog_state.json"
HARNESS_STATUS_PATH = ROOT / "data" / "state" / "claudian_watchdog" / "harness_status.json"

SETTINGS_ERROR_PATTERNS = [
    "spawn EINVAL",
    "Cannot read properties of undefined (reading 'id')",
    "model 'openai/qwen3:8b' not found",
]


def now_jst() -> datetime:
    return datetime.now(JST)


def now_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


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


def load_json(path: Path, fallback: dict[str, Any] | list[Any] | None = None) -> Any:
    if fallback is None:
        fallback = {}
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
            "service": "claudian_watchdog",
            "updatedAt": now_jst().isoformat(),
            "pid": os.getpid(),
            "state": status.get("stage", "unknown"),
            "cycle": status.get("cycle", 0),
            "lastSummary": status.get("summary"),
            "lastError": status.get("lastError"),
        },
    )


def age_minutes(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    delta = now_jst().astimezone(dt.tzinfo) - dt
    return round(delta.total_seconds() / 60.0, 1)


def is_recent(dt: datetime | None, max_age_minutes: int) -> bool:
    age = age_minutes(dt)
    return age is not None and age <= max_age_minutes


def tail_lines(path: Path, max_lines: int = 400) -> list[str]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
        return [line.rstrip("\r\n") for line in lines[-max_lines:]]
    except Exception:
        return []


def parse_log_line(line: str) -> tuple[datetime | None, str]:
    if " " not in line:
        return None, line
    ts_text, body = line.split(" ", 1)
    return parse_dt(ts_text), body


def extract_env_map(raw: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    if not raw:
        return result
    for line in raw.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def normalize_path_text(path: Path | str) -> str:
    return str(path).replace("/", "\\").lower()


def check_settings() -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    status = "healthy"

    settings = load_json(SETTINGS_PATH, {})
    plugin_data = load_json(PLUGIN_DATA_PATH, {})

    if not SETTINGS_PATH.exists():
        findings.append({"severity": "error", "message": "authoritative claudian-settings.json is missing"})
        status = "error"
    if not PLUGIN_DATA_PATH.exists():
        findings.append({"severity": "warning", "message": "plugin data.json is missing"})
        if status != "error":
            status = "warning"

    codex_cfg = ((settings.get("providerConfigs") or {}).get("codex") or {}) if isinstance(settings, dict) else {}
    plugin_codex_cfg = ((plugin_data.get("providers") or {}).get("codex") or {}) if isinstance(plugin_data, dict) else {}

    cli_path_text = str(codex_cfg.get("cliPath") or "")
    plugin_cli_path_text = str(plugin_codex_cfg.get("cliPath") or "")
    cli_path = Path(cli_path_text) if cli_path_text else Path()
    plugin_cli_path = Path(plugin_cli_path_text) if plugin_cli_path_text else Path()
    env_map = extract_env_map(codex_cfg.get("environmentVariables"))
    plugin_env_map = extract_env_map(plugin_codex_cfg.get("environmentVariables"))

    if normalize_path_text(cli_path_text) != normalize_path_text(EXPECTED_CLI_PATH):
        findings.append({"severity": "error", "message": f"settings cliPath mismatch: {cli_path}"})
        status = "error"
    elif not cli_path.exists():
        findings.append({"severity": "error", "message": f"configured cliPath is missing: {cli_path}"})
        status = "error"

    if plugin_cli_path_text and normalize_path_text(plugin_cli_path_text) != normalize_path_text(EXPECTED_CLI_PATH):
        findings.append({"severity": "warning", "message": f"plugin data cliPath mismatch: {plugin_cli_path}"})
        if status != "error":
            status = "warning"

    if not EXPECTED_BRIDGE_PATH.exists():
        findings.append({"severity": "error", "message": "bundled codex_bridge.js is missing"})
        status = "error"

    expected_env = {
        "OPENAI_BASE_URL": "http://127.0.0.1:11434/v1",
        "OPENAI_API_KEY": "ollama",
        "OPENAI_MODEL": "qwen3:8b",
    }
    for key, expected in expected_env.items():
        actual = env_map.get(key)
        if actual != expected:
            findings.append({"severity": "error", "message": f"{key} mismatch: {actual!r}"})
            status = "error"
        plugin_actual = plugin_env_map.get(key)
        if plugin_actual and plugin_actual != expected:
            findings.append({"severity": "warning", "message": f"plugin data {key} mismatch: {plugin_actual!r}"})
            if status != "error":
                status = "warning"

    path_value = env_map.get("PATH", "")
    if path_value and normalize_path_text(PLUGIN_DIR) not in normalize_path_text(path_value):
        findings.append({"severity": "warning", "message": "PATH does not include the plugin directory"})
        if status != "error":
            status = "warning"

    return {
        "name": "settings_consistency",
        "status": status,
        "findings": findings,
        "cliPath": str(cli_path) if cli_path else "",
        "bridgePath": str(EXPECTED_BRIDGE_PATH),
        "environment": env_map,
    }


def check_spawn_log() -> dict[str, Any]:
    lines = tail_lines(SPAWN_LOG_PATH, max_lines=250)
    last_einval: datetime | None = None
    last_good_spawn: datetime | None = None
    last_configured_path: datetime | None = None

    for line in lines:
        ts, body = parse_log_line(line)
        if ts is None:
            continue
        if 'spawn throw code="EINVAL"' in body:
            last_einval = ts
        if 'spawn attempt command="' in body and 'node.exe"' in body and 'codex_bridge.js' in body:
            last_good_spawn = ts
        if "resolveCodexCliPath configured" in body:
            last_configured_path = ts

    findings: list[dict[str, str]] = []
    status = "healthy"

    if not SPAWN_LOG_PATH.exists():
        findings.append({"severity": "warning", "message": "spawn log is missing"})
        status = "warning"
    elif last_einval and (last_good_spawn is None or last_einval > last_good_spawn):
        findings.append({"severity": "error", "message": "latest spawn failure is still spawn EINVAL"})
        status = "error"
    elif last_einval:
        findings.append({"severity": "info", "message": "historical spawn EINVAL detected but later good node spawn recovered"})

    if SPAWN_LOG_PATH.exists() and last_configured_path is None:
        findings.append({"severity": "warning", "message": "configured cliPath was not observed in recent spawn log lines"})
        if status != "error":
            status = "warning"

    return {
        "name": "spawn_path_resolution",
        "status": status,
        "findings": findings,
        "logPath": str(SPAWN_LOG_PATH),
        "lastSpawnEinvalAt": last_einval.isoformat() if last_einval else None,
        "lastGoodNodeSpawnAt": last_good_spawn.isoformat() if last_good_spawn else None,
        "lastConfiguredResolverAt": last_configured_path.isoformat() if last_configured_path else None,
        "logAgeMinutes": age_minutes(datetime.fromtimestamp(SPAWN_LOG_PATH.stat().st_mtime, timezone.utc)) if SPAWN_LOG_PATH.exists() else None,
    }


def parse_bridge_rpc(lines: list[str]) -> dict[str, Any]:
    pending_request_times: dict[Any, datetime] = {}
    turn_started_at: dict[str, datetime] = {}
    turn_completed: dict[str, dict[str, Any]] = {}
    last_turn_start_in: datetime | None = None
    last_completed_ts: datetime | None = None
    last_failed_ts: datetime | None = None
    latest_nonempty_reply: datetime | None = None
    latest_empty_reply: datetime | None = None
    latest_undefined_id: datetime | None = None
    latest_model_not_found: datetime | None = None
    latest_connection_error: datetime | None = None

    for line in lines:
        ts, body = parse_log_line(line)
        if ts is None:
            continue
        if "Cannot read properties of undefined (reading 'id')" in body:
            latest_undefined_id = ts
        if "model 'openai/qwen3:8b' not found" in body:
            latest_model_not_found = ts
        if "connection failed" in body.lower():
            latest_connection_error = ts

        payload_text = None
        direction = None
        if body.startswith("IN: "):
            payload_text = body[4:]
            direction = "IN"
        elif body.startswith("OUT: "):
            payload_text = body[5:]
            direction = "OUT"
        else:
            continue

        try:
            payload = json.loads(payload_text)
        except Exception:
            continue

        if direction == "IN":
            req_id = payload.get("id")
            method = payload.get("method")
            if req_id is not None:
                pending_request_times[req_id] = ts
            if method == "turn/start":
                last_turn_start_in = ts
        elif direction == "OUT":
            req_id = payload.get("id")
            if req_id is not None and "result" in payload:
                started_at = pending_request_times.get(req_id)
                turn_id = ((payload.get("result") or {}).get("turn") or {}).get("id")
                if started_at and turn_id:
                    turn_started_at[turn_id] = started_at

            method = payload.get("method")
            params = payload.get("params") or {}
            if method == "turn/completed":
                turn = params.get("turn") or {}
                turn_id = turn.get("id")
                turn_completed[turn_id] = {"completedAt": ts, "status": turn.get("status")}
                if turn.get("status") == "completed":
                    last_completed_ts = ts
                elif turn.get("status") == "failed":
                    last_failed_ts = ts
            elif method == "item/agentMessage/delta":
                delta = str(params.get("delta") or "")
                if delta.strip():
                    latest_nonempty_reply = ts
                else:
                    latest_empty_reply = ts

    latency_samples: list[float] = []
    pending_turns: list[dict[str, Any]] = []
    for turn_id, started_at in turn_started_at.items():
        completed = turn_completed.get(turn_id)
        if completed:
            latency_seconds = round((completed["completedAt"] - started_at).total_seconds(), 1)
            latency_samples.append(latency_seconds)
        else:
            pending_turns.append(
                {
                    "turnId": turn_id,
                    "startedAt": started_at.isoformat(),
                    "ageMinutes": age_minutes(started_at),
                }
            )

    return {
        "lastTurnStartAt": last_turn_start_in,
        "lastCompletedAt": last_completed_ts,
        "lastFailedAt": last_failed_ts,
        "latestNonEmptyReplyAt": latest_nonempty_reply,
        "latestEmptyReplyAt": latest_empty_reply,
        "latestUndefinedIdAt": latest_undefined_id,
        "latestModelNotFoundAt": latest_model_not_found,
        "latestConnectionErrorAt": latest_connection_error,
        "latencySamples": latency_samples[-20:],
        "pendingTurns": pending_turns,
    }


def check_bridge_log(stale_turn_minutes: int, active_window_minutes: int) -> dict[str, Any]:
    lines = tail_lines(BRIDGE_LOG_PATH, max_lines=500)
    parsed = parse_bridge_rpc(lines)
    findings: list[dict[str, str]] = []
    status = "healthy"

    if not BRIDGE_LOG_PATH.exists():
        findings.append({"severity": "warning", "message": "bridge log is missing"})
        status = "warning"
        return {
            "name": "bridge_protocol_health",
            "status": status,
            "findings": findings,
            "logPath": str(BRIDGE_LOG_PATH),
        }

    recent_activity = any(
        is_recent(parsed[key], active_window_minutes)
        for key in ("lastTurnStartAt", "lastCompletedAt", "lastFailedAt", "latestNonEmptyReplyAt")
    )

    if recent_activity and parsed["latestUndefinedIdAt"] and (
        parsed["lastCompletedAt"] is None or parsed["latestUndefinedIdAt"] > parsed["lastCompletedAt"]
    ):
        findings.append({"severity": "error", "message": "latest bridge failure includes undefined.id contract break"})
        status = "error"

    if recent_activity and parsed["latestModelNotFoundAt"] and (
        parsed["latestNonEmptyReplyAt"] is None or parsed["latestModelNotFoundAt"] > parsed["latestNonEmptyReplyAt"]
    ):
        findings.append({"severity": "error", "message": "latest backend error is model not found"})
        status = "error"

    if recent_activity and parsed["latestConnectionErrorAt"] and (
        parsed["lastCompletedAt"] is None or parsed["latestConnectionErrorAt"] > parsed["lastCompletedAt"]
    ):
        findings.append({"severity": "error", "message": "latest backend error is a connection failure"})
        status = "error"

    latest_empty_reply = parsed["latestEmptyReplyAt"]
    latest_nonempty_reply = parsed["latestNonEmptyReplyAt"]
    if latest_empty_reply and (latest_nonempty_reply is None or latest_empty_reply > latest_nonempty_reply):
        findings.append({"severity": "warning", "message": "latest assistant delta was empty"})
        if status != "error":
            status = "warning"

    stale_pending = [
        item for item in parsed["pendingTurns"]
        if item["ageMinutes"] is not None and item["ageMinutes"] >= stale_turn_minutes
    ]
    if recent_activity and stale_pending:
        findings.append({"severity": "warning", "message": f"{len(stale_pending)} pending turn(s) exceeded {stale_turn_minutes} minutes"})
        if status != "error":
            status = "warning"

    latencies = parsed["latencySamples"]
    if recent_activity and latencies:
        worst_latency = max(latencies)
        if worst_latency >= 120:
            findings.append({"severity": "warning", "message": f"recent bridge latency reached {worst_latency:.1f}s"})
            if status != "error":
                status = "warning"

    if not findings:
        if recent_activity:
            findings.append({"severity": "info", "message": "recent bridge RPC flow has completed turns and no active contract errors"})
        else:
            findings.append({"severity": "info", "message": "bridge logs are quiet; no recent Claudian activity to evaluate"})

    return {
        "name": "bridge_protocol_health",
        "status": status,
        "findings": findings,
        "logPath": str(BRIDGE_LOG_PATH),
        "lastTurnStartAt": parsed["lastTurnStartAt"].isoformat() if parsed["lastTurnStartAt"] else None,
        "lastCompletedAt": parsed["lastCompletedAt"].isoformat() if parsed["lastCompletedAt"] else None,
        "lastFailedAt": parsed["lastFailedAt"].isoformat() if parsed["lastFailedAt"] else None,
        "latestNonEmptyReplyAt": parsed["latestNonEmptyReplyAt"].isoformat() if parsed["latestNonEmptyReplyAt"] else None,
        "latestEmptyReplyAt": parsed["latestEmptyReplyAt"].isoformat() if parsed["latestEmptyReplyAt"] else None,
        "pendingTurns": parsed["pendingTurns"][:10],
        "recentLatenciesSeconds": latencies[-10:],
    }


def derive_ollama_tags_url(base_url: str) -> str:
    if "/v1" in base_url:
        return base_url.split("/v1", 1)[0].rstrip("/") + "/api/tags"
    return base_url.rstrip("/") + "/api/tags"


def check_ollama_model(activity_is_recent: bool) -> dict[str, Any]:
    settings = load_json(SETTINGS_PATH, {})
    codex_cfg = ((settings.get("providerConfigs") or {}).get("codex") or {}) if isinstance(settings, dict) else {}
    env_map = extract_env_map(codex_cfg.get("environmentVariables"))
    base_url = env_map.get("OPENAI_BASE_URL") or "http://127.0.0.1:11434/v1"
    model_name = env_map.get("OPENAI_MODEL") or "qwen3:8b"
    tags_url = derive_ollama_tags_url(base_url)

    findings: list[dict[str, str]] = []
    status = "healthy"
    installed_models: list[str] = []

    try:
        req = urllib.request.Request(tags_url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        installed_models = [
            str(item.get("name") or "")
            for item in (payload.get("models") or [])
            if isinstance(item, dict)
        ]
        if model_name not in installed_models:
            findings.append({"severity": "error", "message": f"required Ollama model is missing: {model_name}"})
            status = "error"
    except urllib.error.URLError as exc:
        severity = "error" if activity_is_recent else "warning"
        findings.append({"severity": severity, "message": f"Ollama tags endpoint unreachable: {exc}"})
        status = "error" if activity_is_recent else "warning"
    except Exception as exc:
        severity = "error" if activity_is_recent else "warning"
        findings.append({"severity": severity, "message": f"failed to inspect Ollama models: {exc}"})
        status = "error" if activity_is_recent else "warning"

    if not findings:
        findings.append({"severity": "info", "message": f"Ollama model is available: {model_name}"})

    return {
        "name": "ollama_model_availability",
        "status": status,
        "findings": findings,
        "baseUrl": base_url,
        "tagsUrl": tags_url,
        "model": model_name,
        "installedModels": installed_models[:20],
    }


def summarize_checks(checks: list[dict[str, Any]]) -> tuple[str, str | None]:
    if any(check["status"] == "error" for check in checks):
        return "error", "at least one Claudian guardrail check is failing"
    if any(check["status"] == "warning" for check in checks):
        return "warning", "Claudian is running but there are early warning signals"
    return "healthy", None


def build_status(cycle: int, stale_turn_minutes: int) -> dict[str, Any]:
    settings_check = check_settings()
    spawn_check = check_spawn_log()
    bridge_check = check_bridge_log(stale_turn_minutes=stale_turn_minutes, active_window_minutes=60)
    bridge_recent = bool(
        bridge_check.get("lastTurnStartAt")
        and is_recent(parse_dt(bridge_check.get("lastTurnStartAt")), 60)
    ) or bool(
        bridge_check.get("lastCompletedAt")
        and is_recent(parse_dt(bridge_check.get("lastCompletedAt")), 60)
    )
    ollama_check = check_ollama_model(activity_is_recent=bridge_recent)
    checks = [
        settings_check,
        spawn_check,
        bridge_check,
        ollama_check,
    ]
    stage, last_error = summarize_checks(checks)
    findings = [
        {"check": check["name"], **finding}
        for check in checks
        for finding in check.get("findings", [])
        if finding.get("severity") in {"error", "warning"}
    ]
    summary = {
        "healthyChecks": sum(1 for check in checks if check["status"] == "healthy"),
        "warningChecks": sum(1 for check in checks if check["status"] == "warning"),
        "errorChecks": sum(1 for check in checks if check["status"] == "error"),
        "findingCount": len(findings),
    }
    return {
        "service": "claudian_watchdog",
        "updatedAt": now_text(),
        "cycle": cycle,
        "stage": stage,
        "summary": summary,
        "lastError": last_error,
        "checks": checks,
        "findings": findings,
        "watchTargets": {
            "settings": str(SETTINGS_PATH),
            "pluginData": str(PLUGIN_DATA_PATH),
            "spawnLog": str(SPAWN_LOG_PATH),
            "bridgeLog": str(BRIDGE_LOG_PATH),
        },
    }


def run_once(cycle: int, stale_turn_minutes: int) -> dict[str, Any]:
    status = build_status(cycle=cycle, stale_turn_minutes=stale_turn_minutes)
    write_status(status)
    save_json(
        STATE_PATH,
        {
            "updatedAt": status["updatedAt"],
            "cycle": cycle,
            "stage": status["stage"],
            "findingCount": status["summary"]["findingCount"],
        },
    )
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect recurring Claudian startup, bridge, and model-routing failures.")
    parser.add_argument("--poll-seconds", type=int, default=180)
    parser.add_argument("--stale-turn-minutes", type=int, default=2)
    parser.add_argument("--once", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    previous = load_json(STATE_PATH, {})
    cycle = int(previous.get("cycle", 0))

    if args.once:
        cycle += 1
        status = run_once(cycle=cycle, stale_turn_minutes=args.stale_turn_minutes)
        print(json.dumps(status, ensure_ascii=False))
        return 0

    while True:
        cycle += 1
        run_once(cycle=cycle, stale_turn_minutes=args.stale_turn_minutes)
        time.sleep(max(30, args.poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
