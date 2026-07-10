# -*- coding: utf-8 -*-
"""成長ループ監査 (Growth Loop Audit) — 偽成長の決定論的検出

docs/growth_loop_quality_protocol.md 第3条の実装。
登録簿 data/workspace/growth_loop_manifest.json の各ループについて、
ログを外部から読み以下を機械計算する (LLM不使用・再現可能):

  G1 物理妥当性: SUCCESS試行のKPIが宣言界内か (界外率 > tol で違反)
  G2 情報増加:   KPI平均の前半/後半 相対変化 < しきい値 かつ 成功率<100% で停滞
  G4 学習反映:   探索パラメータの前半/後半 標準化平均シフトが全て微小なら学習不在
  (G3 ゴールデン誤差は各ループが記録し、本監査は定義有無のみ確認)

判定: FAKE_GROWTH = G1違反 or (G2停滞 and G4学習不在)
      SUSPECT     = G2停滞 xor G4学習不在 or ゴールデン未定義
      HEALTHY     = 上記なし

実行: python scripts/growth_loop_audit.py [--telegram]
出力: data/workspace/growth_loop_audit_status.json / 違反時exit 1
テスト: data/workspace/tests/test_growth_loop_audit.py
"""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "workspace" / "growth_loop_manifest.json"
OUT_STATUS = ROOT / "data" / "workspace" / "growth_loop_audit_status.json"

SUCCESS_VERDICTS = {"SUCCESS", "PASS"}
# G4: 標準化平均シフト(|mean差|/プールstd)がこの値未満のパラメータしか無ければ学習不在
PARAM_SHIFT_MIN = 0.15


# ---------------------------------------------------------------------------
# 純関数 (テスト対象)
# ---------------------------------------------------------------------------

def get_path(obj: dict, dotted: str):
    """ドット記法でネスト値を取得。無ければ None。"""
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def first_kpi(trial: dict, fields: list):
    for f in fields:
        v = get_path(trial, f)
        if v is not None:
            try:
                return float(str(v).rstrip("%"))
            except (TypeError, ValueError):
                continue
    return None


def _mean(xs): return sum(xs) / len(xs) if xs else None


