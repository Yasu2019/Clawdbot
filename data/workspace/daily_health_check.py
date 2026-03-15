#!/usr/bin/env python3
"""
daily_health_check.py — 毎日システム全体チェック
1. Gemini API 無駄消費チェック（LiteLLMエラーループ検知）
2. システム全体ヘルスチェック（コンテナ・デーモン・Qdrant）
3. 無駄なファイル・ディスク使用チェック

実行: docker exec clawstack-unified-clawdbot-gateway-1 python3 /home/node/clawd/daily_health_check.py
"""
import json
import os
import re
import subprocess
import sys
import time
import requests
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)
REPORT = []
ALERTS = []

QDRANT_URL   = "http://qdrant:6333"
LITELLM_URL  = "http://litellm:4000"
OLLAMA_URL   = "http://ollama:11434"
INFINITY_URL = "http://infinity:7997"

LOG_FILE = "/home/node/clawd/daily_health_check.log"

# ── ユーティリティ ──────────────────────────────────────────────────────────────
def section(title):
    REPORT.append(f"\n{'='*40}")
    REPORT.append(f"  {title}")
    REPORT.append(f"{'='*40}")

def ok(msg):
    REPORT.append(f"  OK   {msg}")

def warn(msg):
    REPORT.append(f"  WARN {msg}")
    ALERTS.append(msg)

def info(msg):
    REPORT.append(f"       {msg}")

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def http_get(url, timeout=8):
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code, r.text[:200]
    except Exception as e:
        return 0, str(e)

# ── 1. Gemini API 無駄消費チェック ───────────────────────────────────────────────
def check_gemini_waste():
    section("1. Gemini API 無駄消費チェック")
    try:
        # LiteLLMログを取得（直近500行）
        logs = run("docker logs clawstack-unified-litellm-1 --tail 500 2>&1")
        lines = logs.splitlines()

        cnt_429      = sum(1 for l in lines if "429" in l and "RESOURCE_EXHAUSTED" in l)
        cnt_nomic    = sum(1 for l in lines if "nomic-embed-text" in l and "chat" in l)
        cnt_fallback = sum(1 for l in lines if "Fail Calls made" in l)

        info(f"Gemini 429エラー数 (直近500行): {cnt_429}")
        info(f"nomic→chat誤送信エラー数:       {cnt_nomic}")
        info(f"fallback発火回数:               {cnt_fallback}")

        if cnt_429 > 10:
            warn(f"Gemini 429が{cnt_429}回 — API無駄消費ループの可能性あり")
        elif cnt_429 > 0:
            warn(f"Gemini 429が{cnt_429}回 — 監視継続")
        else:
            ok("Gemini 429エラーなし")

        if cnt_nomic > 5:
            warn(f"nomic→chat誤送信が{cnt_nomic}回 — LiteLLM設定要確認")
        elif cnt_nomic == 0:
            ok("nomic-embed-text chat誤送信なし")

        # LiteLLM自体の応答確認
        code, _ = http_get(f"{LITELLM_URL}/health")
        if code == 200:
            ok("LiteLLM ヘルス: 正常")
        else:
            warn(f"LiteLLM ヘルス: HTTP {code}")

    except Exception as e:
        warn(f"Geminiチェックエラー: {e}")


