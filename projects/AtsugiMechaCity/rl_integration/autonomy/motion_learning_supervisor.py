# -*- coding: utf-8 -*-
"""Motion Learning Supervisor v1 — ローカルLLMレベルで回る自律PDCAループ。

役割: 学習ラン(train_v50_walk_tracking.py)を起動し、完了ごとに
  数値eval + レンダー転倒チェック → playbook.yaml の決定表で次アクションを決定
  → 再学習 / 成功通知 / 人間へエスカレーション。
判断はすべて決定表(playbook)の範囲内。表に無い状況・上限到達は必ず人間へ委ねる。
ローカルLLM(LiteLLM local_fast)は「助言ノート」の生成のみ(判断の主体ではない)。
到達不能なら黙ってスキップする — LLMなしでもループは完全に回る。

起動例(genesis venv):
  python motion_learning_supervisor.py --skill walk --max-cycles 6
状態出力(Portalカードが読む):
  data/workspace/apps/mecha_motion_lab/supervisor_status.json
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STAGE_A = os.path.join(HERE, "..", "stage_a")
TRAINER = os.path.join(STAGE_A, "train_v50_walk_tracking.py")
RENDERER = os.path.join(STAGE_A, "render_walk.py")
PY = sys.executable
WORK = r"C:\v50_work\autonomy"
PORTAL_STATUS = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\supervisor_status.json"
PORTAL_ESCALATIONS = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\escalations"
LITELLM = "http://localhost:4001/v1/chat/completions"


def load_playbook():
    """依存を増やさないための最小YAMLリーダー(この playbook の形だけ読めればよい)。"""
    try:
        import yaml  # 使えるなら正攻法
        with open(os.path.join(HERE, "playbook.yaml"), encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        pass
    pb = {"rules": [], "success_gate": {}, "limits": {}, "known_good_checkpoints": {}}
    section = None
    rule = None
    for raw in open(os.path.join(HERE, "playbook.yaml"), encoding="utf-8"):
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" "):
            section = line.rstrip(":")
            continue
        if section == "rules":
            m = re.match(r"\s+- name:\s*(\S+)", line)
            if m:
                rule = {"name": m.group(1)}
                pb["rules"].append(rule)
            m = re.match(r'\s+when:\s*"(.+)"', line)
            if m and rule is not None:
                rule["when"] = m.group(1)
            m = re.match(r"\s+action:\s*\{(.+)\}", line)
            if m and rule is not None:
                act = {}
                for kv in m.group(1).split(","):
                    k, v = kv.split(":", 1)
                    v = v.strip().strip('"')
                    try:
                        v = float(v) if "." in v or "-" in v[:1] else int(v)
                    except ValueError:
                        pass
                    act[k.strip()] = v
                rule["action"] = act
        elif section in ("success_gate", "limits", "known_good_checkpoints"):
            m = re.match(r"\s+(\S+):\s*(.+)", line)
            if m:
                k, v = m.group(1), m.group(2).strip()
                if v.lower() in ("true", "false"):
                    v = v.lower() == "true"
                else:
                    try:
                        v = float(v) if "." in v else int(v)
                    except ValueError:
                        pass
                pb[section][k] = v
    return pb


def write_status(state):
    os.makedirs(os.path.dirname(PORTAL_STATUS), exist_ok=True)
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(PORTAL_STATUS, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def telegram(text):
    try:
        env = {}
        for line in open(r"D:\Clawdbot_Docker_20260125\.env", encoding="utf-8", errors="ignore"):
            if line.startswith("TELEGRAM_"):
                k, _, v = line.partition("=")
                # .envの値は引用符付き — 剥がさないとURLに"が混入し404で通知が消える
                # (2026-07-12 telegram_demoで実証・修正)
                env[k.strip()] = v.strip().strip('"').strip("'")
        body = json.dumps({"chat_id": env["TELEGRAM_CHAT_ID"], "text": text[:3800]}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}/sendMessage",
            data=body, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print("telegram skip:", e)


def llm_note(metrics, rule_name):
    """任意: ローカルLLMに1行の状況ノートを書かせる。失敗しても無害。"""
    try:
        body = json.dumps({
            "model": "local_fast", "max_tokens": 120,
            "messages": [{"role": "user", "content":
                "You supervise robot walk training. Metrics: "
                f"{json.dumps(metrics)}. Applied playbook rule: {rule_name}. "
                "In one short Japanese sentence, note the situation for the log."}],
        }).encode()
        req = urllib.request.Request(LITELLM, data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip()[:200]
    except Exception:
        return None


# 2026-07-22 GPU使用率対策(.bak_nenvs_20260722): 実測でGPU util16%/VRAM 1000MiB of 16GB/
# 電力34W of 180W=大幅に遊休。n_envs=512はRTX5060Ti(16GB)に対し小さすぎた。並列環境数を
# 増やすとGPU使用率とスループットが上がり、1iterのサンプル数増→学習が速く安定。VRAMは
# 512envで約1000MiB(≒base700+約0.6MiB/env)なので4096でも約3-4GBで安全。環境変数 MECHA_N_ENVS
# で調整可(2048/4096/8192)。T067(GPU lost)配慮で既定は中庸の4096。
N_ENVS = os.environ.get("MECHA_N_ENVS", "4096")


def run_training(cycle_dir, cfg, resume_path):
    args = [PY, TRAINER, "--iterations", str(cfg.get("iterations", 800)),
            "--n-envs", N_ENVS, "--out", cycle_dir,
            "--entropy", str(cfg.get("entropy", 0.001)),
            "--init-log-std", str(cfg.get("init_log_std", -1.2))]
    if cfg.get("ref_json"):
        args += ["--ref-json", cfg["ref_json"]]
    if cfg.get("terrain") and cfg["terrain"] != "none":
        args += ["--terrain", cfg["terrain"]]
    if resume_path:
        args += ["--resume", resume_path]
    print("TRAIN:", " ".join(args), flush=True)
    r = subprocess.run(args, cwd=STAGE_A, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    # T066対応 2026-07-19: 失敗原因の材料を必ず残す(rc=1だけでは診断不能だった)
    try:
        with open(os.path.join(cycle_dir, "train_stdout.log"), "w", encoding="utf-8") as f:
            f.write(r.stdout or "")
        with open(os.path.join(cycle_dir, "train_stderr.log"), "w", encoding="utf-8") as f:
            f.write(r.stderr or "")
    except Exception:
        pass
    return r.returncode


def run_render_check(cycle_dir, ref_json=None, terrain=None):
    """render_walk.py をこのサイクルのチェックポイントで実行し walk_check.json を得る。"""
    env = dict(os.environ, WALK_CKPT=os.path.join(cycle_dir, "latest.pt"),
               WALK_OUT=os.path.join(cycle_dir, "frames"), PYTHONIOENCODING="utf-8")
    if ref_json:
        env["WALK_REF_JSON"] = ref_json
    if terrain and terrain != "none":
        env["WALK_TERRAIN"] = terrain
    r = subprocess.run([PY, RENDERER], cwd=STAGE_A, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    check_path = os.path.join(cycle_dir, "frames", "walk_check.json")
    if os.path.exists(check_path):
        return json.load(open(check_path, encoding="utf-8"))
    print("render check missing; stderr tail:", (r.stderr or "")[-300:])
    return None


def gather_metrics(cycle_dir, check):
    ev = json.load(open(os.path.join(cycle_dir, "eval.json"), encoding="utf-8"))
    m = {"vx": ev.get("deterministic_vx_mean", 0.0),
         "eval_travel": ev.get("deterministic_travel_m_8s", 0.0)}
    if check:
        m["travel"] = check.get("final_travel", 0.0)
        m["fell"] = bool(check.get("fell", True))
        m["min_upright"] = check.get("min_upright", 0.0)
        # 2026-07-20: 転倒時刻(秒)。無転倒はNone→9999扱い。旧walk_checkに
        # フィールドが無い場合は0.0(=即転倒側の保守的解釈)
        ffs = check.get("first_fall_sec", 0.0)
        m["first_fall_sec"] = 9999.0 if ffs is None else float(ffs)
    else:  # レンダー不能時は保守的に扱う(成功判定はしない)
        m["travel"] = m["eval_travel"]
        m["fell"] = True
        m["min_upright"] = 0.0
    return m


def pick_rule(pb, m):
    scope = {"travel": m["travel"], "vx": m["vx"], "fell": m["fell"], "true": True,
             "first_fall_sec": m.get("first_fall_sec", 0.0)}
    for rule in pb["rules"]:
        try:
            if eval(rule["when"], {"__builtins__": {}}, scope):  # playbookは信頼済み設定ファイル
                return rule
        except Exception:
            continue
    return {"name": "no_rule", "action": {"type": "escalate", "reason": "no playbook rule matched"}}


def escalate(state, reason, cycle_dir):
    msg = (f"[MotionLab ESCALATION] skill={state['skill']} cycle={state['cycle']}: {reason}\n"
           f"metrics={json.dumps(state.get('last_metrics'), ensure_ascii=False)}\n"
           f"artifacts={cycle_dir}\n人間の判断が必要です。")
    with open(os.path.join(cycle_dir, "escalation.md"), "w", encoding="utf-8") as f:
        f.write(msg)
    try:  # リポジトリ側にも複製(C:\v50_work消失・上書き対策 — 2026-07-11 run_auto理由不明の再発防止)
        os.makedirs(PORTAL_ESCALATIONS, exist_ok=True)
        fname = f"{state['skill']}_cycle{state['cycle']:02d}_{time.strftime('%Y%m%d_%H%M%S')}.md"
        with open(os.path.join(PORTAL_ESCALATIONS, fname), "w", encoding="utf-8") as f:
            f.write(msg)
    except Exception as e:
        print("escalation copy skip:", e)
    telegram(msg)
    state["state"] = "escalated"
    state["escalation_reason"] = reason
    write_status(state)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", default="walk")
    ap.add_argument("--ref-json", default=None, help="retargeted reference motion (Stage B)")
    ap.add_argument("--iterations", type=int, default=1500, help="initial cycle iterations")
    ap.add_argument("--terrain", default="none", help="U6: stairs|slope_up|slope_down")
    ap.add_argument("--entropy", type=float, default=0.001)
    ap.add_argument("--init-log-std", type=float, default=-1.2)
    ap.add_argument("--max-cycles", type=int, default=None)
    args = ap.parse_args()

    try:  # 学習ループ生存中はPCスリープを抑止(スリープで学習が停止した実績への対策)
        from keep_awake import hold_awake
        hold_awake()
    except Exception:
        pass
    pb = load_playbook()
    max_cycles = args.max_cycles or pb["limits"].get("max_cycles_per_skill", 6)
    state = {"schema": "clawstack.motion_learning_supervisor.v1", "skill": args.skill,
             "state": "running", "cycle": 0, "history": [], "playbook_version": "v1"}
    resume = pb["known_good_checkpoints"].get("best_walker")
    cfg = {"iterations": args.iterations, "entropy": args.entropy,
           "init_log_std": args.init_log_std, "ref_json": args.ref_json,
           "terrain": args.terrain}
    best_travel, no_improve = -1e9, 0

    for cycle in range(1, max_cycles + 1):
        state["cycle"] = cycle
        cycle_dir = os.path.join(WORK, f"{args.skill}_cycle{cycle:02d}")
        os.makedirs(cycle_dir, exist_ok=True)
        state["state"] = "training"
        state["current_dir"] = cycle_dir
        write_status(state)

        rc = run_training(cycle_dir, cfg, resume)
        if rc != 0 or not os.path.exists(os.path.join(cycle_dir, "eval.json")):
            err_tail = ""
            try:
                with open(os.path.join(cycle_dir, "train_stderr.log"), encoding="utf-8") as f:
                    err_tail = f.read()[-500:]
            except Exception:
                pass
            escalate(state, f"training process failed rc={rc}\nstderr_tail: {err_tail}", cycle_dir)
            return 2

        state["state"] = "checking"
        write_status(state)
        check = run_render_check(cycle_dir, args.ref_json, args.terrain)
        m = gather_metrics(cycle_dir, check)
        state["last_metrics"] = m

        rule = pick_rule(pb, m)
        note = llm_note(m, rule["name"])
        entry = {"cycle": cycle, "metrics": m, "rule": rule["name"], "llm_note": note}
        state["history"].append(entry)
        print("CYCLE", cycle, json.dumps(entry, ensure_ascii=False), flush=True)

        act = rule["action"]
        if act["type"] == "success":
            state["state"] = "learned"
            write_status(state)
            telegram(f"[MotionLab] skill '{args.skill}' 習得判定: travel={m['travel']:.2f}m/8s "
                     f"転倒なし。成果物: {cycle_dir}")
            return 0
        if act["type"] == "escalate":
            escalate(state, act.get("reason", rule["name"]), cycle_dir)
            return 2

        # 改善停滞の監視 — v2: 相対15%(v1の固定+0.05mはcycle3の23%改善を
        # 「停滞」と誤判定した)。ベストが小さい/負のうちは絶対+0.05mで判定。
        threshold = best_travel * 1.15 if best_travel > 0.3 else best_travel + 0.05
        if m["travel"] <= threshold:
            no_improve += 1
        else:
            no_improve = 0
        if m["travel"] > best_travel:
            best_travel = m["travel"]
        if no_improve >= pb["limits"].get("max_consecutive_no_improve", 2):
            escalate(state, f"no improvement for {no_improve} cycles (best={best_travel:.2f}m)", cycle_dir)
            return 2

        # retrain: playbook のパラメータで次サイクルへ
        cfg = {"iterations": int(act.get("iterations", 800)),
               "entropy": float(act.get("entropy", 0.001)),
               "init_log_std": float(act.get("init_log_std", -1.2)),
               "ref_json": args.ref_json, "terrain": args.terrain}
        resume = (pb["known_good_checkpoints"].get("best_walker")
                  if act.get("resume") == "best_walker"
                  else os.path.join(cycle_dir, "latest.pt"))

    escalate(state, f"max cycles ({max_cycles}) reached", cycle_dir)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
