# -*- coding: utf-8 -*-
"""Mirror browser-inaccessible dashboard documents and audit content assets."""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "data" / "workspace" / "apps" / "growth_dashboard"
DOWNLOADS = DASH / "downloads"
JST = timezone(timedelta(hours=9))
DATA_SOURCE_PATHS = [
    DASH / "growth_stats.json",
    DASH / "commercial_benchmark_maturity_latest.json",
    DASH / "iatf_video_qa_status.json",
    DASH / "material_source_inventory.json",
    DASH / "iatf_youtube_summary.json",
    DASH / "fleet_diagnostics_status.json",
    DASH / "fleet_idle_dispatch_status.json",
    DASH / "fleet_node_workload_snapshot.json",
    DASH / "k10_tri_track_cae_status.json",
    DASH / "distributed_scheduler_status.json",
    DASH / "knowledge_history.json",
    DASH / "autonomous_improvements.json",
    DASH / "becky_pipeline_status.json",
    DASH / "content_publishing_catalog.json",
    DASH / "dxf2step_project_status.json",
    DASH / "robot_l20_autonomous_status.json",
    DASH / "trend_content_status.json",
    DASH / "content_approval_queue.json",
]


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def source_documents() -> list[tuple[Path, str, str]]:
    game_root = Path("D:/Local_AI_GameDev_Master")
    unity_candidates = sorted(
        path for path in (game_root / "13_UnityMCP").glob("*")
        if path.is_file() and path.name.lower().startswith("readme")
    )
    return [
        (ROOT / "docs" / "INCIDENT_LOG.md", "incident_log.md", "トラブル履歴"),
        (ROOT / "docs" / "incidents" / "quality_incident_report_20260615_thinkpad_sleep_outage.md", "thinkpad_sleep_outage_20260615.md", "ThinkPadスリープ障害レポート"),
        (ROOT / "docs" / "incidents" / "quality_incident_report_20260609_lavie_bios_disconnect.md", "lavie_bios_disconnect_20260609.md", "LAVIE BIOS切断レポート"),
        (game_root / "07_GameDesign" / "ときメモ風3D恋愛シミュレーション企画書.md", "tokimemo_3d_gdd.md", "3D恋愛シミュレーション企画書"),
        (game_root / "07_GameDesign" / "romantic_tropes_db.json", "romantic_tropes_db.json", "トキメキ心理演出DB"),
        (unity_candidates[0] if unity_candidates else game_root / "13_UnityMCP" / "README.md", "unity_mcp_integration.md", "Unity MCP統合ガイド"),
        (game_root / "00_StartHere" / "UE5_Unity_Hybrid_Architecture.md", "ue5_unity_hybrid_architecture.md", "UE5×Unity6ハイブリッド仕様"),
    ]


def mirror_documents() -> list[dict]:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    rows = []
    for source, dest_name, label in source_documents():
        dest = DOWNLOADS / dest_name
        exists = source.is_file()
        if exists:
            shutil.copy2(source, dest)
        rows.append({
            "category": "document", "label": label, "source": str(source),
            "url": f"downloads/{dest_name}", "exists": exists and dest.is_file(),
            "source_updated_at": datetime.fromtimestamp(source.stat().st_mtime, JST).isoformat(timespec="seconds") if exists else None,
        })
    return rows


def content_assets() -> list[dict]:
    rows: list[dict] = []
    catalog = json.loads((DASH / "content_publishing_catalog.json").read_text(encoding="utf-8"))
    for item in catalog.get("items", []):
        for relative in item.get("asset_paths", []):
            path = (DASH / relative).resolve()
            rows.append({
                "category": "article_asset", "owner_id": item.get("id"),
                "label": path.name, "url": relative.replace("\\", "/"),
                "exists": path.is_file(),
                "source_updated_at": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds") if path.is_file() else None,
            })
    queue = json.loads((DASH / "content_approval_queue.json").read_text(encoding="utf-8"))
    for item in queue:
        relative = item.get("body_path")
        if not relative:
            continue
        path = (DASH / relative).resolve()
        rows.append({
            "category": str(item.get("type") or "content").lower(),
            "owner_id": item.get("id"), "label": path.name,
            "url": relative.replace("\\", "/"), "exists": path.is_file(),
            "source_updated_at": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds") if path.is_file() else None,
        })
    return rows


def application_and_video_assets() -> list[dict]:
    rows: list[dict] = []
    applications = [
        ("複数ロボット学習ビューア", DASH / "robot_learning_swarm_demo.html", "robot_learning_swarm_demo.html"),
        ("工場ワークセルモック", DASH / "factory_workcell_mock.html", "factory_workcell_mock.html"),
        ("絶対占い統合アプリ", DASH / "absolute_oracle_fortune.html", "absolute_oracle_fortune.html"),
        ("Local AI GameDev Launcher", DASH / "local_ai_gamedev_launcher.html", "local_ai_gamedev_launcher.html"),
        ("CETOL 3D公差解析", DASH.parent / "cetol6sigma" / "index.html", "../cetol6sigma/index.html"),
    ]
    for label, path, url in applications:
        rows.append({
            "category": "application", "label": label, "url": url, "exists": path.is_file(),
            "source_updated_at": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds") if path.is_file() else None,
        })

    qa_path = DASH / "iatf_video_qa_status.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    for video in qa.get("videos", []):
        relative = str(video.get("mp4_path") or "")
        path = ROOT / relative
        rows.append({
            "category": "video",
            "label": str(video.get("topic") or video.get("title") or path.name),
            "url": relative.replace("data/iatf_videos", "/iatf_videos").replace("\\", "/"),
            "exists": path.is_file(),
            "source_updated_at": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds") if path.is_file() else None,
        })
    return rows


def data_source_freshness() -> list[dict]:
    now = datetime.now(JST)
    rows = []
    for path in DATA_SOURCE_PATHS:
        exists = path.is_file()
        modified = datetime.fromtimestamp(path.stat().st_mtime, JST) if exists else None
        age_hours = (now - modified).total_seconds() / 3600 if modified else None
        rows.append({
            "name": path.name,
            "exists": exists,
            "updated_at": modified.isoformat(timespec="seconds") if modified else None,
            "age_hours": round(age_hours, 1) if age_hours is not None else None,
            "stale_over_48h": age_hours is None or age_hours > 48,
        })
    return rows


def main() -> int:
    rows = mirror_documents() + content_assets() + application_and_video_assets()
    missing = [row for row in rows if not row["exists"]]
    catalog = json.loads((DASH / "content_publishing_catalog.json").read_text(encoding="utf-8"))
    sources = data_source_freshness()
    payload = {
        "schema": "clawstack.growth_dashboard_asset_access_audit.v1",
        "updated_at": now_iso(), "catalog_updated_at": catalog.get("updated_at"),
        "total_assets": len(rows), "available_assets": len(rows) - len(missing),
        "missing_assets": len(missing),
        "data_sources": sources,
        "stale_data_sources": sum(1 for source in sources if source["stale_over_48h"]),
        "rows": rows,
    }
    output = DASH / "asset_access_audit.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] dashboard asset audit total={len(rows)} missing={len(missing)} output={output}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
