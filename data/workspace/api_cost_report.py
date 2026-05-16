from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "data" / "workspace"
STATUS_JSON = WORKSPACE / "api_cost_report_status.json"
STATUS_MD = WORKSPACE / "api_cost_report_status.md"


PROVIDERS = [
    {
        "id": "openai",
        "label": "OpenAI",
        "keys": ["OPENAI_API_KEY"],
        "limit_keys": ["OPENAI_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "anthropic",
        "label": "Anthropic / Claude",
        "keys": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "limit_keys": ["ANTHROPIC_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "gemini",
        "label": "Google Gemini",
        "keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "limit_keys": ["GEMINI_MONTHLY_LIMIT_JPY", "GOOGLE_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "kimi",
        "label": "Kimi / Moonshot",
        "keys": ["MOONSHOT_API_KEY", "KIMI_API_KEY"],
        "limit_keys": ["KIMI_MONTHLY_LIMIT_JPY", "MOONSHOT_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "openrouter",
        "label": "OpenRouter",
        "keys": ["OPENROUTER_API_KEY"],
        "limit_keys": ["OPENROUTER_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "opencode_go",
        "label": "OpenCode GO",
        "keys": ["OPENCODE_GO_API_KEY", "OPENCODEGO_API_KEY"],
        "limit_keys": ["OPENCODE_GO_MONTHLY_LIMIT_JPY", "OPENCODEGO_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "cost_mode": "local_status_when_available",
    },
    {
        "id": "byterover",
        "label": "ByteRover",
        "keys": ["BYTEROVER_API_KEY", "ByteRover_API"],
        "limit_keys": ["BYTEROVER_MONTHLY_LIMIT_JPY"],
        "cost_mode": "free_tier_or_unknown",
    },
    {
        "id": "pexels",
        "label": "Pexels",
        "keys": ["PEXELS_API_KEY"],
        "limit_keys": [],
        "cost_mode": "free_api_cost_0_jpy_quota_unknown",
    },
    {
        "id": "pixabay",
        "label": "Pixabay",
        "keys": ["PIXABAY_API_KEY"],
        "limit_keys": [],
        "cost_mode": "free_api_cost_0_jpy_quota_unknown",
    },
    {
        "id": "unsplash",
        "label": "Unsplash",
        "keys": ["UNSPLASH_ACCESS_KEY", "Unsplash_Access Key"],
        "limit_keys": [],
        "cost_mode": "free_api_cost_0_jpy_quota_unknown",
    },
    {
        "id": "telegram",
        "label": "Telegram Bot",
        "keys": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_FAST_API_KEY"],
        "limit_keys": [],
        "cost_mode": "monetary_cost_0_jpy_rate_limit_only",
    },
    {
        "id": "turso",
        "label": "Turso",
        "keys": ["TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN"],
        "limit_keys": ["TURSO_MONTHLY_LIMIT_JPY"],
        "cost_mode": "unknown_without_plan_export",
    },
]


def read_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def as_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.replace(",", "").strip())
    except ValueError:
        return None


def first_value(env: dict[str, str], keys: list[str]) -> str | None:
    for key in keys:
        value = env.get(key)
        if value:
            return value
    return None


def scan_local_cost_evidence() -> list[dict]:
    evidence: list[dict] = []
    candidates = [
        WORKSPACE / "iatf_opencodego_video_pdca_policy_status.json",
        WORKSPACE / "api_quota_status.json",
        WORKSPACE / "opencode_go_cost_status.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            evidence.append({"path": str(path), "error": str(exc)})
            continue
        text = json.dumps(data, ensure_ascii=False)
        jpy_values = [float(x) for x in re.findall(r'"(?:estimated_cost_jpy|cost_jpy)"\s*:\s*([0-9.]+)', text)]
        usd_values = [float(x) for x in re.findall(r'"(?:estimated_cost_usd|cost_usd)"\s*:\s*([0-9.]+)', text)]
        evidence.append(
            {
                "path": str(path),
                "estimated_cost_jpy_sum": round(sum(jpy_values), 4),
                "estimated_cost_usd_sum": round(sum(usd_values), 6),
                "jpy_value_count": len(jpy_values),
                "usd_value_count": len(usd_values),
            }
        )
    return evidence


def load_quota_status() -> list[dict]:
    path = WORKSPACE / "api_quota_status.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    quotas = []
    for item in data.get("apis", []):
        usage = item.get("usage")
        limit = item.get("limit")
        remaining = None
        if isinstance(usage, (int, float)) and isinstance(limit, (int, float)):
            remaining = limit - usage
        quotas.append(
            {
                "name": item.get("name", ""),
                "usage": usage,
                "limit": limit,
                "remaining": remaining,
                "unit": item.get("unit", ""),
                "resetIn": item.get("resetIn", ""),
                "status": item.get("status", ""),
            }
        )
    return quotas


def quota_for_provider(provider_id: str, quotas: list[dict]) -> dict | None:
    patterns = {
        "openai": ["openai", "codex", "gpt"],
        "anthropic": ["claude", "anthropic"],
        "gemini": ["gemini", "google"],
        "opencode_go": ["opencodego", "opencode go", "opencode"],
    }.get(provider_id, [provider_id])
    for quota in quotas:
        name = str(quota.get("name", "")).lower()
        if any(pattern in name for pattern in patterns):
            return quota
    return None


def make_provider_report(env: dict[str, str], usd_jpy: float) -> list[dict]:
    rows = []
    local_evidence = scan_local_cost_evidence()
    quotas = load_quota_status()
    opencode_known_jpy = 0.0
    for item in local_evidence:
        if "iatf_opencodego_video_pdca_policy_status.json" in item.get("path", ""):
            opencode_known_jpy += item.get("estimated_cost_jpy_sum", 0.0) or 0.0

    for provider in PROVIDERS:
        has_key = first_value(env, provider["keys"]) is not None
        if provider["id"] == "telegram" and (ROOT / "clawstack_v2" / "secrets" / "notification.json").exists():
            has_key = True
        limit = as_float(first_value(env, provider["limit_keys"]))
        quota = quota_for_provider(provider["id"], quotas)
        known_jpy: float | None
        note: str
        if provider["id"] in {"pexels", "pixabay", "unsplash", "telegram"}:
            known_jpy = 0.0
            note = "Monetary API cost is treated as 0 JPY; request quota/rate-limit is not fully known from local files."
        elif provider["id"] == "opencode_go" and opencode_known_jpy:
            known_jpy = round(opencode_known_jpy, 4)
            note = "Estimated from local OpenCode GO PDCA status JSON."
        else:
            known_jpy = None
            note = "No provider billing export or usage API result is available locally; do not invent yen cost."

        remaining = None
        remaining_note = "unknown"
        if known_jpy is not None and limit is not None:
            remaining = round(limit - known_jpy, 4)
            remaining_note = f"{remaining} JPY remaining to configured limit"
        elif limit is not None:
            remaining_note = "configured limit exists, but spend is unknown"
        elif known_jpy is not None:
            remaining_note = "no configured JPY limit"

        rows.append(
            {
                "provider": provider["label"],
                "id": provider["id"],
                "configured": has_key,
                "known_spend_jpy": known_jpy,
                "configured_limit_jpy": limit,
                "remaining_to_limit_jpy": remaining,
                "remaining_note": remaining_note,
                "usage_quota": quota,
                "cost_mode": provider["cost_mode"],
                "note": note,
            }
        )
    return rows


def render_markdown(payload: dict) -> str:
    lines = [
        "# API Cost Report",
        "",
        f"- Generated: {payload['generated_at_jst']}",
        f"- USD/JPY used for optional USD conversion: {payload['usd_jpy']}",
        "- Rule: unknown billing must stay unknown; this report does not invent yen cost.",
        "",
        "| Provider | Configured | Known spend JPY | Limit JPY | JPY Remaining | Usage quota remaining | Note |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload["providers"]:
        spend = "unknown" if row["known_spend_jpy"] is None else f"{row['known_spend_jpy']:.4f}"
        limit = "not set" if row["configured_limit_jpy"] is None else f"{row['configured_limit_jpy']:.4f}"
        remaining = "unknown" if row["remaining_to_limit_jpy"] is None else f"{row['remaining_to_limit_jpy']:.4f}"
        quota = row.get("usage_quota")
        if quota:
            quota_text = f"{quota.get('remaining')} / {quota.get('limit')} {quota.get('unit')} resets {quota.get('resetIn')} ({quota.get('status')})"
        else:
            quota_text = "unknown"
        lines.append(
            f"| {row['provider']} | {row['configured']} | {spend} | {limit} | {remaining} | {quota_text} | {row['remaining_note']} |"
        )
    lines.extend(
        [
            "",
            "## Local Evidence",
            "",
        ]
    )
    if payload["local_cost_evidence"]:
        for item in payload["local_cost_evidence"]:
            lines.append(f"- `{item.get('path')}`: JPY={item.get('estimated_cost_jpy_sum', 0)}, USD={item.get('estimated_cost_usd_sum', 0)}")
    else:
        lines.append("- No local cost evidence files found.")
    return "\n".join(lines) + "\n"


def send_telegram(text: str) -> str:
    secret_path = ROOT / "clawstack_v2" / "secrets" / "notification.json"
    env = read_env(ROOT / ".env")
    token = None
    chat_id = env.get("TELEGRAM_CHAT_ID")
    if secret_path.exists():
        try:
            secret = json.loads(secret_path.read_text(encoding="utf-8"))
            token = secret.get("telegram_bot_token")
        except Exception:
            token = None
    if not token or not chat_id:
        return "skipped: telegram token or chat id missing"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:3800]}).encode("utf-8")
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST")
    with urllib.request.urlopen(req, timeout=20) as res:
        return f"sent:{res.status}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a P009 API cost report in JPY.")
    parser.add_argument("--usd-jpy", type=float, default=float(os.environ.get("USD_JPY_RATE", "155.0")))
    parser.add_argument("--send-telegram", action="store_true")
    args = parser.parse_args()

    env = read_env(ROOT / ".env")
    payload = {
        "policy_id": "P009",
        "status": "active",
        "generated_at_jst": datetime.now().astimezone().isoformat(timespec="seconds"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "usd_jpy": args.usd_jpy,
        "providers": make_provider_report(env, args.usd_jpy),
        "local_cost_evidence": scan_local_cost_evidence(),
        "local_usage_quota_evidence": load_quota_status(),
        "limitations": [
            "Actual cloud billing requires provider billing exports or usage APIs; absent data is reported as unknown.",
            "ChatGPT Plus/Codex UI usage is not visible from this workspace unless an export is provided.",
            "Free photo APIs are reported as 0 JPY monetary cost, but quota remaining is not fully known locally.",
        ],
    }
    STATUS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = render_markdown(payload)
    STATUS_MD.write_text(markdown, encoding="utf-8")
    telegram = None
    if args.send_telegram:
        telegram = send_telegram(markdown)
        payload["telegram"] = telegram
        STATUS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(STATUS_JSON), "markdown": str(STATUS_MD), "telegram": telegram}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
