# -*- coding: utf-8 -*-
"""Rollout renderer + walk check for the rsl_rl (v2) policy.

Why a second renderer: render_walk.py loads the v1 self-contained ActorCritic
(obs 46). The v2 checkpoint is an rsl_rl OnPolicyRunner save -- actor 189->512,
hidden [512,256,128], plus an EmpiricalNormalization state -- so the two are not
interchangeable. This one restores the policy THROUGH OnPolicyRunner so the
observation normalizer is applied exactly as it was in training; skipping the
normalizer silently feeds raw observations to a network trained on normalized
ones and produces a fake "it can't walk" result.

The scene comes from V50WalkEnv with a camera enabled -- the same env class that
was trained, not a copy (INC-141 trap #8).

What this catches that the numeric eval cannot: a policy that games the metric by
crawling or sliding while nominally "upright". Frames + per-step foot contact and
base height are written so the gait can be inspected directly.

  python render_walk_rsl.py --ckpt <run>/latest.pt --out C:\\v50_work\\walk_rsl_frames
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch

import train_v50_walk_tracking as V50
from v50_walk_env import V50WalkEnv
import train_v50_walk_rsl as R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", default=r"C:\v50_work\walk_rsl_frames")
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--ref-json", default=None)
    ap.add_argument("--terrain", default="none")
    ap.add_argument("--height-scan", action="store_true",
                    help="required when the checkpoint was trained with the scan "
                         "(obs 200) -- otherwise the obs dims mismatch")
    ap.add_argument("--stair-height", type=float, default=None)
    ap.add_argument("--corridor-fixed-start", action="store_true",
                    help="terrain=corridor only: always spawn at segment 0, "
                         "offset 0 for a deterministic full-course render")
    ap.add_argument("--cmd-vx", type=float, default=None,
                    help="commanded forward speed (default: reference clip speed)")
    ap.add_argument("--every", type=int, default=5, help="save a frame every N control steps")
    ap.add_argument("--no-push", action="store_true", default=True,
                    help="disable random pushes so the gait is seen cleanly")
    ap.add_argument("--stochastic", action="store_true")
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--no-dr", action="store_true",
                    help="nominal dynamics. With 1 env, domain randomization draws a "
                         "SINGLE mass/gain sample, so an unlucky draw misrepresents "
                         "the policy; disable it for a clean demo.")
    ap.add_argument("--no-reset", action="store_true",
                    help="do not respawn on termination, so the clip is one continuous "
                         "rollout and a fall stays visible instead of being hidden by "
                         "an auto-reset teleport.")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    cfg = {"terrain": args.terrain,
           "episode_length_s": max(args.seconds * 2, 20.0),
           "camera": {"res": (960, 540), "pos": (3.0, 0.5, 0.6),
                      "lookat": (0.0, 0.0, 0.0), "fov": 40}}
    if args.height_scan:
        cfg["height_scan"] = {}
    if args.stair_height is not None:
        cfg["stair_height"] = args.stair_height
    if args.corridor_fixed_start:
        cfg["corridor_fixed_start"] = True
    if args.no_push:
        cfg["push_vel"] = 0.0
    if args.no_dr:
        cfg["dr_mass_scale"] = [1.0, 1.0]
        cfg["dr_kp_scale"] = [1.0, 1.0]
    env = V50WalkEnv(1, args.out, cfg=cfg, ref_json=args.ref_json)

    # Restore policy + observation normalizer via the runner that wrote them.
    from rsl_rl.runners import OnPolicyRunner

    class _A:  # train_cfg() only reads these
        rollout, entropy, init_noise_std = 24, 0.005, 1.0
    runner = OnPolicyRunner(env, R.train_cfg(_A()), log_dir=os.path.join(args.out, "tb"),
                            device="cuda")
    runner.disable_logs = True
    runner.logger_type = "tensorboard"
    runner.load(args.ckpt)
    policy = runner.alg.policy
    normalizer = runner.obs_normalizer if getattr(runner, "empirical_normalization", False) else None
    if normalizer is not None:
        normalizer.eval()
    print(f"policy: {args.ckpt}  normalizer: {'on' if normalizer else 'off'}", flush=True)

    from PIL import Image
    steps = int(args.seconds / env.dt)
    cmd_vx = args.cmd_vx if args.cmd_vx is not None else env.target_vx

    env.reset()
    if args.no_reset:
        env.reset_idx = lambda idx: None      # freeze respawns for a continuous clip
    env.commands[:, 0] = cmd_vx
    env.commands[:, 1] = 0.0
    obs = env.obs_buf
    x0 = float(V50.FWD_SIGN * env.robot.get_qpos()[0, V50.FWD_AXIS])
    trace, frames = [], []
    min_up, min_z, first_fall = 1.0, 10.0, None

    with torch.inference_mode():
        for k in range(steps):
            o = normalizer(obs) if normalizer is not None else obs
            act = policy.act(o) if args.stochastic else policy.act_inference(o)
            obs, _, _, _ = env.step(act)

            qp = env.robot.get_qpos()
            y = float(qp[0, V50.FWD_AXIS])
            z = float(qp[0, 2])
            up = float(env.upright[0])
            cL, cR = bool(env.contacts[0, 0]), bool(env.contacts[0, 1])
            travel = float(V50.FWD_SIGN * qp[0, V50.FWD_AXIS]) - x0
            min_up, min_z = min(min_up, up), min(min_z, z)
            if first_fall is None and bool(env.terminated[0]):
                first_fall = round(k * env.dt, 2)
            trace.append({"t": round(k * env.dt, 3), "z": round(z, 4), "upright": round(up, 4),
                          "travel": round(travel, 4), "contact_L": int(cL), "contact_R": int(cR)})

            if k % args.every == 0 or k == steps - 1:
                env.camera.set_pose(pos=(3.0, y + 0.5, 0.6), lookat=(0.0, y, 0.0))
                rgb = env.camera.render(rgb=True)[0]
                p = os.path.join(args.out, f"walk_{k:04d}.png")
                Image.fromarray(rgb).save(p)
                frames.append(p)

    # Stance pattern is the tell: alternating single-foot support = walking;
    # both feet permanently down = shuffling; neither = sliding on the body.
    both = sum(1 for x in trace if x["contact_L"] and x["contact_R"]) / len(trace)
    single = sum(1 for x in trace if x["contact_L"] != x["contact_R"]) / len(trace)
    none_ = sum(1 for x in trace if not x["contact_L"] and not x["contact_R"]) / len(trace)
    steps_taken = sum(1 for a, b in zip(trace, trace[1:])
                      if (a["contact_L"], a["contact_R"]) != (b["contact_L"], b["contact_R"]))
    res = {"schema": "clawstack.walk_check.v2", "ckpt": args.ckpt,
           "seconds": args.seconds, "commanded_vx": round(cmd_vx, 3),
           "mode": "stochastic" if args.stochastic else "deterministic",
           "pushes": not args.no_push,
           "final_travel_m": trace[-1]["travel"], "mean_vx": round(trace[-1]["travel"] / args.seconds, 3),
           "fell": first_fall is not None, "first_fall_sec": first_fall,
           "min_upright": round(min_up, 3), "min_z": round(min_z, 3),
           "stand_z": round(env.stand_z, 3),
           "double_support_frac": round(both, 3), "single_support_frac": round(single, 3),
           "flight_frac": round(none_, 3), "contact_transitions": steps_taken,
           "frames": len(frames), "frames_dir": args.out}
    with open(os.path.join(args.out, "walk_check.json"), "w", encoding="utf-8") as f:
        json.dump({"result": res, "trace": trace}, f, indent=2)

    # optional mp4 (imageio-ffmpeg is already in this venv).
    # macro_block_size=1 keeps the native 960x540 instead of padding to 960x544.
    try:
        import imageio.v2 as imageio
        mp4 = os.path.join(args.out, "walk.mp4")
        with imageio.get_writer(mp4, fps=args.fps, macro_block_size=1) as w:
            for p in frames:
                w.append_data(imageio.imread(p))
        res["mp4"] = mp4
        print("MP4:", mp4, flush=True)
    except Exception as e:                                   # noqa: BLE001
        # ffmpeg is spawned as a subprocess and its pipes break when this
        # script's own stdout is piped (Windows OSError 9). The PNGs are the
        # real artifact; re-encode them separately if the mp4 is wanted.
        print(f"[render] mp4 skipped ({e!r}); PNG frames are in {args.out}", flush=True)

    print("WALK_CHECK:", json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
