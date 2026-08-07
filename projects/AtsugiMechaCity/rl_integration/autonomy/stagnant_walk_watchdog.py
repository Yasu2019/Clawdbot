# -*- coding: utf-8 -*-
"""motion_learning_supervisor(--skill walk_auto等)の「無駄稼働」自動検知・停止watchdog。
2026-07-30 ユーザー承認により導入。

背景: walk_auto(cycle4/6, min_upright=0.0が3サイクル連続=dive_hack/walks_then_fallsで
毎回完全転倒)を目視+supervisor_status.json確認の上で手動停止した。今後は自動検知したい、
というユーザー要望に基づく。

判定基準(ユーザー承認): supervisor_status.json の "history" 配列の**直近N_CONSECUTIVE件**が
全て metrics.min_upright < UPRIGHT_THRESHOLD なら「無駄稼働」と判定する。

安全設計(stop_rogue_walk.py の踏襲。FMEA):
- 停止対象は「motion_learning_supervisor かつ 現在アクティブなskill(status.jsonのskill欄)」の
  プロセスのみ。**PROTECT_TOKENS**(u5/u7/u1/u2/u4/run_robot_l20/stop_rogue_walk/このwatchdog自身)
  を含むプロセスは絶対に停止しない。
- CommandLine列挙は.ps1ファイル方式(インラインクォートは環境依存で壊れる実績あり、2026-07-20)。
- 停止前に全判定根拠をログへ記録(証拠必須)。
- 停止した場合のみ supervisor_status.json の state を "stopped_by_watchdog" にして経緯を記録。
- supervisor_status.json が無い/パース不能/プロセス列挙不能/対象プロセス未発見、いずれの場合も
  「何もしない」を安全側デフォルトとし、判定内容をログ+標準出力へ残す(自動アクション化なし)。
- Windows Task Scheduler から6時間毎に起動される想定
  (register_stagnant_walk_watchdog.ps1参照、/SC HOURLY /MO 6)。
"""
import json, os, subprocess, sys, time

MECHA = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab"
LOG = os.path.join(MECHA, "stagnant_walk_watchdog_log.txt")
SUP_STATUS = os.path.join(MECHA, "supervisor_status.json")
N_CONSECUTIVE = 3
UPRIGHT_THRESHOLD = 0.02
# 死亡判定(2026-08-08追加): state が「動いているはず」なのに status が更新されず、
# 該当プロセスも居ない状態が続いたら死亡とみなす。
# 背景: is_stagnant は history<3件で無条件 False を返すため、history=[] のまま
# 209時間(8.7日)停止していても12回以上のチェックが全部「OK」を返していた。
# 「無駄に動き続けている」しか見ておらず「動いていない」が素通りする盲点だった。
DEAD_AFTER_HOURS = 12.0
ACTIVE_STATES = ("running", "training", "checking", "escalated")
NOTIFY_COOLDOWN_HOURS = 24.0

PROTECT_TOKENS = ["u5_train_dispatcher", "u7_queue_daemon", "u1_interpreter",
                  "u2_reference_finder", "u4_retarget_runner", "run_robot_l20",
                  "stop_rogue_walk", "stagnant_walk_watchdog"]


def _log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")


def list_python_processes():
    """[(pid, commandline)] を返す。取得不能なら None。

    stop_rogue_walk.py と同じ.ps1ファイル方式(-Commandのインラインクォートは
    環境依存で壊れ0件を返す事故が実証済み、2026-07-20)。"""
    tmpdir = os.path.join(MECHA, "_watchdog_tmp")
    os.makedirs(tmpdir, exist_ok=True)
    ps1 = os.path.join(tmpdir, "enum_python.ps1")
    outjson = os.path.join(tmpdir, "enum_python.json")
    try:
        if os.path.exists(outjson):
            os.remove(outjson)
    except Exception:
        pass
    script = (
        "$ErrorActionPreference='SilentlyContinue'\n"
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Depth 3 | "
        f"Out-File -Encoding utf8 -FilePath '{outjson}'\n")
    with open(ps1, "w", encoding="utf-8") as f:
        f.write(script)
    try:
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile",
                        "-File", ps1], capture_output=True, text=True, timeout=60)
    except Exception as e:
        _log(f"list_python_processes ps run error: {type(e).__name__}: {e}")
        return None
    try:
        if not os.path.exists(outjson):
            _log("enum json missing after ps run")
            return None
        raw = open(outjson, encoding="utf-8-sig", errors="replace").read().strip()
        if not raw:
            return []
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        return [(d.get("ProcessId"), d.get("CommandLine")) for d in data]
    except Exception as e:
        _log(f"list_python_processes parse error: {type(e).__name__}: {e}")
        return None


