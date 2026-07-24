# -*- coding: utf-8 -*-
"""Stage A v2: V50 walk training on rsl_rl PPO + contact-aware rewards.

This is a SIBLING of train_v50_walk_tracking.py, not a replacement. The old
trainer keeps running and keeps its own artifacts; this one writes the SAME
status.json / eval.json schema so motion_learning_supervisor.py and the
mecha_motion_lab dashboard can consume either without a change.

What rsl_rl buys us over the self-contained PPO (see v50_walk_env.py header for
the full root-cause list):
  * correct time-limit bootstrapping via extras["time_outs"]   (root cause C2)
  * EmpiricalNormalization of observations                     (root cause C3)
  * KL-adaptive learning rate instead of a fixed 3e-4
  * minibatched multi-epoch PPO with value clipping

Install note: rsl-rl-lib was installed with --no-deps on purpose. A plain
`pip install rsl-rl-lib` pulls torch 2.13.0 (CPU) and would destroy the
torch 2.11.0+cu128 CUDA build this venv depends on.

Run (venv: C:\\v50_work\\genesis_venv):
  python train_v50_walk_rsl.py --iterations 3000 --n-envs 4096 \
      --out C:\\v50_work\\autonomy\\walk_rsl_cycle01 \
      --ref-json C:\\v50_work\\refs\\walk.json
"""
import argparse, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch

import train_v50_walk_tracking as V50
from v50_walk_env import V50WalkEnv, _default_cfg


def _default_cmd_vx():
    return _default_cfg()["cmd_vx"]


def load_with_surgery(runner, ckpt_path, num_scan):
    """Load a smaller-obs (blind) checkpoint into this larger height-scan network.

    The scan columns were appended at the END of the observation, so the source
    input weights map onto the first (num_obs - num_scan) columns of the new
    first layer unchanged; the new scan columns are left at their (small random)
    init and the policy starts behaving identically to the blind source. The
    observation normalizer's running mean/var are copied for the shared prefix
    and left at 0/1 for the new scan dims. Everything except the first actor and
    critic layers and the two normalizers is shape-identical and copied verbatim.
    """
    import torch as _t
    sd = _t.load(ckpt_path, map_location="cpu", weights_only=False)
    model = runner.alg.policy.state_dict()
    src = sd["model_state_dict"]
    copied, surgical = 0, []
    for k, v in model.items():
        if k not in src:
            continue
        sv = src[k]
        if sv.shape == v.shape:
            model[k] = sv.clone()
            copied += 1
        elif v.dim() == 2 and sv.dim() == 2 and v.shape[0] == sv.shape[0] \
                and v.shape[1] == sv.shape[1] + num_scan:
            w = v.clone()
            w[:, :sv.shape[1]] = sv                     # copy blind input columns
            w[:, sv.shape[1]:] = 0.0                    # zero the new scan columns
            model[k] = w                                # -> starts identical to blind
            surgical.append(k)
        else:
            print(f"[surgery] skip {k}: {tuple(sv.shape)} -> {tuple(v.shape)}", flush=True)
    runner.alg.policy.load_state_dict(model)

    def graft_norm(dst_norm, src_state):
        if dst_norm is None or src_state is None:
            return
        dsd = dst_norm.state_dict()
        for key in ("_mean", "_var", "_std"):
            if key in dsd and key in src_state:
                n = src_state[key].numel()
                dsd[key].view(-1)[:n] = src_state[key].view(-1)
        if "count" in dsd and "count" in src_state:
            dsd["count"].copy_(src_state["count"])
        dst_norm.load_state_dict(dsd)

    if getattr(runner, "empirical_normalization", False):
        graft_norm(runner.obs_normalizer, sd.get("obs_norm_state_dict"))
        graft_norm(getattr(runner, "privileged_obs_normalizer", None),
                   sd.get("privileged_obs_norm_state_dict"))
    print(f"[surgery] {ckpt_path}: copied {copied} tensors verbatim, "
          f"grafted {len(surgical)} input layers (+{num_scan} scan cols zero-carried): "
          f"{surgical}", flush=True)


