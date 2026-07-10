# -*- coding: utf-8 -*-
"""自己修復パルス: Task Scheduler非依存の常駐第2起動経路(多重化の要)。

背景(2026-07-10): 日次スケジュールタスクが7/7から3日間無実行=Task Scheduler層
自体が単一障害点だった。本パルスはスタートアップフォルダ起動の常駐プロセスとして
毎時 self_heal_loops.py を実行する。両者は独立経路なので片方が死んでも復旧が走る。

- T056準拠: 起動時に自分以外のpulseインスタンスを掃除(単一化)
- escalate_humanが出た場合はローカルLLM一次診断(self_heal_diagnose_llm.py)を起動
- 自身のheartbeatを毎時記録(heartbeat_manifest登録済み→dead_project_recheckが監視)
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import os
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "data" / "workspace"
JST = timezone(timedelta(hours=9))
PULSE_STATUS = WS / "self_heal_pulse_status.json"
INTERVAL_SEC = 3600


def ensure_single_instance() -> None:
    """T056: 自分以外のpulseを掃除して単一化(Windows前提・失敗しても続行)。"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"name like 'python%'\" | "
             "Where-Object { $_.CommandLine -match 'self_heal_pulse' -and $_.ProcessId -ne " + str(os.getpid()) + " } | "
             "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $_.ProcessId }"],
            capture_output=True, text=True, timeout=60)
        killed = (out.stdout or "").split()
        if killed:
            print(f"[pulse] T056 cleanup: {killed}")
    except Exception:
        pass


def run_once() -> None:
    started = datetime.now(JST).isoformat()
    rc = None
    try:
        rc = subprocess.run([sys.executable, str(ROOT / "scripts" / "self_heal_loops.py")],
                            timeout=900).returncode
    except Exception as exc:
        rc = f"error:{exc}"[:100]
    # escalate_humanが直近runに出ていればLLM一次診断(助言のみ・実行はしない)
    try:
        st = json.loads((WS / "self_heal_status.json").read_text(encoding="utf-8"))
        if any(a.get("action") == "escalate_human" for a in st.get("actions", [])):
            subprocess.run([sys.executable, str(ROOT / "scripts" / "self_heal_diagnose_llm.py")],
                           timeout=600)
    except Exception:
        pass
    PULSE_STATUS.write_text(json.dumps({
        "schema": "clawstack.self_heal_pulse.v1",
        "checked_at": datetime.now(JST).isoformat(),
        "started_at": started, "self_heal_rc": rc, "pid": os.getpid(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ensure_single_instance()
    print(f"[pulse] 常駐開始 pid={os.getpid()} interval={INTERVAL_SEC}s")
    while True:
        run_once()
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    raise SystemExit(main())