def _std(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def check_g1_validity(trials: list, spec: dict) -> dict:
    """G1: SUCCESS試行のKPIが物理界内か。"""
    kpi = spec["kpi"]
    vals = [first_kpi(t, kpi["fields"]) for t in trials
            if (t.get("verdict") or "").upper() in SUCCESS_VERDICTS]
    vals = [v for v in vals if v is not None]
    if not vals:
        return {"gate": "G1", "ok": True, "samples": 0,
                "note": "KPI付きSUCCESSなし(判定不能)"}
    bad = sum(1 for v in vals
              if v < kpi.get("physical_min", -math.inf)
              or v > kpi.get("physical_max", math.inf))
    rate = round(100.0 * bad / len(vals), 1)
    ok = rate <= float(kpi.get("violation_tol_pct", 20.0))
    return {"gate": "G1", "ok": ok, "samples": len(vals),
            "nonphysical_pct": rate,
            "note": f"界外 {bad}/{len(vals)} ({rate}%)"}


def check_g2_information(trials: list, spec: dict) -> dict:
    """G2: 停滞窓内でKPI平均が動かず、かつ成功率<100% なら情報増加ゼロ。"""
    stag = spec.get("stagnation", {})
    window = int(stag.get("window", 50))
    min_rel = float(stag.get("min_rel_change_pct", 2.0))
    recent = trials[-window:]
    vals = [first_kpi(t, spec["kpi"]["fields"]) for t in recent]
    vals = [v for v in vals if v is not None]
    if len(vals) < max(10, window // 4):
        return {"gate": "G2", "ok": True, "samples": len(vals),
                "note": "試行数不足(判定保留)"}
    half = len(vals) // 2
    m1, m2 = _mean(vals[:half]), _mean(vals[half:])
    denom = abs(m1) if abs(m1) > 1e-9 else 1.0
    rel = round(100.0 * abs(m2 - m1) / denom, 2)
    n_s = sum(1 for t in recent
              if (t.get("verdict") or "").upper() in SUCCESS_VERDICTS)
    all_success = n_s == len(recent) and len(recent) > 0
    stagnant = rel < min_rel and not all_success
    return {"gate": "G2", "ok": not stagnant, "samples": len(vals),
            "kpi_rel_change_pct": rel,
            "note": f"KPI平均変化 {rel}% (要求≥{min_rel}%) 成功率{round(100*n_s/max(1,len(recent)))}%"}


def check_g4_learning(trials: list, spec: dict) -> dict:
    """G4: 探索パラメータ分布が前半/後半で動いているか。"""
    params = spec.get("params", [])
    if not params or len(trials) < 20:
        return {"gate": "G4", "ok": True, "note": "パラメータ未宣言or試行不足(保留)"}
    half = len(trials) // 2
    shifts = {}
    for p in params:
        a = [get_path(t, p) for t in trials[:half]]
        b = [get_path(t, p) for t in trials[half:]]
        a = [float(x) for x in a if isinstance(x, (int, float))]
        b = [float(x) for x in b if isinstance(x, (int, float))]
        if len(a) < 5 or len(b) < 5:
            continue
        pooled = _std(a + b)
        if pooled < 1e-12:
            shifts[p] = 0.0  # 完全固定 = シフトなし
            continue
        shifts[p] = round(abs(_mean(b) - _mean(a)) / pooled, 3)
    if not shifts:
        return {"gate": "G4", "ok": True, "note": "数値パラメータなし(保留)"}
    max_shift = max(shifts.values())
    ok = max_shift >= PARAM_SHIFT_MIN
    return {"gate": "G4", "ok": ok, "max_param_shift": max_shift,
            "shifts": shifts,
            "note": f"最大分布シフト {max_shift} (要求≥{PARAM_SHIFT_MIN}) — 乱数再抽選は探索ではない"}


def check_g3_golden(spec: dict) -> dict:
    """G3基準相関: error_log_path定義を必須とし、golden.verify_log=true なら
    実績(誤差ログの存在+直近誤差<=max_err_pct)まで決定論検証する(2026-07-10強化)。"""
    g = spec.get("golden") or {}
    path = g.get("error_log_path")
    if not path:
        return {"gate": "G3", "ok": False,
                "note": f"未定義: {g.get('status', 'ゴールデンケースなし')}"}
    if not g.get("verify_log"):
        return {"gate": "G3", "ok": True, "note": "ゴールデンケース定義済み(実績検証はverify_log未設定)"}
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / path
    if not p.exists():
        return {"gate": "G3", "ok": False,
                "note": "定義済みだが誤差ログ未生成 — ゴールデン未実行(ループ停止の疑い)"}
    last = None
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
    if last is None:
        return {"gate": "G3", "ok": False, "note": "誤差ログに有効レコードなし"}
    err = last.get("max_err_pct")
    if err is None:
        errs = [v.get("err_pct") for v in (last.get("per_variant") or {}).values()
                if isinstance(v, dict) and isinstance(v.get("err_pct"), (int, float))]
        err = max(errs) if errs else None
    limit = g.get("max_err_pct")
    if err is not None and limit is not None and float(err) > float(limit):
        return {"gate": "G3", "ok": False, "err_pct": float(err),
                "note": f"直近ゴールデン誤差 {err}% > 許容 {limit}%"}
    return {"gate": "G3", "ok": True,
            "err_pct": (float(err) if err is not None else None),
            "note": f"ゴールデン実績あり(直近誤差 {err}%)"}


def audit_loop(trials: list, spec: dict) -> dict:
    g1 = check_g1_validity(trials, spec)
    g2 = check_g2_information(trials, spec)
    g3 = check_g3_golden(spec)
    g4 = check_g4_learning(trials, spec)
    if not g1["ok"] or (not g2["ok"] and not g4["ok"]):
        verdict = "FAKE_GROWTH"
    elif not g2["ok"] or not g4["ok"] or not g3["ok"]:
        verdict = "SUSPECT"
    else:
        verdict = "HEALTHY"
    return {"name": spec.get("name"), "verdict": verdict,
            "trials": len(trials), "gates": [g1, g2, g3, g4]}


def build_report_text(reports: list, checked_at: str) -> str:
    lines = ["🔬 成長ループ監査 " + checked_at]
    worst = {"FAKE_GROWTH": 0, "SUSPECT": 0, "HEALTHY": 0}
    for r in reports:
        worst[r["verdict"]] += 1
    lines.append(f"HEALTHY {worst['HEALTHY']} / SUSPECT {worst['SUSPECT']} / "
                 f"FAKE_GROWTH {worst['FAKE_GROWTH']}")
    for r in reports:
        if r["verdict"] == "HEALTHY":
            continue
        mark = "🟥" if r["verdict"] == "FAKE_GROWTH" else "🟨"
        lines.append(f"{mark} {r['name']} = {r['verdict']} (n={r['trials']})")
        for g in r["gates"]:
            if not g["ok"]:
                lines.append(f"   ❌ {g['gate']}: {g['note']}")
    if worst["FAKE_GROWTH"]:
        lines.append("→ 48h以内に是正 or ループ停止 (growth_loop_quality_protocol.md)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ログ読込 (書き込み途中に耐えるプレフィックス逐次デコード)
# ---------------------------------------------------------------------------

def load_trials_cae_te_log(path: Path, categories: list) -> list:
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    i = txt.find('"trials"')
    if i < 0:
        return []
    i = txt.find("[", i) + 1
    dec = json.JSONDecoder()
    out = []
    while True:
        while i < len(txt) and txt[i] in " \t\r\n,":
            i += 1
        if i >= len(txt) or txt[i] == "]":
            break
        try:
            obj, i = dec.raw_decode(txt, i)
        except Exception:
            break  # 書き込み途中: ここまでの完全なレコードで監査
        if (obj.get("category") or "") in categories:
            out.append(obj)
    out.sort(key=lambda t: t.get("timestamp", ""))
    return out


def load_trials_jsonl(path: Path, categories: list) -> list:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not categories or (obj.get("category") or "") in categories:
            out.append(obj)
    out.sort(key=lambda t: t.get("timestamp", ""))
    return out


def load_trials(spec: dict, root: Path) -> list:
    log = spec.get("log", {})
    path = root / log.get("path", "")
    cats = log.get("categories", [])
    if log.get("format") == "jsonl":
        return load_trials_jsonl(path, cats)
    return load_trials_cae_te_log(path, cats)


def main() -> int:
    parser = argparse.ArgumentParser(description="成長ループ監査")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--telegram", action="store_true")
    args = parser.parse_args()

    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[error] 登録簿読込失敗: {exc}", file=sys.stderr)
        return 2

    checked_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    reports = []
    for spec in manifest.get("loops", []):
        trials = load_trials(spec, ROOT)
        reports.append(audit_loop(trials, spec))

    text = build_report_text(reports, checked_at)
    print(text)

    OUT_STATUS.write_text(json.dumps({
        "schema": "clawstack.growth_loop_audit.v1",
        "checked_at": datetime.now().astimezone().isoformat(),
        "reports": reports,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    bad = any(r["verdict"] != "HEALTHY" for r in reports)
    if args.telegram and bad:
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            from dead_project_recheck import send_telegram
            send_telegram(text)
        except Exception as exc:
            print(f"[warn] Telegram送信失敗: {exc}", file=sys.stderr)
    return 1 if any(r["verdict"] == "FAKE_GROWTH" for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