# ── 2. システム全体ヘルスチェック ────────────────────────────────────────────────
def check_system_health():
    section("2. システム全体ヘルスチェック")

    # 2-A サービスエンドポイント稼働確認（HTTP）
    info("[サービスヘルス]")
    endpoints = [
        # Core AI & Orchestration
        ("OpenClaw Gateway",  "http://clawdbot-gateway:18789"),
        ("LiteLLM",           "http://litellm:4000"),
        ("Ollama",            "http://ollama:11434"),
        ("Infinity",          "http://infinity:7997/health"),
        ("Qdrant",            "http://qdrant:6333"),
        # Document & Search
        ("Paperless",         "http://paperless:8000"),
        ("Docling",           "http://docling:5001/health"),
        ("SearXNG",           "http://searxng:8080"),
        # Automation & UI
        ("n8n",               "http://n8n:5678"),
        ("Node-RED",          "http://nodered:1880"),
        ("Open WebUI",        "http://open_webui:8080"),
        # Storage & Infra
        ("MinIO",             "http://minio:9000"),
        ("Immich",            "http://immich_server:2283"),
        # Observability
        ("Langfuse",          "http://langfuse:3000"),
        ("Prometheus",        "http://prometheus:9090"),
        ("Grafana",           "http://grafana:3000"),
        ("Uptime Kuma",       "http://uptime-kuma:3001"),
        # Data & BI
        ("NocoDB",            "http://nocodb:8080"),
        ("Metabase",          "http://metabase:3000"),
        # Dev Tools & Utilities
        ("Mailpit",           "http://mailpit:8025"),
        ("Excalidraw",        "http://excalidraw:80"),
        ("Dozzle",            "http://dozzle:8080"),
        ("Portainer",         "http://portainer:9000"),
        ("IT-Tools",          "http://it-tools:80"),
        # AI Enrichment
        ("LibreTranslate",    "http://libretranslate:5000"),
        ("Crawl4AI",          "http://crawl4ai:11235"),
        ("Whishper",          "http://whishper:8080"),
        # Knowledge
        ("Outline",           "http://outline:3000"),
    ]
    down_services = []
    for name, url in endpoints:
        code, _ = http_get(url, timeout=10)
        if code in (200, 301, 302, 307, 401, 403):
            ok(f"  {name}: HTTP {code}")
        else:
            warn(f"  {name}: 応答なし (HTTP {code})")
            down_services.append(name)

    if not down_services:
        ok(f"全{len(endpoints)}サービス 応答確認済み")
    else:
        warn(f"応答なしサービス: {', '.join(down_services)}")

    # 2-B バックグラウンドデーモン確認
    info("[バックグラウンドデーモン]")
    daemon_checks = [
        ("ingest_watchdog", "ingest_watchdog.py"),
        ("ingest_eml_v2",   "ingest_eml_v2.py"),
        ("clawstack_mcp",   "clawstack_mcp_server.py"),
    ]
    ps_output = run("ps aux")
    for name, script in daemon_checks:
        if script in ps_output:
            ok(f"  {name}: 稼働中")
        else:
            warn(f"  {name}: 停止中 ({script})")

    # 2-C Qdrantコレクション確認
    info("[Qdrant]")
    try:
        r = requests.get(f"{QDRANT_URL}/collections", timeout=8)
        collections = r.json()["result"]["collections"]
        for c in collections:
            name = c["name"]
            info_r = requests.get(f"{QDRANT_URL}/collections/{name}", timeout=8).json()
            pts = info_r["result"]["points_count"]
            ok(f"  {name}: {pts:,} points")
    except Exception as e:
        warn(f"  Qdrant確認エラー: {e}")

    # 2-D Ollamaモデル確認
    info("[Ollama モデル]")
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        models = r.json().get("models", [])
        required = ["qwen3:8b", "minicpm-v:latest", "nomic-embed-text:latest"]
        model_names = [m["name"] for m in models]
        for req in required:
            if req in model_names:
                ok(f"  {req}: あり")
            else:
                warn(f"  {req}: なし（必須モデル）")
        ok(f"  総モデル数: {len(models)}")
    except Exception as e:
        warn(f"  Ollama確認エラー: {e}")

    # 2-E n8nアクティブワークフロー確認
    info("[n8n ワークフロー]")
    try:
        r = requests.get(
            "http://n8n:5678/api/v1/workflows",
            headers={"X-N8N-API-KEY": "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"},
            timeout=10,
        )
        wfs = r.json()["data"]
        active = [w for w in wfs if w["active"]]
        inactive = [w for w in wfs if not w["active"]]
        ok(f"  アクティブ: {len(active)}本 / 非アクティブ: {len(inactive)}本")
        # 重複チェック
        names = [w["name"] for w in wfs]
        seen = {}
        for n in names:
            seen[n] = seen.get(n, 0) + 1
        dups = {n: c for n, c in seen.items() if c > 1}
        if dups:
            for n, c in dups.items():
                warn(f"  重複ワークフロー: 「{n}」が{c}個")
        else:
            ok("  重複ワークフローなし")
    except Exception as e:
        warn(f"  n8n確認エラー: {e}")


