# -*- coding: utf-8 -*-
"""Independent verification of a saved policy in a FRESH environment.

WHY THIS EXISTS (2026-07-24). train_v50_walk_rsl.py ends by calling evaluate()
on the environment it just trained in. That measurement is not trustworthy on its
own: the slope run printed survival_rate 0.814, but reloading the very
checkpoint it had just written into a fresh env gave 0.069 -- and the trainer's
own evaluate() reproduced 0.069 too. The policy was fine (the same checkpoint
scores 0.88 on flat); the *measurement* was a false positive.

So: never report a training-time number. Reload the checkpoint into a fresh env
and measure here.

Two things this reports that survival alone cannot:
  * climb_ratio -- height actually gained divided by the height the terrain
    offers at the distance travelled. An env that drifts off the 1.6 m-wide ramp
    and strolls along the flat floor survives perfectly while climbing nothing,
    and only this ratio exposes it.
  * a speed sweep -- evaluate() pins the command to target_vx, the TOP of the
    training command range, which badly understates a policy that can climb at a
    sensible pace. On the 8 deg slope the same checkpoint scores 0.40 at
    0.18 m/s and 0.07-0.25 at 0.331 m/s.

  python verify_policy.py --ckpt <x.pt> --terrain slope_up --speeds 0.18,0.25,0.331
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch

import train_v50_walk_tracking as V50
from v50_walk_env import V50WalkEnv
import train_v50_walk_rsl as R

RAMP_HALF_WIDTH = 0.8            # terrain_xml geom size x half


class _Args:                     # train_cfg() only reads these three
    rollout, entropy, init_noise_std = 24, 0.005, 1.0


def load_policy(env, ckpt, out):
    from rsl_rl.runners import OnPolicyRunner
    runner = OnPolicyRunner(env, R.train_cfg(_Args()), log_dir=os.path.join(out, "tb"),
                            device="cuda")
    runner.disable_logs = True
    runner.logger_type = "tensorboard"
    runner.load(ckpt)
    norm = runner.obs_normalizer if getattr(runner, "empirical_normalization", False) else None
    if norm is not None:
        norm.eval()
    return runner.alg.policy, norm


@torch.inference_mode()   # must also cover reset(): once a pass runs under
                          # inference_mode the env buffers become inference
                          # tensors, and reset() writes to them in place.
def run_speed(env, policy, norm, cmd_vx, seconds, terrain):
    steps = int(seconds / env.dt)
    env.reset()
    env.commands[:, 0] = cmd_vx
    env.commands[:, 1] = 0.0
    obs = env.obs_buf
    q0 = env.robot.get_qpos()
    y0 = (V50.FWD_SIGN * q0[:, V50.FWD_AXIS]).clone()
    x0, z0 = q0[:, 0].clone(), q0[:, 2].clone()
    alive = torch.ones(env.num_envs, dtype=torch.bool, device=env.device)
    last = {}
    single = 0.0
    if True:
        for _ in range(steps):
            o = norm(obs) if norm is not None else obs
            obs, _, _, _ = env.step(policy.act_inference(o))
            qp = env.robot.get_qpos()
            for k, v in (("z", qp[:, 2]), ("y", qp[:, V50.FWD_AXIS]), ("x", qp[:, 0])):
                last[k] = torch.where(alive, v, last.get(k, v))
            single += (env.contacts.float().sum(dim=1) == 1).float().mean().item() / steps
            alive &= ~env.terminated

    travel = V50.FWD_SIGN * last["y"] - y0
    gained = last["z"] - z0
    offered = V50.terrain_dz(last["y"], terrain)
    lat = (last["x"] - x0).abs()
    on = lat < RAMP_HALF_WIDTH
    ok = alive & on
    r = {"cmd_vx": round(cmd_vx, 3),
         "survival_rate": round(alive.float().mean().item(), 3),
         "single_contact_frac": round(single, 3),
         "mean_lateral_drift_m": round(lat[alive].mean().item(), 3) if alive.any() else None,
         "frac_survivors_on_track": round(on[alive].float().mean().item(), 3) if alive.any() else None}
    if ok.any():
        g, e = gained[ok].mean().item(), offered[ok].mean().item()
        r["travel_m"] = round(travel[ok].mean().item(), 3)
        r["height_gained_m"] = round(g, 3)
        r["terrain_offers_m"] = round(e, 3)
        r["climb_ratio"] = round(g / e, 3) if abs(e) > 1e-3 else None
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--terrain", default="none")
    ap.add_argument("--speeds", default="", help="comma list; default = target_vx only")
    ap.add_argument("--n-envs", type=int, default=512)
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--ref-json", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--push", type=float, default=0.0)
    ap.add_argument("--dr", action="store_true", help="enable domain randomization")
    ap.add_argument("--height-scan", action="store_true",
                    help="required when the checkpoint was trained with the scan (obs 200)")
    ap.add_argument("--stair-height", type=float, default=None)
    args = ap.parse_args()
    out = args.out or os.path.join(os.environ.get("TEMP", "."), "verify_policy")
    os.makedirs(out, exist_ok=True)

    cfg = {"terrain": args.terrain, "episode_length_s": max(args.seconds * 2, 20.0),
           "push_vel": args.push}
    if not args.dr:
        cfg["dr_mass_scale"] = [1.0, 1.0]
        cfg["dr_kp_scale"] = [1.0, 1.0]
    if args.height_scan:
        cfg["height_scan"] = {}
    if args.stair_height is not None:
        cfg["stair_height"] = args.stair_height
    env = V50WalkEnv(args.n_envs, out, cfg=cfg, ref_json=args.ref_json)
    policy, norm = load_policy(env, args.ckpt, out)

    speeds = [float(s) for s in args.speeds.split(",") if s.strip()] or [env.target_vx]
    res = {"schema": "clawstack.verify_policy.v1", "ckpt": args.ckpt,
           "terrain": args.terrain, "n_envs": args.n_envs, "seconds": args.seconds,
           "domain_randomization": args.dr, "push_vel": args.push,
           "note": "fresh-env reload; training-time evaluate() numbers are not trusted",
           "by_speed": [run_speed(env, policy, norm, s, args.seconds, args.terrain)
                        for s in speeds]}
    with open(os.path.join(out, "verify_policy.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("VERIFY_POLICY:", json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
