#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "outbound_delivery_guard_status.json"
STATE_PATH = WORKSPACE / "outbound_delivery_guard_state.json"

ALLOWED_GMAIL_RECIPIENT = "y.suzuki.hk@gmail.com"
ALLOWED_TELEGRAM_CHAT_ID = "8173025084"


class OutboundPolicyError(RuntimeError):
    """Raised when an outbound delivery target violates the allowlist."""


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def _read_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _canonical_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _canonical_chat_id(value: str | int | None) -> str:
    return str(value or "").strip()


def _policy_snapshot() -> dict[str, Any]:
    return {
        "policyActive": True,
        "allowedChannels": ["telegram", "gmail"],
        "allowedGmailRecipient": ALLOWED_GMAIL_RECIPIENT,
        "allowedTelegramChatId": ALLOWED_TELEGRAM_CHAT_ID,
        "draftOnly": True,
        "externalAutoSendForbidden": True,
    }


def _record_attempt(channel: str, target: str, allowed: bool, source: str, detail: str | None = None) -> None:
    state = _read_json(
        STATE_PATH,
        {
            "allowedCount": 0,
            "blockedCount": 0,
            "lastAllowedAttempt": None,
            "lastBlockedAttempt": None,
        },
    )
    attempt = {
        "at": now_jst_text(),
        "channel": channel,
        "target": target,
        "allowed": allowed,
        "source": source,
    }
    if detail:
        attempt["detail"] = detail
    key = "lastAllowedAttempt" if allowed else "lastBlockedAttempt"
    count_key = "allowedCount" if allowed else "blockedCount"
    state[count_key] = int(state.get(count_key) or 0) + 1
    state[key] = attempt
    _write_json(STATE_PATH, state)

    status = _policy_snapshot()
    status.update(
        {
            "updatedAt": now_jst_text(),
            "allowedCount": state.get("allowedCount", 0),
            "blockedCount": state.get("blockedCount", 0),
            "lastAllowedAttempt": state.get("lastAllowedAttempt"),
            "lastBlockedAttempt": state.get("lastBlockedAttempt"),
        }
    )
    _write_json(STATUS_PATH, status)


def ensure_allowed_email(recipient: str, source: str) -> str:
    normalized = _canonical_email(recipient)
    allowed = normalized == _canonical_email(ALLOWED_GMAIL_RECIPIENT)
    _record_attempt("gmail", normalized or str(recipient), allowed, source)
    if not allowed:
        raise OutboundPolicyError(
            f"Outbound Gmail blocked for {source}: recipient '{recipient}' is not allowlisted."
        )
    return ALLOWED_GMAIL_RECIPIENT


def ensure_allowed_telegram_chat_id(chat_id: str | int, source: str) -> str:
    normalized = _canonical_chat_id(chat_id)
    allowed = normalized == ALLOWED_TELEGRAM_CHAT_ID
    _record_attempt("telegram", normalized or str(chat_id), allowed, source)
    if not allowed:
        raise OutboundPolicyError(
            f"Outbound Telegram blocked for {source}: chat_id '{chat_id}' is not allowlisted."
        )
    return ALLOWED_TELEGRAM_CHAT_ID


def initialize_guard_status(source: str = "startup") -> None:
    _record_attempt("system", "policy_loaded", True, source, "outbound delivery allowlist is active")