def kill_pid(pid):
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Stop-Process -Id {int(pid)} -Force -ErrorAction SilentlyContinue"],
                       capture_output=True, text=True, timeout=30)
        return True
    except Exception as e:
        _log(f"kill {pid} error: {type(e).__name__}: {e}")
        return False


def is_stagnant(status):
    """directly reads history array; (stagnant: bool, reason: str)。
    純関数=オフラインテスト可能。"""
    history = status.get("history", [])
    if len(history) < N_CONSECUTIVE:
        return False, f"only {len(history)} cycle(s) so far, need {N_CONSECUTIVE}"
    tail = history[-N_CONSECUTIVE:]
    vals = [h.get("metrics", {}).get("min_upright") for h in tail]
    if any(v is None for v in vals):
        return False, f"missing min_upright in recent history: {vals}"
    if all(v < UPRIGHT_THRESHOLD for v in vals):
        return True, f"last {N_CONSECUTIVE} cycles min_upright={vals} (all < {UPRIGHT_THRESHOLD})"
    return False, f"last {N_CONSECUTIVE} cycles min_upright={vals} (not all stagnant)"


def hours_since(updated_at):
    """updated_at(ISO文字列)からの経過時間。パースできなければ None。"""
    if not updated_at:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            t = time.mktime(time.strptime(str(updated_at)[:19], fmt))
            return (time.time() - t) / 3600.0
        except Exception:
            continue
    return None


def is_dead(status, supervisor_alive):
    """(dead: bool, reason: str)。純関数=オフラインテスト可能。

    supervisor_alive は「該当skillのsupervisor/trainerプロセスが居るか」。
    プロセスが生きているなら学習中とみなし、絶対にdead判定しない(誤検知防止)。
    """
    state = status.get("state", "?")
    if state not in ACTIVE_STATES:
        return False, f"state={state} は稼働想定外(監視対象外)"
    if supervisor_alive:
        return False, f"state={state} だがプロセス生存中"
    age = hours_since(status.get("updated_at"))
    if age is None:
        return False, "updated_at をパースできない"
    if age < DEAD_AFTER_HOURS:
        return False, f"state={state} 更新{age:.1f}h前 (閾値{DEAD_AFTER_HOURS}h未満)"
    return True, (f"state={state} のまま {age:.1f} 時間更新なし、"
                  f"かつ該当プロセス不在 (cycles={len(status.get('history', []))})")


