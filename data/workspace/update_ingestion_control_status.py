from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent

EMAIL_DAEMON_STATUS = ROOT / "email_continuous_ingest_status.json"
EMAIL_WATCHDOG_STATUS = ROOT / "email_continuous_watchdog_status.json"
EMAIL_INTEGRITY_STATUS = ROOT / "email_search_integrity_status.json"
PAPERLESS_INGEST_STATUS = ROOT / "ingest_watchdog_status.json"
PAPERLESS_WATCHDOG_STATUS = ROOT / "paperless_rag_watchdog_status.json"
PAPERLESS_REVIEW_STATUS = ROOT / "paperless_pdf_review_artifacts_status.json"

OUTPUT_JSON = ROOT / "data_ingestion_control_status.json"
OUTPUT_MD = ROOT / "data_ingestion_control_summary.md"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


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


def age_minutes(value: str | None) -> float | None:
    dt = parse_dt(value)
    if dt is None:
        return None
    delta = now_jst().astimezone(dt.tzinfo) - dt
    return round(delta.total_seconds() / 60.0, 1)


def status_level(ok: bool, warn: bool = False) -> str:
    if ok:
        return "healthy"
    if warn:
        return "degraded"
    return "error"


def email_status() -> dict[str, Any]:
    daemon = read_json(EMAIL_DAEMON_STATUS)
    watchdog = read_json(EMAIL_WATCHDOG_STATUS)
    integrity = read_json(EMAIL_INTEGRITY_STATUS)

    daemon_stage = str(daemon.get("stage") or "unknown")
    daemon_age = age_minutes(daemon.get("updatedAt") or daemon.get("lastSuccessAt"))
    watchdog_age = age_minutes(watchdog.get("updatedAt"))
    integrity_ok = bool(integrity.get("ok"))
    integrity_age = age_minutes(integrity.get("finishedAt") or integrity.get("startedAt"))
    last_success = daemon.get("lastSuccessAt")
    last_error = str(daemon.get("lastError") or "").strip()

    stage_healthy = daemon_stage in {"idle", "indexing", "sync_learning", "dashboard_refresh", "full_backfill"}
    daemon_fresh = daemon_age is not None and daemon_age <= 20
    watchdog_fresh = watchdog_age is not None and watchdog_age <= 20 and str(watchdog.get("stage") or "") == "running"
    integrity_recent = integrity_age is not None and integrity_age <= 720

    ok = daemon_fresh and stage_healthy and watchdog_fresh and integrity_ok and integrity_recent
    degraded = (daemon_fresh and watchdog_fresh) or (integrity_ok and integrity_recent)

    recommended = []
    if not daemon_fresh or not stage_healthy:
        recommended.append("continuous_email_ingest_daemon.py を修復または再起動")
    if not watchdog_fresh:
        recommended.append("email_continuous_watchdog.py の心拍と再起動履歴を確認")
    if not (integrity_ok and integrity_recent):
        recommended.append("email_search.db の integrity check / repair を実行")

    return {
        "name": "Gmail Ingestion",
        "level": status_level(ok, degraded),
        "healthy": ok,
        "daemonStage": daemon_stage,
        "daemonAgeMinutes": daemon_age,
        "watchdogAgeMinutes": watchdog_age,
        "integrityOk": integrity_ok,
        "integrityAgeMinutes": integrity_age,
        "lastSuccessAt": last_success,
        "lastError": last_error,
        "recommendedActions": recommended,
    }


