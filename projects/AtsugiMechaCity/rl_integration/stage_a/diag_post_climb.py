# -*- coding: utf-8 -*-
"""終了位置の分布と終了理由を env 毎に実測する。

踏破率(eval_course_completion_WIP.py)は平均しか出さないため、
「平均5.17m」から「階段(5.0mで終わる)を登り切った直後に落ちている」と
推定するところで止まっていた。平均は分布の形を隠す — 5.0m 手前と
6.5m 付近の二峰でも同じ平均になる。ここでは分布そのものを出す。

env 毎に記録する:
    終了時の prog / 終了理由(tilt/low/collision/timeout) /
    そのときの upright・前進速度・接地足数

出力はセグメント境界で区切ったヒストグラムと JSON。
既存ファイルは一切変更しない(診断専用の新規ファイル)。
"""
import sys, argparse, json, math
from pathlib import Path

import torch

sys.path.insert(0, r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\stage_a")
from v50_walk_env import V50WalkEnv, V50
import train_v50_walk_tracking as T


def segments(terrain):
    """[(kind, prog0, prog1)] を返す。corridor 系は _corridor_layout を唯一の真とし、
    単体地形はコース長の定義(eval_course_completion_WIP.py と同一)に合わせる。"""
    if terrain in T.CORRIDOR_VARIANTS:
        return [(s["kind"], s["prog0"], s["prog1"]) for s in T._corridor_layout(None, terrain)]
    runup = T.TERRAIN_FLAT_RUNUP
    if terrain in ("stairs", "stairs_down"):
        end = runup + T.TERRAIN_STAIR_D * T.TERRAIN_STAIR_N
        return [("flat", 0.0, runup),
                ("stairs_up" if terrain == "stairs" else "stairs_down", runup, end)]
    if terrain in ("slope_up", "slope_down"):
        end = runup + 2 * T.TERRAIN_SLOPE_HALF * math.cos(math.radians(T.TERRAIN_SLOPE_DEG))
        return [("flat", 0.0, runup), (terrain, runup, end)]
    return [("flat", 0.0, 5.0)]


ap = argparse.ArgumentParser()
ap.add_argument("--ckpt", required=True)
ap.add_argument("--terrain", required=True)
ap.add_argument("--label", default="")
ap.add_argument("--n-envs", type=int, default=2048)
ap.add_argument("--cmd-vx", type=float, default=0.27)
# 参照モーションは**学習時と同じ設定**で渡す(T079aa: 参照なしで学習した方策に
# 階段用の参照を与えると観測が変わり、検証済みの実測と矛盾する値が出る)。
ap.add_argument("--ref-json", default=None)
ap.add_argument("--out", default=None, help="JSON 出力先。既定は出力しない")
# 既定の窓はコース長に比例する(eval_course_completion_WIP.py と同じ規約)。
# コース長が違う2条件を比べると窓も一緒に変わるため、窓自体の影響を切り離せない。
# 明示指定で窓を固定し、幾何の差と窓の差を分離するための対照用フラグ。
ap.add_argument("--window-s", type=float, default=None,
                help="評価窓を秒で固定する。既定はコース長から自動計算")
# DR(質量・PDゲイン)は既定 8 グループで、2048env でも**独立抽選は8回だけ**、
# 256env が同一の質量/KPを共有する(v50_walk_env.py の _apply_dr)。質量とKPは
# 階段登坂の成否を決める支配要因なので、8回の抽選が結果全体を動かし、
# env 数を増やしても実効サンプル数は 8 のまま。同一設定の再実行で完走率が
# 19.0% <-> 42.2% と振れる原因はこれ。評価では独立抽選数を増やす。
ap.add_argument("--dr-groups", type=int, default=None,
                help="DRの独立抽選グループ数。0 で n-envs と同数(env毎に独立)")
# 再現しない原因の切り分け用。DR を env 毎(2048抽選)にしても振れ幅が縮まらなかったため、
# 確率的な入力を1つずつ落として、どれが run 単位のばらつきを生んでいるかを実測する。
ap.add_argument("--no-dr", action="store_true", help="DRを無効化(質量・KPを公称値に固定)")
ap.add_argument("--no-push", action="store_true", help="外乱pushを無効化")
a = ap.parse_args()

segs = segments(a.terrain)
L = segs[-1][2]
secs = a.window_s if a.window_s is not None else max(20.0, L / a.cmd_vx * 1.6)

cfg = {"terrain": a.terrain, "episode_length_s": secs,
       **({"height_scan": {}} if a.terrain != "none" else {}),
       "cmd_vx": [a.cmd_vx, a.cmd_vx], "cmd_zero_prob": 0.0, "push_vel": 0.35}
if a.terrain in T.CORRIDOR_VARIANTS:
    cfg["corridor_fixed_start"] = True
if a.dr_groups is not None:
    cfg["dr_groups"] = a.n_envs if a.dr_groups == 0 else a.dr_groups
if a.no_dr:
    cfg["dr_mass_scale"] = [1.0, 1.0]
    cfg["dr_kp_scale"] = [1.0, 1.0]
if a.no_push:
    cfg["push_vel"] = 0.0
env = V50WalkEnv(a.n_envs, r"D:\Temp\claude\diag_post_climb", cfg=cfg, ref_json=a.ref_json)

from rsl_rl.runners import OnPolicyRunner
tc = {"algorithm": {"class_name": "PPO", "clip_param": 0.2, "desired_kl": 0.01,
      "entropy_coef": 0.005, "gamma": 0.99, "lam": 0.95, "learning_rate": 1e-3,
      "max_grad_norm": 1.0, "num_learning_epochs": 5, "num_mini_batches": 4,
      "schedule": "adaptive", "use_clipped_value_loss": True, "value_loss_coef": 1.0},
      "policy": {"class_name": "ActorCritic", "activation": "elu",
                 "actor_hidden_dims": [512, 256, 128], "critic_hidden_dims": [512, 256, 128],
                 "init_noise_std": 1.0},
      "runner": {"checkpoint": -1, "experiment_name": "d", "load_run": -1,
                 "max_iterations": 1, "num_steps_per_env": 24, "record_interval": -1,
                 "resume": False, "resume_path": None, "run_name": ""},
      "runner_class_name": "OnPolicyRunner", "num_steps_per_env": 24, "save_interval": 100,
      "empirical_normalization": True, "seed": 1}
r = OnPolicyRunner(env, tc, r"D:\Temp\claude\diag_post_climb", device=env.device)
r.load(a.ckpt)
pol = r.get_inference_policy(device=env.device)

N, dev = a.n_envs, env.device
obs, _ = env.reset()
done = torch.zeros(N, dtype=torch.bool, device=dev)
# 最初の終了だけを記録する。
#
# step が返った時点でどの値がリセット前かは項目ごとに違う(実測で確認した):
#   env.pos / env.upright / env.term_*  … _check_termination で確定 -> 終了時の値。有効
#   env.lin_vel / env.contacts          … step 末尾の reset_idx が lin_vel をゼロ化し
#                                          (`self.lin_vel[idx] = 0.0`)、続く _compute_obs()
#                                          が接地を取り直すため **post-reset**。
# 素直に読むと vx が全 env で厳密に 0.000、接地が 100% 両足(=リセット直後の起立姿勢)に
# なる。速度と接地は 1 ステップ前のスナップショットを使う。
snap_vx = torch.zeros(N, device=dev)
snap_feet = torch.zeros(N, device=dev)
end_prog = torch.zeros(N, device=dev)
max_prog = torch.zeros(N, device=dev)
end_upright = torch.zeros(N, device=dev)
end_vx = torch.zeros(N, device=dev)
end_feet = torch.zeros(N, device=dev)
reason = torch.zeros(N, dtype=torch.long, device=dev)   # 0=timeout 1=tilt 2=low 3=collision

for _ in range(int(secs / env.dt)):
    # ループ先頭 = 直前 step 終了時の状態。ここで取れば、この step で終了する env に
    # とっては「終了1ステップ前」、最後まで生き残る env にとっては「最終 step の
    # 時間切れリセットを受ける前」の値になり、両方を同じ経路で扱える。
    snap_vx = V50.FWD_SIGN * env.lin_vel[:, V50.FWD_AXIS]
    snap_feet = env.contacts.float().sum(dim=1)
    with torch.no_grad():
        act = pol(obs)
    obs, _, rst, _ = env.step(act)
    prog = -env.pos[:, V50.FWD_AXIS]
    max_prog = torch.where(~done, torch.maximum(max_prog, prog), max_prog)
    rst = rst.bool() if rst.dtype != torch.bool else rst
    new = rst & (~done)
    if bool(new.any()):
        vx, feet = snap_vx, snap_feet     # 終了1ステップ前(post-reset汚染を避ける)
        # 優先度: collision > low > tilt。同時成立時にどれを主因と呼ぶかを固定する。
        rsn = torch.zeros(N, dtype=torch.long, device=dev)
        rsn = torch.where(env.term_tilt, torch.full_like(rsn, 1), rsn)
        rsn = torch.where(env.term_low, torch.full_like(rsn, 2), rsn)
        rsn = torch.where(env.term_collision, torch.full_like(rsn, 3), rsn)
        end_prog = torch.where(new, prog, end_prog)
        end_upright = torch.where(new, env.upright, end_upright)
        end_vx = torch.where(new, vx, end_vx)
        end_feet = torch.where(new, feet, end_feet)
        reason = torch.where(new, rsn, reason)
        done |= new
    if bool(done.all()):
        break

# 最後まで終了しなかった env は時間切れ(=完走扱い)。
alive = ~done
if bool(alive.any()):
    end_prog = torch.where(alive, max_prog, end_prog)
    end_upright = torch.where(alive, env.upright, end_upright)
    end_vx = torch.where(alive, snap_vx, end_vx)
    end_feet = torch.where(alive, snap_feet, end_feet)

ep = end_prog.clamp(min=0.0).cpu()
mp = max_prog.clamp(min=0.0).cpu()
rs = reason.cpu()
up, vxc, ftc = end_upright.cpu(), end_vx.cpu(), end_feet.cpu()
RNAME = {0: "timeout", 1: "tilt", 2: "low", 3: "collision"}

label = a.label or f"{a.terrain}"
print(f"\n===== {label} =====")
print(f"ckpt   : {a.ckpt}")
print(f"コース : {L:.2f} m ({len(segs)} セグメント) 窓 {secs:.1f}s  n_envs={N}")
print(f"踏破率 : 平均 {float((mp / L).clamp(max=1.0).mean()) * 100:.1f}% "
      f"中央 {float((mp / L).clamp(max=1.0).median()) * 100:.1f}% "
      f"完走 {float((mp >= L - 0.05).float().mean()) * 100:.1f}%")

def stats(m):
    """終了時の姿勢・速度・接地の分布。平均だけだと『全部0.000』が実態なのか
    丸めなのか判別できないため、中央値と標準偏差、接地足数の内訳まで出す。"""
    n = int(m.sum())
    if not n:
        return "-"
    v = vxc[m]
    f = ftc[m]
    f0 = float((f == 0).float().mean()) * 100
    f1 = float((f == 1).float().mean()) * 100
    f2 = float((f == 2).float().mean()) * 100
    return (f"up {float(up[m].mean()):.3f}±{float(up[m].std()) if n > 1 else 0.0:.3f} | "
            f"vx 平均{float(v.mean()):+.3f} 中央{float(v.median()):+.3f} "
            f"sd{float(v.std()) if n > 1 else 0.0:.3f} |vx|>0.05:{float((v.abs() > 0.05).float().mean()) * 100:4.0f}% | "
            f"接地 0足{f0:3.0f}% 1足{f1:3.0f}% 2足{f2:3.0f}%")


print("\n-- セグメント別 終了位置分布 --")
rows = []
for kind, p0, p1 in segs:
    m = (ep >= p0) & (ep < p1)
    n = int(m.sum())
    frac = n / N * 100
    print(f"{kind:12s} {p0:5.2f}-{p1:5.2f}m {frac:6.1f}% {n:7d} | {stats(m)}")
    rows.append({"kind": kind, "prog0": p0, "prog1": p1, "count": n, "frac_pct": frac})
# コース終端より先で終了した env。地形ジオメトリはコース終端で切れるため、
# ここでの転倒は「段差から落ちた」だけの地形外アーティファクトであり、
# 課題の失敗として数えてはいけない。
m_end = ep >= L - 1e-6
n_end = int(m_end.sum())
print(f"{'地形外(終端以降)':12s} {L:5.2f}m~     {n_end / N * 100:6.1f}% {n_end:7d} | {stats(m_end)}")
rows.append({"kind": "past_course_end", "prog0": L, "prog1": None,
             "count": n_end, "frac_pct": n_end / N * 100})

print("\n-- 終了理由 --")
reasons = {}
for k, name in RNAME.items():
    m = rs == k
    n = int(m.sum())
    reasons[name] = {"count": n, "frac_pct": n / N * 100,
                     "mean_end_prog": float(ep[m].mean()) if n else None}
    if n:
        print(f"{name:10s} {n / N * 100:6.1f}% {n:7d}  終了prog 平均 {float(ep[m].mean()):5.2f}m "
              f"中央 {float(ep[m].median()):5.2f}m")
    else:
        print(f"{name:10s} {0.0:6.1f}% {0:7d}")

# 階段区間を登り切った後だけを取り出す(仮説の核心)。
up_seg = next((s for s in segs if s[0] == "stairs_up"), None)
if up_seg is not None:
    top = up_seg[2]
    reached = mp >= top
    print(f"\n-- 階段終端 {top:.2f}m を越えた env のみ ({int(reached.sum())}/{N} "
          f"= {float(reached.float().mean()) * 100:.1f}%) --")
    if int(reached.sum()):
        after = ep[reached]
        print(f"そのうち終端到達 {float((after >= L - 0.05).float().mean()) * 100:5.1f}%  "
              f"途中終了 {float((after < L - 0.05).float().mean()) * 100:5.1f}%")
        print(f"終了prog 平均 {float(after.mean()):.2f}m 中央 {float(after.median()):.2f}m")
        for k, name in RNAME.items():
            m = reached & (rs == k)
            n = int(m.sum())
            if n:
                print(f"  {name:10s} {n / int(reached.sum()) * 100:5.1f}%  "
                      f"終了prog 平均 {float(ep[m].mean()):5.2f}m")

if a.out:
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": label, "ckpt": a.ckpt, "terrain": a.terrain, "n_envs": N,
        "course_len_m": L, "window_s": secs, "cmd_vx": a.cmd_vx,
        "ref_json": a.ref_json,
        "completion_mean_pct": float((mp / L).clamp(max=1.0).mean()) * 100,
        "completion_median_pct": float((mp / L).clamp(max=1.0).median()) * 100,
        "full_course_pct": float((mp >= L - 0.05).float().mean()) * 100,
        "segments": rows, "reasons": reasons,
        "end_prog": [round(float(v), 4) for v in ep.tolist()],
        "end_reason": [RNAME[int(v)] for v in rs.tolist()],
    }
    Path(a.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON: {a.out}")