def _notify_throttled(key):
    """同じ死亡状態で6時間毎に通知が飛び続けないよう、24時間に1回へ抑制する。
    (dead状態は復旧するまで続くため、無抑制だと通知が無視されるようになる)"""
    state_path = os.path.join(MECHA, "watchdog_notify_state.json")
    now = time.time()
    try:
        st = json.load(open(state_path, encoding="utf-8"))
    except Exception:
        st = {}
    if now - float(st.get(key, 0)) < NOTIFY_COOLDOWN_HOURS * 3600:
        return False
    st[key] = now
    try:
        json.dump(st, open(state_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception as e:
        _log(f"notify state write error: {type(e).__name__}: {e}")
    return True


def notify_dead(skill, reason, status):
    """死亡はログではなく通知する。停止(kill)は行わない。

    telegram_outbox.py は送信関数ではなくジョブ処理系(process_outbox)のため、
    実績のある data/workspace/notify_image.send_telegram_text を使う。
    失敗した場合は outbox に msg_*.json を置いて後段に拾わせる。
    """
    msg = (f"[MotionLab DEAD] skill={skill}\n{reason}\n"
           f"escalation_reason={status.get('escalation_reason', '-')}\n"
           f"status={SUP_STATUS}")
    print(msg)
    if not _notify_throttled(f"dead:{skill}"):
        _log("DEAD 通知は抑制(24時間以内に送信済み)")
        return False
    try:
        sys.path.insert(0, r"D:\Clawdbot_Docker_20260125\data\workspace")
        from notify_image import send_telegram_text
        if send_telegram_text(msg):
            _log("DEAD notified via notify_image.send_telegram_text")
            return True
    except Exception as e:
        _log(f"DEAD notify error: {type(e).__name__}: {e}")
    try:
        outbox = os.path.join(MECHA, "telegram_outbox")
        os.makedirs(outbox, exist_ok=True)
        path = os.path.join(outbox, f"msg_dead_{time.strftime('%Y%m%d_%H%M%S')}.json")
        json.dump({"caption": msg}, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        _log(f"DEAD queued to outbox: {path}")
        return True
    except Exception as e:
        _log(f"DEAD outbox error: {type(e).__name__}: {e}")
    return False


def supervisor_process_alive(skill, procs):
    """該当skillのsupervisor/trainerプロセスが居るか。
    procs が None(列挙不能)のときは安全側で True(=生きているとみなす)。"""
    if procs is None:
        return True
    for _pid, cl in procs:
        if not cl:
            continue
        if "motion_learning_supervisor" in cl and f"--skill {skill}" in cl:
            return True
        if "train_v50_walk" in cl:
            return True
    return False


def main():
    if not os.path.exists(SUP_STATUS):
        _log("no supervisor_status.json found; nothing to check")
        print("stagnant_watch: no status file, nothing to check")
        return 0

    try:
        status = json.load(open(SUP_STATUS, encoding="utf-8"))
    except Exception as e:
        _log(f"status parse error: {type(e).__name__}: {e}")
        print("stagnant_watch: status parse error")
        return 1

    skill = status.get("skill", "?")
    state = status.get("state", "?")
    stagnant, reason = is_stagnant(status)

    # 死亡検知は停滞検知より先に見る(停滞判定は history>=3 を要求するため、
    # 学習が一度も回っていない死亡状態を拾えない)。
    procs = list_python_processes()
    alive = supervisor_process_alive(skill, procs)
    dead, dead_reason = is_dead(status, alive)
    _log(f"check: skill={skill} state={state} stagnant={stagnant} reason={reason} "
         f"| alive={alive} dead={dead} dead_reason={dead_reason}")

    if dead:
        notify_dead(skill, dead_reason, status)
        print(f"stagnant_watch: DEAD (skill={skill}, {dead_reason})")
        return 0

    if not stagnant:
        print(f"stagnant_watch: OK (skill={skill}, {reason})")
        return 0

    if state not in ("running", "training", "checking"):
        _log(f"stagnant but state={state} (not active) -- nothing to kill")
        print(f"stagnant_watch: stagnant but process already inactive (state={state})")
        return 0

    if procs is None:
        _log("abort: cannot enumerate processes")
        print("stagnant_watch: enumerate failed, cannot act")
        return 1

    killed = []
    for pid, cl in procs:
        if not cl or "motion_learning_supervisor" not in cl:
            continue
        if any(p in cl for p in PROTECT_TOKENS):
            _log(f"  pid={pid} SKIP (protected token) cmd={cl[:200]}")
            continue
        if f"--skill {skill}" not in cl:
            _log(f"  pid={pid} SKIP (different skill) cmd={cl[:200]}")
            continue
        _log(f"  pid={pid} KILL (stagnant, skill={skill}) cmd={cl[:200]}")
        if kill_pid(pid):
            killed.append(pid)

    if killed:
        status["state"] = "stopped_by_watchdog"
        status["stopped_reason"] = f"stagnant_walk_watchdog: {reason}"
        status["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        json.dump(status, open(SUP_STATUS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        _log(f"DONE: killed {killed} (skill={skill}, {reason})")
        print(f"stagnant_watch: killed {killed} -- {reason}")
    else:
        _log(f"stagnant confirmed but no matching process found (skill={skill})")
        print(f"stagnant_watch: stagnant but no matching process found (skill={skill})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