def paperless_status() -> dict[str, Any]:
    ingest = read_json(PAPERLESS_INGEST_STATUS)
    watchdog = read_json(PAPERLESS_WATCHDOG_STATUS)
    review = read_json(PAPERLESS_REVIEW_STATUS)

    ingest_stage = str(ingest.get("stage") or "unknown")
    ingest_age = age_minutes(ingest.get("updatedAt"))
    watchdog_age = age_minutes(watchdog.get("updatedAt"))
    review_age = age_minutes(review.get("updatedAt"))
    processed_count = ingest.get("processedCount")

    ingest_fresh = ingest_age is not None and ingest_age <= 20 and ingest_stage in {"starting", "polling", "processing", "processing_batch", "idle"}
    watchdog_fresh = watchdog_age is not None and watchdog_age <= 20 and str(watchdog.get("stage") or "") == "healthy"
    review_ok = bool(review.get("ok"))
    review_recent = review_age is not None and review_age <= 720

    ok = ingest_fresh and watchdog_fresh and review_ok and review_recent
    degraded = (ingest_fresh and watchdog_fresh) or (review_ok and review_recent)

    recommended = []
    if not ingest_fresh:
        recommended.append("ingest_watchdog.py の stage / queue / Qdrant 接続を確認")
    if not watchdog_fresh:
        recommended.append("paperless_rag_watchdog.py の心拍と restart 履歴を確認")
    if not (review_ok and review_recent):
        recommended.append("review artifact を update_paperless_pdf_review_artifacts.py で再生成")

    return {
        "name": "Paperless Ingestion",
        "level": status_level(ok, degraded),
        "healthy": ok,
        "ingestStage": ingest_stage,
        "ingestAgeMinutes": ingest_age,
        "watchdogAgeMinutes": watchdog_age,
        "reviewOk": review_ok,
        "reviewAgeMinutes": review_age,
        "processedCount": processed_count,
        "recommendedActions": recommended,
    }


def build_payload() -> dict[str, Any]:
    email = email_status()
    paperless = paperless_status()
    overall_ok = email["healthy"] and paperless["healthy"]
    overall_degraded = email["level"] == "degraded" or paperless["level"] == "degraded"

    if overall_ok:
        overall = "healthy"
        summary = "Gmail と Paperless はともに継続蓄積できています。"
    elif overall_degraded:
        overall = "degraded"
        summary = "少なくとも一方が注意状態です。停止前に介入できます。"
    else:
        overall = "error"
        summary = "少なくとも一方は業務停止に近い状態です。即対応が必要です。"

    return {
        "updatedAt": now_text(),
        "service": "data_ingestion_control",
        "overall": overall,
        "summary": summary,
        "systems": {
            "gmail": email,
            "paperless": paperless,
        },
    }


def write_summary(payload: dict[str, Any]) -> None:
    lines = [
        "# Data Ingestion Control Summary",
        "",
        f"Updated: {payload['updatedAt']}",
        "",
        f"Overall: {payload['overall']}",
        payload["summary"],
        "",
    ]
    for key in ("gmail", "paperless"):
        item = payload["systems"][key]
        lines.append(f"## {item['name']}")
        lines.append(f"- Level: {item['level']}")
        if key == "gmail":
            lines.append(f"- Daemon stage: {item['daemonStage']}")
            lines.append(f"- Daemon age: {item['daemonAgeMinutes']} min")
            lines.append(f"- Watchdog age: {item['watchdogAgeMinutes']} min")
            lines.append(f"- Integrity ok: {item['integrityOk']}")
            lines.append(f"- Last success: {item['lastSuccessAt']}")
            if item["lastError"]:
                lines.append(f"- Last error: {item['lastError']}")
        else:
            lines.append(f"- Ingest stage: {item['ingestStage']}")
            lines.append(f"- Ingest age: {item['ingestAgeMinutes']} min")
            lines.append(f"- Watchdog age: {item['watchdogAgeMinutes']} min")
            lines.append(f"- Review ok: {item['reviewOk']}")
            lines.append(f"- Processed count: {item['processedCount']}")
        lines.append("- Recommended actions:")
        if item["recommendedActions"]:
            for action in item["recommendedActions"]:
                lines.append(f"  - {action}")
        else:
            lines.append("  - none")
        lines.append("")
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    payload = build_payload()
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary(payload)
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