# ── 3. 無駄なファイル・ディスク使用チェック ──────────────────────────────────────
def check_waste():
    section("3. 無駄なファイル・ディスクチェック")

    # 3-A ログファイルサイズ確認
    info("[ログファイル]")
    log_files = [
        "/home/node/clawd/ingest_watchdog.log",
        "/home/node/clawd/ingest_eml.log",
        "/home/node/clawd/night_backfill.log",
        "/home/node/clawd/workflow_healer.log",
        "/home/node/clawd/daily_health_check.log",
    ]
    for lf in log_files:
        if os.path.exists(lf):
            size_mb = os.path.getsize(lf) / 1e6
            name = os.path.basename(lf)
            if size_mb > 50:
                warn(f"  {name}: {size_mb:.1f}MB — 肥大化（要ローテーション）")
            elif size_mb > 10:
                warn(f"  {name}: {size_mb:.1f}MB — 注意")
            else:
                ok(f"  {name}: {size_mb:.1f}MB")

    # 3-B 停止コンテナ・ダングリングイメージ確認
    info("[Docker 未使用リソース]")
    stopped = run("docker ps -a --filter status=exited --format '{{.Names}}' 2>/dev/null")
    stopped_list = [s for s in stopped.splitlines() if s.strip()]
    if stopped_list:
        warn(f"  停止コンテナ {len(stopped_list)}本あり: {', '.join(stopped_list[:5])}")
    else:
        ok("  停止コンテナなし")

    dangling = run("docker images -f dangling=true -q 2>/dev/null")
    dangling_count = len([d for d in dangling.splitlines() if d.strip()])
    if dangling_count > 5:
        warn(f"  未使用Dockerイメージ: {dangling_count}個（docker image prune 推奨）")
    elif dangling_count > 0:
        info(f"  未使用Dockerイメージ: {dangling_count}個")
    else:
        ok("  未使用Dockerイメージなし")

    # 3-C ワークスペース内の大きなファイル確認
    info("[ワークスペース 大きなファイル]")
    ws = "/home/node/clawd"
    large_files = []
    try:
        for fname in os.listdir(ws):
            fpath = os.path.join(ws, fname)
            if os.path.isfile(fpath):
                size_mb = os.path.getsize(fpath) / 1e6
                if size_mb > 5:
                    large_files.append((size_mb, fname))
        large_files.sort(reverse=True)
        if large_files:
            for size_mb, fname in large_files[:5]:
                info(f"  {fname}: {size_mb:.1f}MB")
        else:
            ok("  大きなファイルなし（>5MB）")
    except Exception as e:
        warn(f"  ファイルチェックエラー: {e}")

    # 3-D /tmp の容量確認
    info("[/tmp ディレクトリ]")
    tmp_size = run("du -sh /tmp 2>/dev/null | cut -f1")
    if tmp_size:
        info(f"  /tmp 使用量: {tmp_size}")
        try:
            val = float(tmp_size.replace("G","000").replace("M","").replace("K","0.001").replace("B","0.0001"))
            if val > 500:
                warn(f"  /tmp が {tmp_size} — クリーン推奨")
        except Exception:
            pass


# ── メイン ────────────────────────────────────────────────────────────────────────
def main():
    REPORT.append(f"Daily Health Check — {NOW.strftime('%Y-%m-%d %H:%M JST')}")

    check_gemini_waste()
    check_system_health()
    check_waste()

    # サマリー
    section("サマリー")
    if ALERTS:
        REPORT.append(f"  WARNING {len(ALERTS)}件:")
        for a in ALERTS:
            REPORT.append(f"    * {a}")
    else:
        REPORT.append("  全項目 正常")

    report_text = "\n".join(REPORT)

    # ログ保存
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(report_text + "\n\n")
    except Exception:
        pass

    print(report_text)
    return report_text


if __name__ == "__main__":
    main()
