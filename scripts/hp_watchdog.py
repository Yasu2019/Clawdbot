# -*- coding: utf-8 -*-
"""YNS-PC-HP watchdog: monitor K10 and report liveness centrally."""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.parse
import urllib.request
from datetime import datetime

K10_METRICS_URL = "http://100.119.18.40:8111/metrics"
K10_HEARTBEAT_URL = "http://100.119.18.40:8113/fleet_evidence"
BOT_TOKEN = os.environ.get("CLAWSTACK_TELEGRAM_BOT_TOKEN", "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4")
CHAT_ID = os.environ.get("CLAWSTACK_TELEGRAM_CHAT_ID", "8173025084")
CHECK_INTERVAL_SEC = 300
FAIL_THRESHOLD = 3


def check_internet() -> bool:
    try:
        req = urllib.request.Request("http://1.1.1.1", method="HEAD")
        with urllib.request.urlopen(req, timeout=5):
            return True
    except Exception:
        return False


def check_k10() -> bool:
    try:
        req = urllib.request.Request(K10_METRICS_URL)
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status == 200
    except Exception:
        return False


def report_heartbeat(k10_ok: bool, consecutive_failures: int) -> bool:
    payload = {
        "schema": "clawstack.hp_k10_watchdog.v1",
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "watchdog": "hp_watchdog",
        "k10_ok": bool(k10_ok),
        "consecutive_failures": int(consecutive_failures),
        "check_interval_sec": CHECK_INTERVAL_SEC,
        "fail_threshold": FAIL_THRESHOLD,
    }
    try:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            K10_HEARTBEAT_URL,
            data=raw,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except Exception:
        return False


def send_alert() -> None:
    try:
        hostname = socket.gethostname()
        text = (
            "🚨 [緊急SOS] K10 (100.119.18.40) が応答しません。\n"
            f"YNS-PC-HPによる連続3回の監視失敗です。 (Reported by {hostname})"
        )
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        print(f"Failed to send Telegram alert: {exc}", flush=True)


def main() -> None:
    print(f"Starting HP Watchdog on {socket.gethostname()}...", flush=True)
    consecutive_failures = 0
    while True:
        try:
            if check_internet():
                k10_ok = check_k10()
                if k10_ok:
                    consecutive_failures = 0
                    report_heartbeat(True, consecutive_failures)
                else:
                    consecutive_failures += 1
                    print(
                        f"[Warning] K10 missed heartbeat {consecutive_failures}/{FAIL_THRESHOLD}",
                        flush=True,
                    )
                    if consecutive_failures == FAIL_THRESHOLD:
                        send_alert()
                        time.sleep(3600)
                        consecutive_failures = 0
            else:
                consecutive_failures = 0
        except Exception as exc:
            print(f"[Warning] watchdog loop: {exc}", flush=True)
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
