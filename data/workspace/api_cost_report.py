from __future__ import annotations

import argparse
import html
import json
import os
import re
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "data" / "workspace"
STATUS_JSON = WORKSPACE / "api_cost_report_status.json"
STATUS_MD = WORKSPACE / "api_cost_report_status.md"
HISTORY_JSONL = WORKSPACE / "api_cost_report_history.jsonl"
HISTORY_SQLITE = WORKSPACE / "api_cost_report.sqlite"


PROVIDERS = [
    {
        "id": "openai",
        "label": "OpenAI",
        "keys": ["OPENAI_API_KEY", "CLOUD_OPENAI_API_KEY"],
        "limit_keys": ["OPENAI_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "fixed_fee_keys": ["OPENAI_FIXED_MONTHLY_JPY"],
        "billing_mode_keys": ["OPENAI_BILLING_MODE"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "anthropic",
        "label": "Anthropic / Claude",
        "keys": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
        "limit_keys": ["ANTHROPIC_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "fixed_fee_keys": ["ANTHROPIC_FIXED_MONTHLY_JPY", "CLAUDE_FIXED_MONTHLY_JPY"],
        "billing_mode_keys": ["ANTHROPIC_BILLING_MODE", "CLAUDE_BILLING_MODE"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "gemini",
        "label": "Google Gemini",
        "keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "limit_keys": ["GEMINI_MONTHLY_LIMIT_JPY", "GOOGLE_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "fixed_fee_keys": ["GEMINI_FIXED_MONTHLY_JPY", "GOOGLE_FIXED_MONTHLY_JPY"],
        "billing_mode_keys": ["GEMINI_BILLING_MODE", "GOOGLE_BILLING_MODE"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "kimi",
        "label": "Kimi / Moonshot",
        "keys": ["MOONSHOT_API_KEY", "KIMI_API_KEY"],
        "limit_keys": ["KIMI_MONTHLY_LIMIT_JPY", "MOONSHOT_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "fixed_fee_keys": ["KIMI_FIXED_MONTHLY_JPY", "MOONSHOT_FIXED_MONTHLY_JPY"],
        "billing_mode_keys": ["KIMI_BILLING_MODE", "MOONSHOT_BILLING_MODE"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "openrouter",
        "label": "OpenRouter",
        "keys": ["OPENROUTER_API_KEY"],
        "limit_keys": ["OPENROUTER_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "fixed_fee_keys": ["OPENROUTER_FIXED_MONTHLY_JPY"],
        "billing_mode_keys": ["OPENROUTER_BILLING_MODE"],
        "cost_mode": "unknown_without_billing_export",
    },
    {
        "id": "opencode_go",
        "label": "OpenCode GO",
        "keys": ["OPENCODE_GO_API_KEY", "OPENCODEGO_API_KEY", "OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY", "OpenCode_Go"],
        "limit_keys": ["OPENCODE_GO_MONTHLY_LIMIT_JPY", "OPENCODEGO_MONTHLY_LIMIT_JPY", "API_MONTHLY_BUDGET_JPY"],
        "fixed_fee_keys": ["OPENCODE_GO_FIXED_MONTHLY_JPY", "OPENCODEGO_FIXED_MONTHLY_JPY"],
        "billing_mode_keys": ["OPENCODE_GO_BILLING_MODE", "OPENCODEGO_BILLING_MODE"],
        "cost_mode": "local_status_when_available",
    },
    {
        "id": "byterover",
        "label": "ByteRover",
        "keys": ["BYTEROVER_API_KEY", "ByteRover_API"],
        "limit_keys": ["BYTEROVER_MONTHLY_LIMIT_JPY"],
        "fixed_fee_keys": ["BYTEROVER_FIXED_MONTHLY_JPY"],
        "billing_mode_keys": ["BYTEROVER_BILLING_MODE"],
        "cost_mode": "free_tier_or_unknown",
    },
    {
        "id": "pexels",
        "label": "Pexels",
        "keys": ["PEXELS_API_KEY"],
        "limit_keys": [],
        "fixed_fee_keys": [],
        "billing_mode_keys": [],
        "default_billing_mode": "free",
        "cost_mode": "free_api_cost_0_jpy_quota_unknown",
    },
    {
        "id": "pixabay",
        "label": "Pixabay",
        "keys": ["PIXABAY_API_KEY"],
        "limit_keys": [],
        "fixed_fee_keys": [],
        "billing_mode_keys": [],
        "default_billing_mode": "free",
        "cost_mode": "free_api_cost_0_jpy_quota_unknown",
    },
    {
        "id": "unsplash",
        "label": "Unsplash",
        "keys": ["UNSPLASH_ACCESS_KEY", "Unsplash_Access Key"],
        "limit_keys": [],
        "fixed_fee_keys": [],
        "billing_mode_keys": [],
        "default_billing_mode": "free",
        "cost_mode": "free_api_cost_0_jpy_quota_unknown",
    },
    {
        "id": "telegram",
        "label": "Telegram Bot",
        "keys": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_FAST_API_KEY"],
        "limit_keys": [],
        "fixed_fee_keys": [],
        "billing_mode_keys": [],
        "default_billing_mode": "free",
        "cost_mode": "monetary_cost_0_jpy_rate_limit_only",
    },
    {
        "id": "turso",
        "label": "Turso",
        "keys": ["TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN"],
        "limit_keys": ["TURSO_MONTHLY_LIMIT_JPY"],
        "fixed_fee_keys": ["TURSO_FIXED_MONTHLY_JPY"],
        "billing_mode_keys": ["TURSO_BILLING_MODE"],
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


def normalize_billing_mode(value: str | None, default: str | None = None) -> str:
    mode = (value or default or "unknown").strip().lower().replace("-", "_")
    aliases = {
        "fixed": "fixed_monthly",
        "subscription": "fixed_monthly",
        "monthly": "fixed_monthly",
        "included": "fixed_monthly",
        "free_tier": "free",
        "usage": "usage_based",
        "payg": "usage_based",
        "pay_as_you_go": "usage_based",
    }
    return aliases.get(mode, mode)


def classify_billing_status(
    configured: bool,
    billing_mode: str,
    known_spend_jpy: float | None,
    limit_jpy: float | None,
    fixed_fee_jpy: float | None,
) -> str:
    if not configured:
        return "not_configured"
    if billing_mode == "free":
        return "free_no_monetary_cost"
    if billing_mode == "fixed_monthly":
        if known_spend_jpy is None:
            return "fixed_monthly_fee_configured_usage_unknown" if fixed_fee_jpy is not None else "fixed_monthly_plan_unpriced"
        if limit_jpy is not None and known_spend_jpy > limit_jpy:
            return "over_configured_limit"
        return "within_fixed_monthly_plan"
    if known_spend_jpy is None:
        return "billing_amount_unknown"
    if limit_jpy is not None and known_spend_jpy > limit_jpy:
        return "over_configured_limit"
    if limit_jpy is not None:
        return "within_configured_limit"
    return "known_spend_no_limit"


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
        fixed_fee = as_float(first_value(env, provider.get("fixed_fee_keys", [])))
        billing_mode = normalize_billing_mode(
            first_value(env, provider.get("billing_mode_keys", [])),
            provider.get("default_billing_mode"),
        )
        if billing_mode == "unknown" and fixed_fee is not None:
            billing_mode = "fixed_monthly"
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

        total_known_monthly_jpy = None
        if fixed_fee is not None and known_jpy is not None:
            total_known_monthly_jpy = round(fixed_fee + known_jpy, 4)
        elif fixed_fee is not None:
            total_known_monthly_jpy = round(fixed_fee, 4)
        elif known_jpy is not None:
            total_known_monthly_jpy = known_jpy

        billing_status = classify_billing_status(has_key, billing_mode, known_jpy, limit, fixed_fee)

        rows.append(
            {
                "provider": provider["label"],
                "id": provider["id"],
                "configured": has_key,
                "billing_mode": billing_mode,
                "fixed_monthly_fee_jpy": fixed_fee,
                "known_spend_jpy": known_jpy,
                "total_known_monthly_jpy": total_known_monthly_jpy,
                "configured_limit_jpy": limit,
                "remaining_to_limit_jpy": remaining,
                "remaining_note": remaining_note,
                "billing_status": billing_status,
                "usage_quota": quota,
                "cost_mode": provider["cost_mode"],
                "note": note,
            }
        )
    return rows


def summarize_costs(rows: list[dict]) -> dict:
    known_variable = sum(row["known_spend_jpy"] or 0.0 for row in rows)
    known_fixed = sum(row["fixed_monthly_fee_jpy"] or 0.0 for row in rows)
    total_known = sum(row["total_known_monthly_jpy"] or 0.0 for row in rows)
    unknown = [row["provider"] for row in rows if row["configured"] and row["billing_status"] in {
        "billing_amount_unknown",
        "fixed_monthly_plan_unpriced",
        "fixed_monthly_fee_configured_usage_unknown",
    }]
    over_limit = [row["provider"] for row in rows if row["billing_status"] == "over_configured_limit"]
    fixed_or_free_ok = [
        row["provider"]
        for row in rows
        if row["configured"] and row["billing_status"] in {"free_no_monetary_cost", "within_fixed_monthly_plan"}
    ]
    return {
        "known_variable_spend_jpy": round(known_variable, 4),
        "known_fixed_monthly_fees_jpy": round(known_fixed, 4),
        "total_known_monthly_jpy": round(total_known, 4),
        "configured_unknown_billing_count": len(unknown),
        "configured_unknown_billing_providers": unknown,
        "over_limit_providers": over_limit,
        "fixed_or_free_ok_providers": fixed_or_free_ok,
        "has_over_limit": bool(over_limit),
        "has_unknown_billing": bool(unknown),
    }


def append_history(payload: dict) -> None:
    record = {
        "generated_at_jst": payload["generated_at_jst"],
        "generated_at_utc": payload["generated_at_utc"],
        "policy_id": payload["policy_id"],
        "summary": payload["summary"],
        "providers": payload["providers"],
    }
    with HISTORY_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    with sqlite3.connect(HISTORY_SQLITE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_cost_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at_jst TEXT NOT NULL,
                generated_at_utc TEXT NOT NULL,
                total_known_monthly_jpy REAL NOT NULL,
                known_variable_spend_jpy REAL NOT NULL,
                known_fixed_monthly_fees_jpy REAL NOT NULL,
                configured_unknown_billing_count INTEGER NOT NULL,
                has_over_limit INTEGER NOT NULL,
                summary_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_cost_provider_status (
                report_id INTEGER NOT NULL,
                provider_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                configured INTEGER NOT NULL,
                billing_mode TEXT NOT NULL,
                fixed_monthly_fee_jpy REAL,
                known_spend_jpy REAL,
                total_known_monthly_jpy REAL,
                configured_limit_jpy REAL,
                remaining_to_limit_jpy REAL,
                billing_status TEXT NOT NULL,
                quota_status TEXT,
                provider_json TEXT NOT NULL,
                FOREIGN KEY(report_id) REFERENCES api_cost_reports(id)
            )
            """
        )
        cursor = conn.execute(
            """
            INSERT INTO api_cost_reports (
                generated_at_jst,
                generated_at_utc,
                total_known_monthly_jpy,
                known_variable_spend_jpy,
                known_fixed_monthly_fees_jpy,
                configured_unknown_billing_count,
                has_over_limit,
                summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["generated_at_jst"],
                payload["generated_at_utc"],
                payload["summary"]["total_known_monthly_jpy"],
                payload["summary"]["known_variable_spend_jpy"],
                payload["summary"]["known_fixed_monthly_fees_jpy"],
                payload["summary"]["configured_unknown_billing_count"],
                1 if payload["summary"]["has_over_limit"] else 0,
                json.dumps(payload["summary"], ensure_ascii=False),
            ),
        )
        report_id = cursor.lastrowid
        for row in payload["providers"]:
            quota = row.get("usage_quota") or {}
            conn.execute(
                """
                INSERT INTO api_cost_provider_status (
                    report_id,
                    provider_id,
                    provider,
                    configured,
                    billing_mode,
                    fixed_monthly_fee_jpy,
                    known_spend_jpy,
                    total_known_monthly_jpy,
                    configured_limit_jpy,
                    remaining_to_limit_jpy,
                    billing_status,
                    quota_status,
                    provider_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    row["id"],
                    row["provider"],
                    1 if row["configured"] else 0,
                    row["billing_mode"],
                    row["fixed_monthly_fee_jpy"],
                    row["known_spend_jpy"],
                    row["total_known_monthly_jpy"],
                    row["configured_limit_jpy"],
                    row["remaining_to_limit_jpy"],
                    row["billing_status"],
                    quota.get("status"),
                    json.dumps(row, ensure_ascii=False),
                ),
            )
        conn.commit()


def render_markdown(payload: dict) -> str:
    lines = [
        "# API Cost Report",
        "",
        f"- Generated: {payload['generated_at_jst']}",
        f"- USD/JPY used for optional USD conversion: {payload['usd_jpy']}",
        "- Rule: unknown billing must stay unknown; this report does not invent yen cost.",
        f"- Known variable spend: {payload['summary']['known_variable_spend_jpy']:.4f} JPY",
        f"- Known fixed monthly fees: {payload['summary']['known_fixed_monthly_fees_jpy']:.4f} JPY",
        f"- Total known monthly cost: {payload['summary']['total_known_monthly_jpy']:.4f} JPY",
        f"- Unknown configured billing providers: {payload['summary']['configured_unknown_billing_count']}",
        f"- History DB: `{HISTORY_JSONL}`",
        f"- SQLite DB: `{HISTORY_SQLITE}`",
        "",
        "| Provider | Configured | Billing mode | Fixed monthly JPY | Known variable JPY | Total known JPY | Limit JPY | JPY Remaining | Billing status | Usage quota remaining |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in payload["providers"]:
        spend = "unknown" if row["known_spend_jpy"] is None else f"{row['known_spend_jpy']:.4f}"
        fixed = "not set" if row["fixed_monthly_fee_jpy"] is None else f"{row['fixed_monthly_fee_jpy']:.4f}"
        total = "unknown" if row["total_known_monthly_jpy"] is None else f"{row['total_known_monthly_jpy']:.4f}"
        limit = "not set" if row["configured_limit_jpy"] is None else f"{row['configured_limit_jpy']:.4f}"
        remaining = "unknown" if row["remaining_to_limit_jpy"] is None else f"{row['remaining_to_limit_jpy']:.4f}"
        quota = row.get("usage_quota")
        if quota:
            quota_text = f"{quota.get('remaining')} / {quota.get('limit')} {quota.get('unit')} resets {quota.get('resetIn')} ({quota.get('status')})"
        else:
            quota_text = "unknown"
        lines.append(
            f"| {row['provider']} | {row['configured']} | {row['billing_mode']} | {fixed} | {spend} | {total} | {limit} | {remaining} | {row['billing_status']} | {quota_text} |"
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


def render_telegram_html(payload: dict) -> str:
    lines = [
        "📊 <b>【Clawstack】API Cost &amp; Quota Report</b>",
        "",
        f"📅 <i>Generated: {payload['generated_at_jst']}</i>",
        f"💴 USD/JPY Rate: {payload['usd_jpy']}",
        "",
        "<b>====== SUMMARY ======</b>"
    ]
    summary = payload["summary"]
    var_spend = summary["known_variable_spend_jpy"]
    fixed_fees = summary["known_fixed_monthly_fees_jpy"]
    total_cost = summary["total_known_monthly_jpy"]
    
    if total_cost > 0:
        lines.append(f"🟠 <b>Total Known Monthly JPY: {total_cost:.4f}</b> (Var: {var_spend:.4f}, Fixed: {fixed_fees:.4f})")
    else:
        lines.append(f"🟢 Total Known Monthly JPY: 0.0000")
        
    lines.append(f"❓ Unknown Billing Configured Providers: {summary['configured_unknown_billing_count']}")
    
    lines.extend([
        "",
        "<b>====== PROVIDER DETAILS ======</b>"
    ])
    
    for row in payload["providers"]:
        quota = row.get("usage_quota") or {}
        quota_status = str(quota.get("status", "")).lower()
        billing_status = str(row["billing_status"]).lower()
        
        spend = "unknown" if row["known_spend_jpy"] is None else f"{row['known_spend_jpy']:.4f} JPY"
        fixed = "not set" if row["fixed_monthly_fee_jpy"] is None else f"{row['fixed_monthly_fee_jpy']:.4f} JPY"
        limit = "not set" if row["configured_limit_jpy"] is None else f"{row['configured_limit_jpy']:.4f} JPY"
        
        quota_text = ""
        if quota:
            quota_text = f"{quota.get('remaining')} / {quota.get('limit')} {quota.get('unit')} resets {quota.get('resetIn')} ({quota.get('status')})"
        else:
            quota_text = "unknown"
            
        emoji = "⚪"
        prefix = ""
        suffix = ""
        
        # 1. 限界近い (Critical / Warning)
        if quota_status == "critical" or "critical" in quota_text.lower() or billing_status == "over_configured_limit":
            emoji = "🔴"
            prefix = "<b>[LIMIT CRITICAL] "
            suffix = "</b>"
        elif quota_status == "warning" or "warning" in quota_text.lower():
            emoji = "⚠️"
            prefix = "<b>[LIMIT WARNING] "
            suffix = "</b>"
        # 2. 費用が発生している (Spend/Billing Detected)
        elif (row["known_spend_jpy"] is not None and row["known_spend_jpy"] > 0) or (row["fixed_monthly_fee_jpy"] is not None and row["fixed_monthly_fee_jpy"] > 0):
            emoji = "🟠"
            prefix = "<b>[SPEND DETECTED] "
            suffix = "</b>"
        # 3. 無料 (Free / OK)
        elif "free" in billing_status:
            emoji = "🟢"
            prefix = "[FREE] "
        elif row["configured"]:
            emoji = "🔵"
            prefix = "[ACTIVE] "
        else:
            emoji = "⚫"
            prefix = "[INACTIVE] "
            
        p_name = html.escape(row["provider"])
        lines.append(f"{emoji} {prefix}{p_name}{suffix}")
        lines.append(f"   ├ Mode: {html.escape(row['billing_mode'])} | Spend: {spend}")
        lines.append(f"   ├ Limit: {limit} | Quota: {html.escape(quota_text)}")
        
    lines.extend([
        "",
        "📈 <b>Growth &amp; Improvement Dashboard</b>",
        "🔗 http://localhost:8088/apps/growth_dashboard/index.html"
    ])
    return "\n".join(lines) + "\n"


def send_telegram(text: str) -> str:
    secret_path = ROOT / "clawstack_v2" / "secrets" / "notification.json"
    env = {**read_env(ROOT / ".env"), **os.environ}
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
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:3800], "parse_mode": "HTML"}).encode("utf-8")
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST")
    with urllib.request.urlopen(req, timeout=20) as res:
        return f"sent:{res.status}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a P009 API cost report in JPY.")
    parser.add_argument("--usd-jpy", type=float, default=float(os.environ.get("USD_JPY_RATE", "155.0")))
    parser.add_argument("--send-telegram", action="store_true")
    args = parser.parse_args()

    env = read_env(ROOT / ".env")
    providers = make_provider_report(env, args.usd_jpy)
    payload = {
        "policy_id": "P009",
        "status": "active",
        "generated_at_jst": datetime.now().astimezone().isoformat(timespec="seconds"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "usd_jpy": args.usd_jpy,
        "providers": providers,
        "summary": summarize_costs(providers),
        "local_cost_evidence": scan_local_cost_evidence(),
        "local_usage_quota_evidence": load_quota_status(),
        "limitations": [
            "Actual cloud billing requires provider billing exports or usage APIs; absent data is reported as unknown.",
            "ChatGPT Plus/Codex UI usage is not visible from this workspace unless an export is provided.",
            "Free photo APIs are reported as 0 JPY monetary cost, but quota remaining is not fully known locally.",
            "Fixed monthly plans are only classified as fixed when *_BILLING_MODE=fixed_monthly or *_FIXED_MONTHLY_JPY is configured locally.",
        ],
    }
    append_history(payload)
    STATUS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = render_markdown(payload)
    STATUS_MD.write_text(markdown, encoding="utf-8")
    telegram = None
    if args.send_telegram:
        telegram_html = render_telegram_html(payload)
        telegram = send_telegram(telegram_html)
        payload["telegram"] = telegram
        STATUS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(STATUS_JSON), "markdown": str(STATUS_MD), "telegram": telegram}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
