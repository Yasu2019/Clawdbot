# -*- coding: utf-8 -*-
"""踏破率で評価する。生存率は評価窓とコース長に依存して意味が変わるため。

  踏破率 = 到達prog / コース全長(地形が終わる位置)
  完走率 = コース終端に到達したenvの割合
"""
import sys, argparse, torch
sys.path.insert(0, r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\stage_a")
from v50_walk_env import V50WalkEnv, V50
import train_v50_walk_tracking as T

def course_len(terr):
    if terr in T.CORRIDOR_VARIANTS:
        return T._corridor_layout(None, terr)[-1]["prog1"]
    if terr in ("stairs", "stairs_down"):
        return T.TERRAIN_FLAT_RUNUP + T.TERRAIN_STAIR_D * T.TERRAIN_STAIR_N
    if terr in ("slope_up", "slope_down"):
        import math
        return T.TERRAIN_FLAT_RUNUP + 2 * T.TERRAIN_SLOPE_HALF * math.cos(math.radians(T.TERRAIN_SLOPE_DEG))
    return 5.0

ap = argparse.ArgumentParser()
ap.add_argument("--ckpt", required=True); ap.add_argument("--terrain", required=True)
ap.add_argument("--label", default=""); ap.add_argument("--n-envs", type=int, default=256)
ap.add_argument("--cmd-vx", type=float, default=0.27)
a = ap.parse_args()

L = course_len(a.terrain)
secs = max(20.0, L / a.cmd_vx * 1.6)          # コース長に応じた窓(踏破に必要な時間の1.6倍)
REF = (r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration"
       r"\stage_b\refs\v50_ref_stairs_up_cmu143_17_armneutral.json")
cfg = {"terrain": a.terrain, "episode_length_s": secs, "height_scan": {},
       "cmd_vx": [a.cmd_vx, a.cmd_vx], "cmd_zero_prob": 0.0, "push_vel": 0.35}
if a.terrain in T.CORRIDOR_VARIANTS: cfg["corridor_fixed_start"] = True
env = V50WalkEnv(a.n_envs, r"D:\Temp\claude\course", cfg=cfg, ref_json=REF)
from rsl_rl.runners import OnPolicyRunner
tc = {"algorithm":{"class_name":"PPO","clip_param":0.2,"desired_kl":0.01,"entropy_coef":0.005,
 "gamma":0.99,"lam":0.95,"learning_rate":1e-3,"max_grad_norm":1.0,"num_learning_epochs":5,
 "num_mini_batches":4,"schedule":"adaptive","use_clipped_value_loss":True,"value_loss_coef":1.0},
 "policy":{"class_name":"ActorCritic","activation":"elu","actor_hidden_dims":[512,256,128],
 "critic_hidden_dims":[512,256,128],"init_noise_std":1.0},
 "runner":{"checkpoint":-1,"experiment_name":"d","load_run":-1,"max_iterations":1,
 "num_steps_per_env":24,"record_interval":-1,"resume":False,"resume_path":None,"run_name":""},
 "runner_class_name":"OnPolicyRunner","num_steps_per_env":24,"save_interval":100,
 "empirical_normalization":True,"seed":1}
r = OnPolicyRunner(env, tc, r"D:\Temp\claude\course", device=env.device); r.load(a.ckpt)
pol = r.get_inference_policy(device=env.device)
N, dev = a.n_envs, env.device
obs, _ = env.reset(); done = torch.zeros(N, dtype=torch.bool, device=dev)
mx = torch.zeros(N, device=dev)
for _ in range(int(secs / env.dt)):
    with torch.no_grad(): act = pol(obs)
    obs, _, rst, _ = env.step(act)
    mx = torch.where(~done, torch.maximum(mx, -env.pos[:, V50.FWD_AXIS]), mx)
    done |= (rst.bool() if rst.dtype != torch.bool else rst)
    if bool(done.all()): break
f = (mx / L).clamp(max=1.0)
print(f"{a.label or a.terrain:22s} コース{L:6.2f}m 窓{secs:5.1f}s | "
      f"踏破率 平均{float(f.mean())*100:5.1f}% 中央{float(f.median())*100:5.1f}% | "
      f"完走 {float((mx>=L-0.05).float().mean())*100:5.1f}%")
