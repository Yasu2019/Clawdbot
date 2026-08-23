# -*- coding: utf-8 -*-
"""歩容の自然さを人間の基準値と数値で突き合わせる。

「人間らしくない」は見た目の印象では動かせないので、どの指標がどれだけ外れて
いるかを数字にする。体格が違うので生の m/s や歩幅[m]を人間と直接比べても
意味がない。速度はフルード数 Fr = v^2/(g*L)、歩幅は脚長で無次元化して比べる。

測る項目:
  接地   飛翔期率 / 両脚支持率 / 単脚支持率 / 立脚:遊脚比
  時空間 歩行周期・ケイデンス・歩幅(脚長で正規化)・Fr・速度追従
  関節   膝屈曲角の範囲、立脚中と遊脚中の平均
  協調   腕振りが対側脚と同位相か(shoulder_L と hip_R の相関)
  姿勢   胴体ピッチの平均と振れ幅

外乱pushとDRは既定で切る。人間の歩行分析は無擾乱条件の値であり、DRは
評価の再現性を壊すため(既定8グループしか引かない)。

診断専用。学習・評価の数値経路には触れない。
"""
import argparse, math, sys

sys.path.insert(0, r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\stage_a")
import torch
from v50_walk_env import V50WalkEnv, V50
import train_v50_walk_rsl as R

D = {n: i for i, n in enumerate(V50.DOF_NAMES)}

# 一般的な成人の歩行の基準値(標準的な歩行分析の値)。
HUMAN = {
    "flight_pct": (0.0, "0%(walkingは定義上、両足が同時に離れない)"),
    "double_pct": (20.0, "約20%(片側10%×2回)"),
    "stance_swing": (60.0, "立脚60% : 遊脚40%"),
    "stride_per_leg": (1.55, "歩幅/脚長 ≈ 1.5〜1.6"),
    "froude": (0.25, "快適歩行 Fr≈0.25 / 歩走遷移 Fr≈0.5"),
    "knee_swing_deg": (62.0, "遊脚期ピーク 60〜65°"),
    "knee_stance_deg": (17.0, "立脚初期 15〜20°"),
    "trunk_pitch_deg": (5.0, "前後±5°以内"),
    "arm_phase": (1.0, "腕は対側脚と同位相(正の相関)"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--terrain", default="none")
    ap.add_argument("--ref-json", default=None)
    ap.add_argument("--n-envs", type=int, default=256)
    ap.add_argument("--cmd-vx", type=float, default=0.27)
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--height-scan", action="store_true",
                    help="obs200の方策(corridor/stairs系)で必要。平地専用v26はobs189なので付けない")
    ap.add_argument("--with-push", action="store_true")
    ap.add_argument("--with-dr", action="store_true")
    a = ap.parse_args()

    cfg = {"terrain": a.terrain, "episode_length_s": a.seconds + 5.0,
           "cmd_vx": [a.cmd_vx, a.cmd_vx], "cmd_zero_prob": 0.0}
    if a.height_scan:
        cfg["height_scan"] = {}
    if not a.with_push:
        cfg["push_vel"] = 0.0
    if not a.with_dr:
        cfg["dr_mass_scale"] = [1.0, 1.0]
        cfg["dr_kp_scale"] = [1.0, 1.0]

    env = V50WalkEnv(a.n_envs, r"D:\Temp\claude\diag_gait", cfg=cfg, ref_json=a.ref_json)

    from rsl_rl.runners import OnPolicyRunner

    class _A:
        rollout, entropy, init_noise_std = 24, 0.005, 1.0

    runner = OnPolicyRunner(env, R.train_cfg(_A()), log_dir=r"D:\Temp\claude\diag_gait\tb",
                            device="cuda")
    runner.disable_logs = True
    runner.logger_type = "tensorboard"
    runner.load(a.ckpt)
    policy = runner.alg.policy
    norm = runner.obs_normalizer if getattr(runner, "empirical_normalization", False) else None
    if norm is not None:
        norm.eval()

    obs, _ = env.reset()
    # 脚長 = 立位での股関節高さ(床面から)。Fr と歩幅の無次元化に使う。
    #
    # **stand_z - foot_stand_z で出してはいけない**。foot_stand_z は spawn_dz を
    # 引いた補正済みの量で、stand_z とは基準が違う(引き算すると 1.23m という
    # 機体全長1.46mと矛盾する値になる。実際に一度その誤りを出した)。
    # 立位の link 位置を**同一フレームで1回読み**、床面の名前付き定数 FLOOR_TOP
    # からの高さを取る。
    import train_v50_walk_tracking as _T
    _names = [l.name for l in env.robot.links]
    _hip = _names.index("upper_leg_L")
    _rest = env.robot.get_links_pos()[0]
    leg_len = float(_rest[_hip, 2]) - _T.FLOOR_TOP
    foot_z_rest = float(_rest[_names.index("foot_L"), 2])

    steps = int(a.seconds / env.dt)
    C, VX, KN, HIPS, SHO, PITCH, ALIVE = [], [], [], [], [], [], []
    CLR = []
    for _ in range(steps):
        with torch.no_grad():
            o = norm(obs) if norm is not None else obs
            act = policy.act_inference(o)
        obs, _, rst, _ = env.step(act)
        C.append(env.contacts.clone())
        CLR.append(env.foot_clearance.clone())
        VX.append((V50.FWD_SIGN * env.lin_vel[:, V50.FWD_AXIS]).clone())
        q = env.robot.get_dofs_position(dofs_idx_local=env.dof_idx)
        KN.append(q[:, [D["knee_L"], D["knee_R"]]].clone())
        HIPS.append(q[:, [D["hip_L"], D["hip_R"]]].clone())
        SHO.append(q[:, [D["shoulder_L"], D["shoulder_R"]]].clone())
        g = env.grav
        PITCH.append(torch.atan2(V50.FWD_SIGN * g[:, V50.FWD_AXIS],
                                 (-g[:, 2]).clamp(min=1e-6)).clone())
        # 転倒した env は歩容統計から外す(倒れた後の値は歩行ではない)。
        ALIVE.append((~rst.bool() if rst.dtype != torch.bool else ~rst).clone())

    C = torch.stack(C)                       # (T,N,2)
    CLR = torch.stack(CLR)                   # (T,N,2) 立位足高さからの持ち上げ量[m]
    VX = torch.stack(VX); KN = torch.stack(KN)
    HIPS = torch.stack(HIPS); SHO = torch.stack(SHO); PITCH = torch.stack(PITCH)
    ALIVE = torch.stack(ALIVE)
    # 一度でも転倒した env は全区間を除外する。
    keep = ALIVE.all(dim=0)
    n_keep = int(keep.sum())
    if n_keep == 0:
        print("転倒せずに走り切った env が無い。歩容統計を出せない。")
        sys.exit(2)
    C, VX, KN = C[:, keep], VX[:, keep], KN[:, keep]
    CLR = CLR[:, keep]
    HIPS, SHO, PITCH = HIPS[:, keep], SHO[:, keep], PITCH[:, keep]

    nfeet = C.sum(dim=2)                     # (T,N) 0/1/2
    flight = (nfeet == 0).float().mean().item() * 100
    dbl = (nfeet == 2).float().mean().item() * 100
    sgl = (nfeet == 1).float().mean().item() * 100
    # 立脚:遊脚は片脚あたりの接地率で見る。
    stance = C.float().mean().item() * 100

    # 歩行周期: 左足の接地開始(立ち上がりエッジ)の間隔。
    #
    # 接地のチャタリング(数ステップだけ離れて戻る)を1歩と数えると周期が過小に、
    # ケイデンスが過大に出る。生値と、近接エッジを1つにまとめた debounce 値の
    # 両方を出して、チャタリングが効いているかどうかを見えるようにする。
    def periods_from(td, min_gap_steps):
        out = []
        for e in range(td.shape[1]):
            idx = torch.nonzero(td[:, e]).flatten().tolist()
            merged = []
            for i in idx:
                if not merged or i - merged[-1] >= min_gap_steps:
                    merged.append(i)
            if len(merged) >= 3:
                d = [merged[k + 1] - merged[k] for k in range(len(merged) - 1)]
                out.append(sum(d) / len(d) * env.dt)
        return sum(out) / len(out) if out else float("nan")

    td = (C[1:, :, 0] & ~C[:-1, :, 0])
    period_raw = periods_from(td, 1)
    period = periods_from(td, int(round(0.08 / env.dt)))   # 0.08秒未満の再接地は同一歩とみなす

    vx = VX.mean().item()
    stride = vx * period if period == period else float("nan")
    fr = vx * vx / (9.81 * leg_len)
    cadence = 2 * 60.0 / period if period == period else float("nan")

    # 膝: 立脚中(その脚が接地)と遊脚中で分ける。符号規約が不明なので絶対量の
    # 振れ幅(range)を主指標にし、平均も併記する。
    kn_deg = KN * 180.0 / math.pi
    swing_mask = ~C
    kn_swing = kn_deg[swing_mask].abs()
    kn_stance = kn_deg[C].abs()
    kn_range = (kn_deg.amax(dim=0) - kn_deg.amin(dim=0)).mean().item()

    # 腕振り: 人間は対側同位相。shoulder_L と hip_R の相関を env ごとに出して平均。
    def corr(x, y):
        x = x - x.mean(dim=0, keepdim=True)
        y = y - y.mean(dim=0, keepdim=True)
        num = (x * y).sum(dim=0)
        den = x.norm(dim=0) * y.norm(dim=0) + 1e-9
        return (num / den).mean().item()

    arm_contra = corr(SHO[:, :, 0], HIPS[:, :, 1])    # 左肩 vs 右股
    arm_ipsi = corr(SHO[:, :, 0], HIPS[:, :, 0])      # 左肩 vs 左股
    sho_range = ((SHO.amax(dim=0) - SHO.amin(dim=0)) * 180 / math.pi).mean().item()

    # 遊脚中の足の持ち上げ量を**直接**測る。膝角からの推論では誤る:
    # 膝が伸びたままでも股関節主導で足は上がりうる。報酬 foot_clearance は
    # (clearance - 0.10)^2 を罰する形なので、ここが 10cm 近ければその項は
    # ほぼ 0 になり、実際 v44 の報酬内訳で 26位以下(|寄与|<0.0006)だった。
    swing_c = ~C
    clr_swing = CLR[swing_c]
    clr_peak = (CLR * swing_c.float()).amax(dim=0).mean().item()

    pitch_deg = PITCH * 180.0 / math.pi
    pitch_mean = pitch_deg.mean().item()
    pitch_range = (pitch_deg.amax(dim=0) - pitch_deg.amin(dim=0)).mean().item()

    lbl = a.label or f"{a.ckpt.split('/')[-1]} @ cmd {a.cmd_vx}"
    print(f"\n===== {lbl} =====")
    print(f"地形 {a.terrain} / 指令 {a.cmd_vx:.4f} m/s / {a.seconds:.0f}s / "
          f"転倒せず完走 {n_keep}/{a.n_envs} env")
    print(f"脚長(股関節高さ) {leg_len:.3f} m  [立位: 股 {leg_len + _T.FLOOR_TOP:+.3f} / "
          f"足 {foot_z_rest:+.3f} / 床 {_T.FLOOR_TOP:+.3f}]")
    print(f"{'指標':22s} {'実測':>12s}   {'人間の基準':<34s}")
    print(f"{'-'*22} {'-'*12}   {'-'*34}")
    print(f"{'飛翔期率':22s} {flight:11.1f}%   {HUMAN['flight_pct'][1]}")
    print(f"{'両脚支持率':22s} {dbl:11.1f}%   {HUMAN['double_pct'][1]}")
    print(f"{'単脚支持率':22s} {sgl:11.1f}%   約80%")
    print(f"{'片脚あたり接地率':22s} {stance:11.1f}%   {HUMAN['stance_swing'][1]}")
    print(f"{'歩行周期(debounce)':22s} {period:11.3f}s   -")
    print(f"{'歩行周期(生値)':22s} {period_raw:11.3f}s   生値<<debounceなら接地チャタリング")
    print(f"{'ケイデンス':22s} {cadence:9.0f}歩/分   約110歩/分")
    print(f"{'前進速度':22s} {vx:9.3f}m/s   -")
    print(f"{'歩幅':22s} {stride:9.3f}m    -")
    print(f"{'歩幅/脚長':22s} {stride/leg_len:11.2f}    {HUMAN['stride_per_leg'][1]}")
    print(f"{'フルード数 Fr':22s} {fr:11.4f}    {HUMAN['froude'][1]}")
    print(f"{'膝の可動範囲':22s} {kn_range:10.1f}°    遊脚ピーク60〜65°を含む振れ")
    print(f"{'膝角(遊脚中,|平均|)':22s} {kn_swing.mean().item():10.1f}°    {HUMAN['knee_swing_deg'][1]}")
    print(f"{'膝角(立脚中,|平均|)':22s} {kn_stance.mean().item():10.1f}°    {HUMAN['knee_stance_deg'][1]}")
    print(f"{'足クリアランス(遊脚平均)':22s} {clr_swing.mean().item()*100:9.1f}cm   目標10cm(人間8〜12cm)")
    print(f"{'足クリアランス(遊脚ピーク)':22s} {clr_peak*100:9.1f}cm   -")
    print(f"{'腕振り範囲':22s} {sho_range:10.1f}°    -")
    print(f"{'腕-対側脚 相関':22s} {arm_contra:11.2f}    正なら人間と同じ対側同位相")
    print(f"{'腕-同側脚 相関':22s} {arm_ipsi:11.2f}    負であるべき(対側の裏返し)")
    print(f"{'胴体ピッチ 平均':22s} {pitch_mean:10.1f}°    ほぼ0")
    print(f"{'胴体ピッチ 振れ幅':22s} {pitch_range:10.1f}°    {HUMAN['trunk_pitch_deg'][1]}")


if __name__ == "__main__":
    main()
