# -*- coding: utf-8 -*-
"""自己修復ハーネス: 学習ループの停止を検知し安全な範囲で自動復旧する(K10ホスト・毎時)。

対象と処方(2026-07-10 ユーザー承認・全て決定論):
1. tri-track(Moldflow/OpenRadioss): status stale>2h → watchdog ps1 再実行(冪等)
2. メカsupervisor: stale>4h かつ state∈busy かつ 学習プロセス不在
   → T054復旧2点セット(request→retargeted / supervisor→escalated)

安全設計(T054教訓「ガーディアンの自己破壊」対策):
- data/workspace/MAINTENANCE_LOCK が存在する間は一切行動しない
- 同一対象への復旧は24hに最大2回(self_heal_status.jsonで管理)。超過は人間へ委ねる
- 全行動を self_heal_log.jsonl に追記(監査可能)
- --dry-run で判断のみ表示

実行: python scripts/self_heal_loops.py [--dry-run]
登録: scripts/register_self_heal_task.bat (毎時+起動時)
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
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "data" / "workspace"
JST = timezone(timedelta(hours=9))

TRITRACK_STATUS = WS / "k10_tri_track_cae_status.json"
SUPERVISOR_STATUS = WS / "apps" / "mecha_motion_lab" / "supervisor_status.json"
SKILL_REQUESTS = WS / "apps" / "mecha_motion_lab" / "skill_requests.json"
WATCHDOG_PS1 = ROOT / "scripts" / "start_k10_tri_track_cae_watchdog.ps1"
# ps1で復旧する常駐のホワイトリスト(name, statusファイル, stale閾値h, 復旧ps1)
PS1_RECOVERABLES = (
    ("robot_l20_watchdog", WS / "apps" / "growth_dashboard" / "robot_l20_watchdog_status.json", 3.0,
     ROOT / "scripts" / "start_robot_l20_autonomous_watchdog.ps1"),
)
LOCK = WS / "MAINTENANCE_LOCK"
STATUS_OUT = WS / "self_heal_status.json"
LOG_OUT = WS / "self_heal_log.jsonl"

TRITRACK_STALE_H = 2.0
CHECKER_STALE_H = 26.0  # 死活再チェック/成長監査自身のstale閾値(プロトコル§9)
CHECKERS = (
    ("growth_loop_audit", WS / "growth_loop_audit_status.json",
     ROOT / "scripts" / "growth_loop_audit.py", ()),
    ("dead_project_recheck", WS / "dead_project_recheck_status.json",
     ROOT / "scripts" / "dead_project_recheck.py", ()),
    ("commercial_benchmark_maturity", WS / "apps" / "growth_dashboard" / "commercial_benchmark_maturity_latest.json",
     WS / "commercial_benchmark_maturity.py",
     ("--out", str(WS / "apps" / "growth_dashboard" / "commercial_benchmark_maturity_latest.json"))),
)
SUPERVISOR_STALE_H = 4.0
MAX_ACTIONS_PER_24H = 2
BUSY_STATES = ("running", "training", "checking")


def read_json_tolerant(path: Path, retries: int = 4):
    for _ in range(retries):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            time.sleep(1.5)
    return None


def age_hours(ts: str | None, now: datetime) -> float | None:
    if not ts:
        return None
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=JST)
    return (now - t).total_seconds() / 3600.0


def trainer_process_running() -> bool:
    """v50学習プロセス(genesis venv python)の生存確認。判定不能時はTrue=行動しない(安全側)。"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"name like 'python%'\" | "
             "Where-Object { $_.CommandLine -match 'v50_work|train_v50|motion_learning' }).Count"],
            capture_output=True, text=True, timeout=60)
        return int((out.stdout or "0").strip() or 0) > 0
    except Exception:
        return True


def decide_actions(now: datetime, tri: dict | None, sup: dict | None,
                   trainer_alive: bool, recent_action_counts: dict) -> list[dict]:
    """純関数: 状態から実施すべき復旧アクションを決める(単体テスト対象)。"""
    actions: list[dict] = []
    tri_age = age_hours((tri or {}).get("updated_at"), now)
    if tri is None or tri_age is None or tri_age > TRITRACK_STALE_H:
        if recent_action_counts.get("restart_tritrack", 0) < MAX_ACTIONS_PER_24H:
            actions.append({"action": "restart_tritrack",
                            "reason": f"tri-track status stale ({tri_age if tri_age is not None else 'unreadable'}h > {TRITRACK_STALE_H}h)"})
        else:
            actions.append({"action": "escalate_human", "target": "tritrack",
                            "reason": "24h内の自動復旧上限到達 — 根本原因調査が必要"})
    sup_age = age_hours((sup or {}).get("updated_at"), now)
    if sup and sup_age is not None and sup_age > SUPERVISOR_STALE_H and sup.get("state") in BUSY_STATES:
        if trainer_alive:
            pass  # 学習プロセス生存中の長時間学習は正常
        elif recent_action_counts.get("reset_supervisor", 0) < MAX_ACTIONS_PER_24H:
            actions.append({"action": "reset_supervisor",
                            "reason": f"supervisor state={sup.get('state')} が{sup_age:.1f}h停滞かつ学習プロセス不在(T054型)"})
        else:
            actions.append({"action": "escalate_human", "target": "supervisor",
                            "reason": "24h内の自動復旧上限到達"})
    return actions


def load_recent_action_counts(now: datetime) -> dict:
    counts: dict = {}
    if not LOG_OUT.exists():
        return counts
    for line in LOG_OUT.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        a = age_hours(rec.get("at"), now)
        if a is not None and a <= 24 and rec.get("executed"):
            counts[rec.get("action")] = counts.get(rec.get("action"), 0) + 1
    return counts