def train_cfg(args):
    return {
        "algorithm": {
            "class_name": "PPO",
            "clip_param": 0.2,
            "desired_kl": 0.01,
            "entropy_coef": args.entropy,
            "gamma": 0.99,
            "lam": 0.95,
            "learning_rate": 1.0e-3,
            "max_grad_norm": 1.0,
            "num_learning_epochs": 5,
            "num_mini_batches": 4,
            "schedule": "adaptive",          # KL-adaptive LR
            "use_clipped_value_loss": True,
            "value_loss_coef": 1.0,
            "normalize_advantage_per_mini_batch": False,
        },
        "policy": {
            "class_name": "ActorCritic",
            "activation": "elu",
            "actor_hidden_dims": [512, 256, 128],
            "critic_hidden_dims": [512, 256, 128],
            "init_noise_std": args.init_noise_std,
        },
        "num_steps_per_env": args.rollout,
        "save_interval": 50,
        "empirical_normalization": True,     # root cause C3
        "obs_groups": {"policy": ["policy"], "critic": ["policy"]},
        "logger": "tensorboard",
        "experiment_name": "v50_walk_rsl",
        "run_name": "",
        "resume": False,
        "load_run": -1,
        "checkpoint": -1,
    }


class StatusWriter:
    """Mirror the clawstack.stage_a_walk_tracking.v1 status contract."""

    def __init__(self, env, out, total):
        self.env, self.out, self.total = env, out, total
        self.t0 = time.time()
        self.best = -1e9

    def write(self, it):
        env = self.env
        s = env.stats()
        # Keep `mean_reward_per_step` comparable to the v1 trainer, which
        # reported per-step reward rather than episode return.
        rew_step = s["return"] / max(s["ep_len_s"] / env.dt, 1.0)
        self.best = max(self.best, rew_step)
        pose_err = ((env.dof_pos - env.ref) ** 2).mean().item()
        payload = {
            "schema": "clawstack.stage_a_walk_tracking.v1",
            "trainer": "rsl_rl",
            "iteration": it, "iterations_total": self.total,
            "mean_reward_per_step": round(rew_step, 4),
            "best_reward_per_step": round(self.best, 4),
            "mean_episode_return": round(s["return"], 3),
            "mean_episode_len_s": round(s["ep_len_s"], 2),
            "fall_rate": round(s["fall_rate"], 3),
            "fall_by_tilt": round(s["fall_by_tilt"], 3),
            "fall_by_low": round(s["fall_by_low"], 3),
            "fall_by_collision": round(s["fall_by_collision"], 3),
            "vx_mean": round(s["vx"], 3),
            "upright": round(s["upright"], 3),
            "pose_err": round(pose_err, 5),
            "single_contact_frac": round(s["single_contact"], 3),
            "mean_air_time": round(s["air_time"], 3),
            "elapsed_sec": round(time.time() - self.t0, 1),
            "n_envs": env.num_envs,
        }
        with open(os.path.join(self.out, "status.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return payload


def evaluate(env, policy, normalizer, seconds=8.0, cmd_vx=None):
    """Deterministic + stochastic evaluation, reported as UPRIGHT travel.

    Why this differs from the v1 eval, which reported bare displacement:
    `check_reference_gait.py` showed that this body, driven open loop by the
    reference gait with ZERO policy action, topples forward and slides
    1.56 m (analytic sin gait) / 1.61 m (retargeted 100STYLE). The v1 "best
    walker" figures -- 1.63 m, 1.71 m, 1.85 m -- sit right on top of that
    number, so bare displacement cannot distinguish walking from falling over
    and has been rewarding the latter.

    `clean_travel_m` therefore counts distance ONLY from envs that stayed
    upright for the whole window, and `survival_rate` reports how many did.
    A policy that dives scores clean_travel 0.0 no matter how far it slides.
    """
    cmd_vx = env.target_vx if cmd_vx is None else cmd_vx
    res = {"target_vx": env.target_vx, "eval_cmd_vx": round(cmd_vx, 3), "window_s": seconds,
           "note": "clean_travel_m counts only envs that never fell; travel_m_8s is raw "
                   "displacement and includes topple slide. These numbers come from the "
                   "env this policy TRAINED in -- confirm with verify_policy.py on a "
                   "fresh reload before reporting them (T068)."}
    steps = int(seconds / env.dt)
    # inference_mode (not no_grad): rsl_rl collects rollouts under inference_mode,
    # so env buffers are already inference tensors and in-place writes to them
    # outside that context raise.
    with torch.inference_mode():
        for mode in ("deterministic", "stochastic"):
            env.reset()
            env.commands[:, 0] = cmd_vx
            env.commands[:, 1] = 0.0
            obs = env.obs_buf
            x0 = (V50.FWD_SIGN * env.robot.get_qpos()[:, V50.FWD_AXIS]).clone()
            alive = torch.ones(env.num_envs, dtype=torch.bool, device=env.device)
            travel_at_fall = torch.zeros(env.num_envs, device=env.device)
            vx_acc = air_acc = single_acc = 0.0
            for _ in range(steps):
                o = normalizer(obs) if normalizer is not None else obs
                act = policy.act_inference(o) if mode == "deterministic" else policy.act(o)
                obs, _, _, _ = env.step(act)
                d = V50.FWD_SIGN * env.robot.get_qpos()[:, V50.FWD_AXIS] - x0
                travel_at_fall = torch.where(alive, d, travel_at_fall)
                alive &= ~env.terminated
                vx_acc += (V50.FWD_SIGN * env.lin_vel[:, V50.FWD_AXIS]).mean().item() / steps
                air_acc += env.foot_air_time.mean().item() / steps
                single_acc += (env.contacts.float().sum(dim=1) == 1).float().mean().item() / steps
            raw = (V50.FWD_SIGN * env.robot.get_qpos()[:, V50.FWD_AXIS] - x0).mean().item()
            surv = alive.float().mean().item()
            clean = travel_at_fall[alive].mean().item() if alive.any() else 0.0
            res[f"{mode}_travel_m_8s"] = round(raw, 3)
            res[f"{mode}_clean_travel_m"] = round(clean, 3)
            res[f"{mode}_survival_rate"] = round(surv, 3)
            res[f"{mode}_vx_mean"] = round(vx_acc, 3)
            res[f"{mode}_mean_air_time"] = round(air_acc, 3)
            res[f"{mode}_single_contact_frac"] = round(single_acc, 3)
    res["eval_forward_travel_m_8s"] = res["deterministic_clean_travel_m"]
    res["eval_clean_travel_m"] = res["deterministic_clean_travel_m"]
    res["eval_survival_rate"] = res["deterministic_survival_rate"]
    res["eval_vx_mean"] = res["deterministic_vx_mean"]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=1500)
    ap.add_argument("--n-envs", type=int, default=4096)
    ap.add_argument("--rollout", type=int, default=24)
    ap.add_argument("--out", default=r"C:\v50_work\autonomy\walk_rsl_smoke")
    ap.add_argument("--resume", default=None)
    ap.add_argument("--entropy", type=float, default=0.005)
    ap.add_argument("--init-noise-std", type=float, default=1.0)
    ap.add_argument("--ref-json", default=None)
    ap.add_argument("--terrain", default="none",
                    choices=["none", "stairs", "stairs_down", "slope_up", "slope_down"])
    ap.add_argument("--episode-length-s", type=float, default=20.0)
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--tensorboard", action="store_true")
    # Terrain work needs a slower command range and more dynamics diversity than
    # flat ground: the 8 deg slope policy trained on [0.15,0.35] only held up at
    # ~0.18 m/s, and 8 DR bands let it specialise (T068).
    ap.add_argument("--cmd-vx-min", type=float, default=None)
    ap.add_argument("--cmd-vx-max", type=float, default=None)
    ap.add_argument("--dr-groups", type=int, default=None)
    ap.add_argument("--dr-mass", default=None, help="lo,hi mass scale")
    ap.add_argument("--dr-kp", default=None, help="lo,hi PD gain scale")
    ap.add_argument("--eval-vx", type=float, default=None,
                    help="speed used by the built-in eval (default: reference clip "
                         "speed, which is the TOP of the training range)")
    # Exteroception: forward terrain height scan (needed for stairs, T069).
    ap.add_argument("--height-scan", action="store_true",
                    help="append a forward terrain height scan to the observation")
    ap.add_argument("--scan-ahead", default=None,
                    help="comma list of forward look-ahead distances (m); "
                         "default 0.0,0.1,...,1.0")
    ap.add_argument("--stair-height", type=float, default=None,
                    help="override step height (m) for the stair curriculum")
    ap.add_argument("--resume-surgery", action="store_true",
                    help="load a smaller-obs checkpoint (e.g. the blind flat/slope "
                         "policy) into this larger height-scan network: existing "
                         "input weights are copied, the new scan columns start at "
                         "zero, so the policy begins identical to the source.")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    from rsl_rl.runners import OnPolicyRunner

    cfg = {"terrain": args.terrain, "episode_length_s": args.episode_length_s}
    if args.no_push:
        cfg["push_vel"] = 0.0
    if args.cmd_vx_min is not None or args.cmd_vx_max is not None:
        lo, hi = _default_cmd_vx()
        cfg["cmd_vx"] = [args.cmd_vx_min if args.cmd_vx_min is not None else lo,
                         args.cmd_vx_max if args.cmd_vx_max is not None else hi]
    if args.dr_groups is not None:
        cfg["dr_groups"] = args.dr_groups
    for key, val in (("dr_mass_scale", args.dr_mass), ("dr_kp_scale", args.dr_kp)):
        if val:
            cfg[key] = [float(v) for v in val.split(",")]
    if args.stair_height is not None:
        cfg["stair_height"] = args.stair_height
    if args.height_scan:
        hs = {}
        if args.scan_ahead:
            hs["ahead"] = [float(v) for v in args.scan_ahead.split(",")]
        cfg["height_scan"] = hs
    env = V50WalkEnv(args.n_envs, args.out, cfg=cfg, ref_json=args.ref_json)
    print(f"ENV ready: obs={env.num_obs} act={env.num_actions} stand_z={env.stand_z:.4f} "
          f"target_vx={env.target_vx} gait_period={env.gait_period}", flush=True)

    # tensorboard is NOT installed in genesis_venv and pulling it in risks the
    # torch 2.11.0+cu128 build; status.json is the primary telemetry. Opt in
    # explicitly with --tensorboard once the package is present.
    # rsl_rl 2.3.3 dereferences log_dir unconditionally in store_code_state(),
    # so log_dir=None crashes; keep a real dir and mute logging via disable_logs.
    runner = OnPolicyRunner(env, train_cfg(args), log_dir=os.path.join(args.out, "tb"),
                            device="cuda")
    if not args.tensorboard:
        runner.disable_logs = True
        runner.logger_type = "tensorboard"   # save() reads it even when muted
    if args.resume and args.resume_surgery:
        load_with_surgery(runner, args.resume, env.num_scan)
    elif args.resume:
        runner.load(args.resume)

    status = StatusWriter(env, args.out, args.iterations)
    # rsl_rl runs the whole loop internally; drive it in slices so status.json
    # stays live for the supervisor and the dashboard.
    CHUNK = 25
    done = 0
    while done < args.iterations:
        n = min(CHUNK, args.iterations - done)
        runner.learn(num_learning_iterations=n, init_at_random_ep_len=(done == 0))
        done += n
        p = status.write(done)
        print(f"it {done:5d}/{args.iterations} | ret {p['mean_episode_return']:8.2f} | "
              f"ep {p['mean_episode_len_s']:5.2f}s | fall {p['fall_rate']:4.2f}"
              f"(tilt {p['fall_by_tilt']:.2f}/low {p['fall_by_low']:.2f}/"
              f"col {p['fall_by_collision']:.2f}) | "
              f"vx {p['vx_mean']:5.3f} | up {p['upright']:4.2f} | "
              f"1foot {p['single_contact_frac']:4.2f} | air {p['mean_air_time']:.3f}", flush=True)
        runner.save(os.path.join(args.out, "latest.pt"))

    runner.save(os.path.join(args.out, "latest.pt"))
    policy = runner.alg.policy
    normalizer = runner.obs_normalizer if getattr(runner, "empirical_normalization", False) else None
    if normalizer is not None:
        normalizer.eval()
    ev = evaluate(env, policy, normalizer, cmd_vx=args.eval_vx)
    with open(os.path.join(args.out, "eval.json"), "w", encoding="utf-8") as f:
        json.dump(ev, f, indent=2)
    print("EVAL:", json.dumps(ev), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
