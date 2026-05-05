"""OpenRadioss 結果監視 → Telegram 失敗通知

使い方:
  python openradioss_result_watchdog.py --run-id 44
  python openradioss_result_watchdog.py        # 最新 engine_runXX.log を自動検出

エンジン停止後に .out ファイルを解析し、ABNORMAL TERMINATION を検出した場合に
Telegram に通知する。NORMAL TERMINATION はログのみで通知しない。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp932", "shift_jis", "mbcs"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

ROOT = Path(r"D:\Clawdbot_Docker_20260125")
CONTAINER = "clawstack-unified-openradioss-1"
CONFIG = ROOT / "data" / "state" / "openclaw.json"
STATUS = ROOT / "data" / "workspace" / "openradioss_pdca_status.json"

POLL_SEC = 300          # エンジン稼働中のポーリング間隔（5分）
POLL_SEC_DONE = 30      # 停止後の最終確認待ち
MAX_WAIT_SEC = 24 * 3600  # 最長 24h 監視


# ── Telegram ─────────────────────────────────────────────────────────────
def send_telegram(text: str) -> str:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        token = cfg["channels"]["telegram"]["botToken"]
        chat_ids = [str(x) for x in cfg["channels"]["telegram"]["allowFrom"]]
        chat_id = "8173025084" if "8173025084" in chat_ids else chat_ids[0]
        body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as res:
            return f"sent:{res.status}"
    except Exception as exc:
        return f"failed:{exc}"


# ── コンテナ内ファイル読み取り ───────────────────────────────────────────
def read_container_file(path: str) -> str:
    result = subprocess.run(
        ["docker", "exec", CONTAINER, "cat", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return result.stdout if result.returncode == 0 else ""


def engine_is_running() -> bool:
    """engine.pid が存在し、プロセスが生きているか確認"""
    pid_content = read_container_file("/work/engine.pid").strip()
    if not pid_content:
        return False
    pid = pid_content.split()[0]
    check = subprocess.run(
        ["docker", "exec", CONTAINER, "sh", "-c", f"kill -0 {pid} 2>/dev/null && echo alive"],
        capture_output=True, text=True
    )
    return "alive" in check.stdout


# ── .out ファイル解析 ────────────────────────────────────────────────────
def _docker_exec(cmd: str) -> str:
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "sh", "-c", cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
    )
    return r.stdout if r.returncode == 0 else ""


def parse_out_file(run_id: str) -> dict:
    """engine_runXX.log の末尾 + grep で結果を解析（大ファイル対策）"""
    result: dict = {
        "run_id": run_id,
        "termination": "unknown",
        "t_final": None,
        "cycles": None,
        "elapsed_sec": None,
        "failure_reason": None,
    }

    # 末尾100行で終了判定
    tail = _docker_exec(f"tail -100 /work/engine_run{run_id}.log")
    if not tail:
        tail = _docker_exec("tail -100 /work/4mmx4mm_ASSY_20260105_0001.out")
    if not tail:
        result["failure_reason"] = "output files not found"
        result["termination"] = "abnormal"
        return result

    # ABNORMAL を先に判定（"NORMAL TERMINATION" は "ABNORMAL TERMINATION" の部分文字列のため）
    if any(k in tail for k in ["ABNORMAL TERMINATION", "FATAL ERROR", "STOP DUE TO", "ERROR COUNT"]):
        result["termination"] = "abnormal"
    elif "NORMAL TERMINATION" in tail:
        result["termination"] = "normal"

    # 経過時間（末尾にある）
    m = re.search(r"ELAPSED TIME\s*=\s*([\d.]+)\s*s", tail)
    if m:
        result["elapsed_sec"] = float(m.group(1))

    # 総サイクル数（engine_run ログの末尾に記載）
    m_cyc = re.search(r"TOTAL NUMBER OF CYCLES\s*:\s*(\d+)", tail)
    if m_cyc:
        result["cycles"] = int(m_cyc.group(1))

    # 最終T時刻: TIME : 0.XXXXE-XX 形式をログから取得
    t_matches = re.findall(r"TIME\s*:\s*([\d.E+\-]+)", tail)
    if not t_matches:
        # engine_run ログ全体から最後のTIME行を取得
        t_matches_full = _docker_exec(
            f"grep -oE 'TIME : [0-9.E+-]+' /work/engine_run{run_id}.log 2>/dev/null | tail -1"
        )
        m3 = re.search(r"TIME : ([\d.E+\-]+)", t_matches_full)
        if m3:
            t_matches = [m3.group(1)]
    if t_matches:
        try:
            result["t_final"] = float(t_matches[-1])
        except ValueError:
            pass

    # 失敗理由（FATAL/ABNORMAL/ERROR 行）
    if result["termination"] == "abnormal":
        err_lines = _docker_exec(
            f"grep -E 'FATAL|ABNORMAL|ERROR' /work/engine_run{run_id}.log 2>/dev/null | head -3"
        )
        result["failure_reason"] = err_lines.strip()[:300] or "詳細不明"

    return result


# ── ステータス更新 ────────────────────────────────────────────────────────
def update_status(payload: dict) -> None:
    try:
        existing = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    except Exception:
        existing = {}
    existing.update(payload)
    existing["watchdog_updated_at"] = datetime.now().isoformat(timespec="seconds")
    STATUS.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


# ── メイン監視ループ ──────────────────────────────────────────────────────
def watch(run_id: str) -> None:
    print(f"[watchdog] Run{run_id} 監視開始 (poll={POLL_SEC}s, max={MAX_WAIT_SEC}s)", flush=True)
    update_status({"watchdog_run_id": run_id, "watchdog_phase": "watching"})

    start = time.time()
    while time.time() - start < MAX_WAIT_SEC:
        if not engine_is_running():
            print("[watchdog] エンジン停止を検出。結果確認します...", flush=True)
            time.sleep(POLL_SEC_DONE)  # .out ファイルが flush されるまで少し待つ
            break
        elapsed = int(time.time() - start)
        print(f"[watchdog] エンジン稼働中 (+{elapsed//60}分)...", flush=True)
        time.sleep(POLL_SEC)
    else:
        msg = f"⚠️ OpenRadioss Run{run_id} 監視タイムアウト（{MAX_WAIT_SEC//3600}h超）"
        send_telegram(msg)
        update_status({"watchdog_phase": "timeout"})
        print(msg, flush=True)
        return

    result = parse_out_file(run_id)
    update_status({"watchdog_phase": "done", "watchdog_result": result})

    t_str = f"{result['t_final']:.5f}s" if result["t_final"] else "不明"
    cyc_str = f"{result['cycles']:,}" if result["cycles"] else "不明"
    elapsed_str = f"{result['elapsed_sec']/3600:.1f}h" if result["elapsed_sec"] else "不明"

    if result["termination"] == "normal":
        msg = (
            f"✅ OpenRadioss Run{run_id} 正常完了\n"
            f"T={t_str}  Cycle={cyc_str}  経過={elapsed_str}"
        )
        print(msg, flush=True)
        # 正常終了は通知しない（ログのみ）

    else:
        reason = result.get("failure_reason") or "詳細不明"
        msg = (
            f"❌ OpenRadioss Run{run_id} 異常終了\n"
            f"T={t_str}  Cycle={cyc_str}  経過={elapsed_str}\n"
            f"原因: {reason}"
        )
        tg = send_telegram(msg)
        print(f"[watchdog] Telegram送信: {tg}", flush=True)
        print(msg, flush=True)
        update_status({"watchdog_telegram": tg, "watchdog_failure_msg": msg})


def detect_run_id() -> str:
    """最新の engine_runXX.log から Run ID を自動検出"""
    result = subprocess.run(
        ["docker", "exec", CONTAINER, "sh", "-c", "ls /work/engine_run*.log 2>/dev/null | sort -V | tail -1"],
        capture_output=True, text=True
    )
    match = re.search(r"engine_run(\d+)\.log", result.stdout)
    return match.group(1) if match else "43"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=None, help="Run番号（省略時は自動検出）")
    args = ap.parse_args()

    run_id = args.run_id or detect_run_id()
    watch(run_id)