def execute(action: dict, dry: bool) -> bool:
    if dry:
        return False
    if action["action"].startswith("restart_") and action.get("ps1"):
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", action["ps1"]], timeout=120)
        return True
    if action["action"] == "restart_progressive_die_hub":
        subprocess.run(["docker", "compose", "up", "-d", "progressive_die_hub"],
                       cwd=str(ROOT), timeout=300)
        # 起動後にゴールデン回帰を再実行して結果を残す
        subprocess.run([sys.executable, str(ROOT / "scripts" / "cetol_golden_regression.py")], timeout=300)
        return True
    if action["action"] == "run_checker":
        subprocess.run([sys.executable, action["script"], *action.get("args", [])], timeout=600)
        return True
    if action["action"] == "restart_tritrack":
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(WATCHDOG_PS1)],
                       timeout=120)
        return True
    if action["action"] == "reset_supervisor":
        sup = read_json_tolerant(SUPERVISOR_STATUS) or {}
        sup["state"] = "escalated"
        sup["escalation_reason"] = f"self_heal: stale {sup.get('state')} auto-reset {datetime.now(JST).isoformat()}"
        SUPERVISOR_STATUS.write_text(json.dumps(sup, ensure_ascii=False, indent=2), encoding="utf-8")
        req = read_json_tolerant(SKILL_REQUESTS) or {}
        skill = str(sup.get("skill", "")).split("_")[0]
        for q in req.get("requests", []):
            if q.get("status") in ("dispatched", "training") or (skill and skill in str(q.get("text", ""))):
                q["status"] = "retargeted"
                q["note"] = "self_heal auto-reset (T054 2点セット)"
        SKILL_REQUESTS.write_text(json.dumps(req, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    return False  # escalate_human はログ通知のみ


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    now = datetime.now(JST)
    if LOCK.exists():
        print(f"[skip] MAINTENANCE_LOCK 存在 — 行動しない(T054ガード)")
        return 0
    tri = read_json_tolerant(TRITRACK_STATUS)
    sup = read_json_tolerant(SUPERVISOR_STATUS)
    counts = load_recent_action_counts(now)
    trainer_alive = trainer_process_running()
    actions = decide_actions(now, tri, sup, trainer_alive, counts)
    for name, spath, stale_h, ps1 in PS1_RECOVERABLES:
        st = read_json_tolerant(spath)
        p_age = age_hours((st or {}).get("checked_at") or (st or {}).get("updated_at"), now)
        if (st is None or p_age is None or p_age > stale_h) and ps1.exists():
            key = f"restart_{name}"
            if counts.get(key, 0) < MAX_ACTIONS_PER_24H:
                actions.append({"action": key, "reason": f"{name} stale ({p_age if p_age is not None else 'unreadable'}h > {stale_h}h)",
                                "ps1": str(ps1)})
            else:
                actions.append({"action": "escalate_human", "target": name, "reason": "24h内の自動復旧上限到達"})
    # 意味ゲート停止の可視化: streak高止まりは自動リセットせず人間へ(T019/T049の趣旨保持)
    for tname, tv in ((tri or {}).get("tracks") or {}).items():
        streak = int((tv or {}).get("fail_streak") or 0)
        if streak >= 8:
            actions.append({"action": "escalate_human", "target": f"track:{tname}",
                            "reason": f"意味ゲート水準の連敗(streak={streak}) — 原因是正+人間承認が必要(自動リセット禁止)"})
    # CETOLゴールデンがAPI_OFFLINE→Hubコンテナを冪等起動(docker compose up -d)
    cg = read_json_tolerant(WS / "cetol_golden_status.json")
    if cg and cg.get("verdict") == "API_OFFLINE":
        if counts.get("restart_progressive_die_hub", 0) < MAX_ACTIONS_PER_24H:
            actions.append({"action": "restart_progressive_die_hub",
                            "reason": "cetol golden = API_OFFLINE (Hub :8004停止)"})
        else:
            actions.append({"action": "escalate_human", "target": "progressive_die_hub",
                            "reason": "24h内の自動復旧上限到達"})
    # 監視役の監視(T-P016教訓): 監査/死活チェッカー自身がstaleなら直接実行して蘇生
    for name, status_path, script, extra_args in CHECKERS:
        st = read_json_tolerant(status_path)
        c_age = age_hours((st or {}).get("checked_at") or (st or {}).get("assessed_at"), now)
        if st is None or c_age is None or c_age > CHECKER_STALE_H:
            actions.append({"action": "run_checker", "target": name,
                            "reason": f"checker stale ({c_age if c_age is not None else 'unreadable'}h > {CHECKER_STALE_H}h)",
                            "script": str(script), "args": list(extra_args)})
    results = []
    with LOG_OUT.open("a", encoding="utf-8") as f:
        for a in actions:
            executed = execute(a, args.dry_run)
            rec = {**a, "at": now.isoformat(), "executed": executed, "dry_run": args.dry_run}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            results.append(rec)
            print(("[DRY] " if args.dry_run else "[DO] ") + json.dumps(rec, ensure_ascii=False))
    STATUS_OUT.write_text(json.dumps({
        "schema": "clawstack.self_heal.v1", "checked_at": now.isoformat(),
        "tritrack_age_h": age_hours((tri or {}).get("updated_at"), now),
        "supervisor_age_h": age_hours((sup or {}).get("updated_at"), now),
        "trainer_alive": trainer_alive, "actions": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if not actions:
        print("[ok] 全ループ健全 — 行動なし")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
