# -*- coding: utf-8 -*-
"""学習済み方策で N 体を同時走行させ、俯瞰の連番PNG + mp4 を出力する。

報道映像でよく見る「大量のエージェントが並んで同時に学習している」ビューと同じ形式。
env をグリッドに並べるのは Genesis の scene.build(env_spacing=..., n_envs_per_row=...)。
地形は robot と同じ MJCF の worldbody に入っているので env ごとに複製される
(実測確認済み)。get_pos() は env ローカル座標を返すため、terrain_dz・終了判定・
報酬はグリッド配置の影響を受けない。

描画専用。学習・評価の数値経路には触れない。方策は**学習したのと同じ env**で
動かす(INC-141 trap #8: 描画側でXMLを複製すると黙って乖離する)。

例:
  python render_grid.py --ckpt <ckpt> --terrain corridor --height-scan \
      --corridor-fixed-start --ref-json <ref> --n-envs 16 --seconds 60
"""
import argparse, os, sys

sys.path.insert(0, r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\stage_a")
import torch
from v50_walk_env import V50WalkEnv, V50
import train_v50_walk_tracking as T
import train_v50_walk_rsl as R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--out", default=r"C:\v50_work\autonomy\grid_render")
    ap.add_argument("--terrain", default="corridor")
    ap.add_argument("--ref-json", default=None)
    ap.add_argument("--n-envs", type=int, default=16)
    # Genesis の n_envs_per_row は **y方向(コース進行方向)の本数**で、行は x 方向に
    # 増える(_parallelize)。corridor は y に19.5m伸びるので、横並びを増やしたいなら
    # ここは小さくする(2 なら y に2本、x に n/2 本の横並びになる)。
    ap.add_argument("--per-row", type=int, default=2)
    ap.add_argument("--seconds", type=float, default=60.0)
    ap.add_argument("--cmd-vx", type=float, default=0.27)
    ap.add_argument("--every", type=int, default=5, help="N制御ステップ毎に1フレーム")
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--height-scan", action="store_true")
    ap.add_argument("--corridor-fixed-start", action="store_true")
    ap.add_argument("--stair-height", type=float, default=None)
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--no-dr", action="store_true",
                    help="DRを切る。既定8グループは評価再現性を壊すが、描画では"
                         "見た目のばらつきが欲しいので既定は有効のまま")
    # 画角。既定はコース長から自動で決める(--cam-* を渡すと上書き)。
    ap.add_argument("--cam-pos", default=None, help="x,y,z")
    ap.add_argument("--cam-lookat", default=None, help="x,y,z")
    ap.add_argument("--cam-fov", type=float, default=45.0)
    ap.add_argument("--cam-far", type=float, default=400.0,
                    help="遠クリップ面。Genesis既定の20mでは俯瞰は空しか映らない")
    ap.add_argument("--res", default="1920,1080", help="w,h")
    ap.add_argument("--spacing", default=None, help="x,y。既定はコース長から自動")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    # コース長からグリッド間隔を決める。corridor は前方(-Y)に長いので y 間隔を広く取る。
    if args.terrain in T.CORRIDOR_VARIANTS:
        course = T._corridor_layout(args.stair_height, args.terrain)[-1]["prog1"]
    elif args.terrain in ("stairs", "stairs_down"):
        course = T.TERRAIN_FLAT_RUNUP + T.TERRAIN_STAIR_D * T.TERRAIN_STAIR_N
    else:
        course = 5.0
    if args.spacing:
        sx, sy = (float(v) for v in args.spacing.split(","))
    else:
        # sx は横並びの間隔(コース幅1.6mなので3.5mで十分)、sy は進行方向の間隔で
        # コース長を超えないと前後のコースが重なる。
        sx, sy = 3.5, course + 4.0

    res = tuple(int(v) for v in args.res.split(","))
    # 画角は build 後に scene.envs_offset(実オフセット)から決める。ここでは仮値。
    cam_pos, cam_lookat = (10.0, 0.0, 10.0), (0.0, 0.0, 0.0)

    cfg = {"terrain": args.terrain,
           "episode_length_s": max(args.seconds * 2, 20.0),
           "cmd_vx": [args.cmd_vx, args.cmd_vx], "cmd_zero_prob": 0.0,
           "env_spacing": (sx, sy), "n_envs_per_row": args.per_row,
           # Genesis のカメラ既定 far は 20m。俯瞰では視距離がこれを軽く超え、
           # 何も映らず空だけになる。グリッド全体が入る距離まで伸ばす。
           "camera": {"res": res, "pos": cam_pos, "lookat": cam_lookat,
                      "fov": args.cam_fov, "far": args.cam_far}}
    if args.height_scan or args.terrain in T.CORRIDOR_VARIANTS:
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

    env = V50WalkEnv(args.n_envs, args.out, cfg=cfg, ref_json=args.ref_json)

    # 実オフセットから画角を決める。Genesis の配置規則(_parallelize)は
    #     offset_x = (i // n_envs_per_row) * env_spacing[0]
    #     offset_y = (i %  n_envs_per_row) * env_spacing[1]
    # で、**n_envs_per_row は y 方向(コース進行方向)の本数**、行は x 方向に増える。
    # 直感と逆なので、計算し直さず envs_offset をそのまま読む。
    import math as _m
    off = env.scene.envs_offset
    ox, oy = off[:, 0], off[:, 1]
    # 各 env の地形は x が原点±1.0m(コース幅0.8m)、y は原点から前方(-Y)へ course。
    x_lo, x_hi = float(ox.min()) - 1.0, float(ox.max()) + 1.0
    y_lo, y_hi = float(oy.min()) - course, float(oy.max()) + 0.5
    cx, cy = (x_lo + x_hi) / 2, (y_lo + y_hi) / 2
    span = max(x_hi - x_lo, y_hi - y_lo)
    if args.cam_lookat:
        cam_lookat = tuple(float(v) for v in args.cam_lookat.split(","))
    else:
        cam_lookat = (cx, cy, 0.0)
    if args.cam_pos:
        cam_pos = tuple(float(v) for v in args.cam_pos.split(","))
    else:
        # 斜め上から見下ろす報道映像風。span が収まる距離を fov から逆算する。
        # 斜めに見下ろすほど地面は画面内で伸びるので、余裕を大きめに取り、
        # 俯角も強め(高さ優位)にして footprint を圧縮する。
        dist = span / (2 * _m.tan(_m.radians(args.cam_fov) / 2)) * 1.55
        cam_pos = (cx + dist * 0.38, cy + dist * 0.30, dist * 0.86)
    # up は渡さない。明示すると画が回ってグリッドが斜めに寝る(2026-08-23 実測)。
    env.camera.set_pose(pos=cam_pos, lookat=cam_lookat)
    rows = (args.n_envs + args.per_row - 1) // args.per_row
    print(f"grid: x方向{rows}列 x y方向{args.per_row}本  spacing=({sx:.1f}, {sy:.1f})  "
          f"course={course:.2f}m  bbox x[{x_lo:.1f},{x_hi:.1f}] y[{y_lo:.1f},{y_hi:.1f}]  "
          f"cam={tuple(round(v, 1) for v in cam_pos)} -> {tuple(round(v, 1) for v in cam_lookat)}",
          flush=True)

    from rsl_rl.runners import OnPolicyRunner

    class _A:                       # train_cfg() が読むのはこの3つだけ
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
    steps = int(args.seconds / env.dt)
    frames = []
    alive_hist = []
    for k in range(steps):
        with torch.no_grad():
            o = normalizer(obs) if normalizer is not None else obs
            act = policy.act_inference(o)
        obs, _, _, _ = env.step(act)
        if k % args.every == 0 or k == steps - 1:
            rgb = env.camera.render(rgb=True)[0]
            p = os.path.join(args.out, f"grid_{k:05d}.png")
            Image.fromarray(rgb).save(p)
            frames.append(p)
            # 進捗の目安。倒れた env は自動リセットされるので「今どれだけ前に
            # 進んでいるか」の中央値を出す(踏破率の代わりではない)。
            prog = (-env.pos[:, V50.FWD_AXIS]).clamp(min=0.0)
            alive_hist.append(float(prog.median()))
    print(f"frames: {len(frames)}  中央prog 最終 {alive_hist[-1]:.2f}m", flush=True)

    try:
        import imageio.v2 as imageio
        mp4 = os.path.join(args.out, "grid.mp4")
        with imageio.get_writer(mp4, fps=args.fps, macro_block_size=1) as w:
            for p in frames:
                w.append_data(imageio.imread(p))
        print(f"mp4: {mp4}", flush=True)
    except Exception as e:                                    # noqa: BLE001
        print(f"[render] mp4 skipped ({e!r}); PNG は {args.out}", flush=True)


if __name__ == "__main__":
    main()
