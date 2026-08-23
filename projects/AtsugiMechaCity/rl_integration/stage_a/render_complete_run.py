# -*- coding: utf-8 -*-
"""コースを完走したエピソードだけを切り出して動画にする。

v44 の corridor 完走率は約10%(push有) / 26%(push無)なので、1回描画しても
完走個体は撮れない。ここでは1体で複数エピソードを連続で回して**全フレームを
描画しておき**、終了後に完走したエピソードのフレームだけを mp4 にする。
seed の再現性に依存しないので確実に撮れる。

注意: n_envs=1 では DR は build 時に1回だけ引かれ、全エピソードで共通になる
(_apply_dr は reset では引き直さない)。不運な質量/KPを引くと何回やっても
完走しないので、既定で DR は公称値に固定する(--with-dr で有効化)。

描画専用。学習・評価の数値経路には触れない。方策は**学習したのと同じ env**で
動かす(INC-141 trap #8)。
"""
import argparse, math, os, sys

sys.path.insert(0, r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\stage_a")
import torch
from v50_walk_env import V50WalkEnv, V50
import train_v50_walk_tracking as T
import train_v50_walk_rsl as R


def course_len(terrain, stair_h=None):
    if terrain in T.CORRIDOR_VARIANTS:
        return T._corridor_layout(stair_h, terrain)[-1]["prog1"]
    if terrain in ("stairs", "stairs_down"):
        return T.TERRAIN_FLAT_RUNUP + T.TERRAIN_STAIR_D * T.TERRAIN_STAIR_N
    if terrain in ("slope_up", "slope_down"):
        return (T.TERRAIN_FLAT_RUNUP
                + 2 * T.TERRAIN_SLOPE_HALF * math.cos(math.radians(T.TERRAIN_SLOPE_DEG)))
    return 5.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", default=r"C:\v50_work\autonomy\complete_run")
    ap.add_argument("--terrain", default="corridor")
    ap.add_argument("--ref-json", default=None)
    ap.add_argument("--episodes", type=int, default=12, help="試行回数の上限")
    ap.add_argument("--cmd-vx", type=float, default=0.27)
    ap.add_argument("--every", type=int, default=10, help="N制御ステップ毎に1フレーム")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--height-scan", action="store_true")
    ap.add_argument("--stair-height", type=float, default=None)
    ap.add_argument("--with-push", action="store_true",
                    help="外乱pushを有効にする(学習条件。完走率が約10%まで下がる)")
    ap.add_argument("--with-dr", action="store_true",
                    help="DRを有効にする。n_envs=1では全エピソード共通の値が引かれるので非推奨")
    ap.add_argument("--res", default="1280,720")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    L = course_len(args.terrain, args.stair_height)
    # 1エピソードの上限。コース踏破に要する時間の1.6倍(評価規約と同じ)に余裕を足す。
    ep_s = max(20.0, L / args.cmd_vx * 1.6) + 10.0
    res = tuple(int(v) for v in args.res.split(","))

    cfg = {"terrain": args.terrain, "episode_length_s": ep_s,
           "cmd_vx": [args.cmd_vx, args.cmd_vx], "cmd_zero_prob": 0.0,
           "camera": {"res": res, "pos": (3.0, 0.5, 0.6), "lookat": (0.0, 0.0, 0.0),
                      "fov": 40}}
    if args.height_scan or args.terrain in T.CORRIDOR_VARIANTS:
        cfg["height_scan"] = {}
    if args.stair_height is not None:
        cfg["stair_height"] = args.stair_height
    if args.terrain in T.CORRIDOR_VARIANTS:
        cfg["corridor_fixed_start"] = True
    if not args.with_push:
        cfg["push_vel"] = 0.0
    if not args.with_dr:
        cfg["dr_mass_scale"] = [1.0, 1.0]
        cfg["dr_kp_scale"] = [1.0, 1.0]

    env = V50WalkEnv(1, args.out, cfg=cfg, ref_json=args.ref_json)
    print(f"course={L:.2f}m  episode={ep_s:.1f}s  episodes<={args.episodes}  "
          f"push={'on' if args.with_push else 'off'}  dr={'on' if args.with_dr else 'off'}",
          flush=True)

    from rsl_rl.runners import OnPolicyRunner

    class _A:
        rollout, entropy, init_noise_std = 24, 0.005, 1.0

    runner = OnPolicyRunner(env, R.train_cfg(_A()), log_dir=os.path.join(args.out, "tb"),
                            device="cuda")
    runner.disable_logs = True
    runner.logger_type = "tensorboard"
    runner.load(args.ckpt)
    policy = runner.alg.policy
    normalizer = (runner.obs_normalizer
                  if getattr(runner, "empirical_normalization", False) else None)
    if normalizer is not None:
        normalizer.eval()
    print(f"policy: {args.ckpt}  normalizer: {'on' if normalizer else 'off'}", flush=True)

    from PIL import Image
    obs, _ = env.reset()
    ep_steps = int(ep_s / env.dt)
    ep_idx = 0
    ep_frames = []          # 現エピソードのフレーム
    ep_max_prog = 0.0
    winner = None           # (ep_idx, frames, max_prog)
    attempts = []

    def flush_episode():
        nonlocal winner
        attempts.append((ep_idx, ep_max_prog, len(ep_frames)))
        done_mark = "完走" if ep_max_prog >= L - 0.05 else "途中終了"
        print(f"  ep{ep_idx:02d}: max_prog {ep_max_prog:6.2f}m / {L:.2f}m  "
              f"{done_mark}  frames={len(ep_frames)}", flush=True)
        if winner is None and ep_max_prog >= L - 0.05:
            winner = (ep_idx, list(ep_frames), ep_max_prog)

    total_steps = ep_steps * args.episodes
    for k in range(total_steps):
        with torch.no_grad():
            o = normalizer(obs) if normalizer is not None else obs
            act = policy.act_inference(o)
        obs, _, rst, _ = env.step(act)
        prog = float(-env.pos[0, V50.FWD_AXIS])
        ep_max_prog = max(ep_max_prog, prog)
        if k % args.every == 0:
            z = float(env.pos[0, 2])
            y = float(env.pos[0, V50.FWD_AXIS])
            # 追従カメラ。高低差のある地形で機体が画角外に出ないよう足元基準にする
            # (render_walk_rsl.py と同じ扱い)。
            cam_z = z - 0.43
            env.camera.set_pose(pos=(3.0, y + 0.5, cam_z + 0.6), lookat=(0.0, y, cam_z))
            rgb = env.camera.render(rgb=True)[0]
            p = os.path.join(args.out, f"run_{ep_idx:02d}_{k:06d}.png")
            Image.fromarray(rgb).save(p)
            ep_frames.append(p)
        if bool(rst[0]):
            flush_episode()
            if winner is not None:
                break
            ep_idx += 1
            ep_frames, ep_max_prog = [], 0.0
    else:
        if ep_frames:
            flush_episode()

    if winner is None:
        best = max(attempts, key=lambda a: a[1]) if attempts else None
        print(f"完走個体は撮れなかった。最良 ep{best[0]} max_prog {best[1]:.2f}m"
              if best else "エピソードが1つも終わらなかった", flush=True)
        sys.exit(2)

    w_idx, w_frames, w_prog = winner
    print(f"完走: ep{w_idx} max_prog {w_prog:.2f}m  frames={len(w_frames)}", flush=True)
    try:
        import imageio.v2 as imageio
        mp4 = os.path.join(args.out, f"complete_ep{w_idx:02d}.mp4")
        with imageio.get_writer(mp4, fps=args.fps, macro_block_size=1) as wr:
            for p in w_frames:
                wr.append_data(imageio.imread(p))
        print(f"mp4: {mp4}", flush=True)
    except Exception as e:                                    # noqa: BLE001
        print(f"[render] mp4 skipped ({e!r}); 完走エピソードのPNGは "
              f"{args.out} の run_{w_idx:02d}_*.png", flush=True)


if __name__ == "__main__":
    main()
