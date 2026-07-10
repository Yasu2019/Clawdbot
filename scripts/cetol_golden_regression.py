# -*- coding: utf-8 -*-
"""CETOL 6σ ゴールデン回帰: 既知解の公差スタック3ケースをHub API(:8004)で日次検証し
誤差推移を記録する(商用接近の証拠=G3基盤・決定論・LLM不使用)。

- 解析解(WC/RSS)と突合。MCはRSS近傍±閾値で判定
- API停止時は verdict=API_OFFLINE を記録(偽PASSしない)
- 出力: data/workspace/cetol_golden_error_log.jsonl(追記) + cetol_golden_status.json

実行: python scripts/cetol_golden_regression.py
登録: scripts/register_cetol_golden_task.bat (毎日07:40)
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "data" / "workspace"
API = "http://127.0.0.1:8004/api/tolerance-stack"
LOG = WS / "cetol_golden_error_log.jsonl"
STATUS = WS / "cetol_golden_status.json"
JST = timezone(timedelta(hours=9))

# 既知解ゴールデン(dims: (nominal, ±tol)。WC=Σtol, RSS=sqrt(Σtol^2))
GOLDEN_CASES = [
    {"id": "g1_two_plates", "dims": [(10.0, 0.1), (20.0, 0.2)]},
    {"id": "g2_five_stack", "dims": [(5.0, 0.05)] * 5},
    {"id": "g3_asym_mix", "dims": [(12.5, 0.15), (3.2, 0.02), (8.0, 0.08)]},
]
MC_TOL_PCT = 15.0  # モンテカルロはRSSの±15%以内を要求(サンプリング誤差許容)
EXACT_TOL_PCT = 0.5  # WC/RSSは解析解一致(0.5%以内)を要求


def analytic(dims):
    wc = sum(t for _, t in dims)
    rss = math.sqrt(sum(t * t for _, t in dims))
    return wc, rss


def call_api(case) -> dict | None:
    payload = json.dumps({
        "stack": [{"nominal": n, "tolerance": t} for n, t in case["dims"]],
        "method": "all",
    }).encode("utf-8")
    req = urllib.request.Request(API, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def evaluate(case, resp: dict) -> dict:
    wc_ref, rss_ref = analytic(case["dims"])
    out = {"case": case["id"], "wc_ref": round(wc_ref, 6), "rss_ref": round(rss_ref, 6)}
    errs = []
    for key, ref, tol_pct in (("wc", wc_ref, EXACT_TOL_PCT), ("rss", rss_ref, EXACT_TOL_PCT),
                              ("mc", rss_ref, MC_TOL_PCT)):
        got = resp.get(key) or resp.get(f"{key}_result") or resp.get(f"{key}_tolerance")
        if isinstance(got, dict):
            got = got.get("tolerance") or got.get("value") or got.get("total")
        if got is None:
            out[f"{key}_err_pct"] = None
            continue
        err = abs(float(got) - ref) / ref * 100.0
        out[key] = float(got)
        out[f"{key}_err_pct"] = round(err, 3)
        out[f"{key}_ok"] = err <= tol_pct
        errs.append(err)
    out["max_err_pct"] = round(max(errs), 3) if errs else None
    return out


def main() -> int:
    now = datetime.now(JST).isoformat()
    results, offline = [], False
    for case in GOLDEN_CASES:
        resp = call_api(case)
        if resp is None:
            offline = True
            results.append({"case": case["id"], "verdict": "API_OFFLINE"})
            continue
        results.append(evaluate(case, resp))
    all_ok = (not offline) and all(
        r.get("wc_ok") and r.get("rss_ok") and (r.get("mc_ok") is not False)
        for r in results if "verdict" not in r)
    record = {"at": now, "verdict": "API_OFFLINE" if offline else ("PASS" if all_ok else "FAIL"),
              "max_err_pct": max((r.get("max_err_pct") or 0.0) for r in results) if not offline else None,
              "results": results}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    STATUS.write_text(json.dumps({"schema": "clawstack.cetol_golden.v1",
                                  "checked_at": now, **record}, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0 if record["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
