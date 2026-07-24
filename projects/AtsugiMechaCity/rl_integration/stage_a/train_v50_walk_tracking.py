# -*- coding: utf-8 -*-
"""Stage A: V50 walk tracking on Genesis GPU (self-contained PPO).

Goal (bd 1wr / decision doc Stage A): produce a physically-valid walk with real
forward travel, replacing the near-zero-amplitude sin reference. The reference
JSON (v50_ref_motion.json) was found broken (root travel 0.0, hip amplitude
~0.5 deg), so this trainer generates its own analytic sin-gait reference with
the amplitudes the Blender preview actually uses (hip 11deg / knee 10deg /
ankle 5deg) plus a forward-velocity target of 0.8 m/s (v50_amp_config.yaml).

Design notes:
- Self-contained PPO (no rsl-rl) to avoid library API drift; single file so a
  local model can maintain it (API-fuel rule 2).
- Genesis API verified by C:\\v50_work\\genesis_api_probe.py on genesis 1.2.1.
- Residual action space: PD target = reference pose + 0.35 * action.

Run (venv: C:\\v50_work\\genesis_venv):
  python train_v50_walk_tracking.py --iterations 60 --n-envs 256 --out C:\\v50_work\\stage_a_smoke
"""
import argparse, json, math, os, re, time
import torch
import torch.nn as nn

MJCF_SRC = r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\artifacts\v50_mecha.xml"
# B-1: 12 sagittal DOFs + 4 roll DOFs appended at the END (canonical append-only
# rule). Roll joints are injected into the MJCF at load (see Env XML rewrite).
DOF_NAMES = ["hip_L","knee_L","ankle_L","hip_R","knee_R","ankle_R",
             "shoulder_L","elbow_L","wrist_L","shoulder_R","elbow_R","wrist_R",
             "hip_L_roll","ankle_L_roll","hip_R_roll","ankle_R_roll"]
N_SAGITTAL = 12
# PD gains per DOF (v50_amp_config.yaml). MJCF <actuator> is stripped at load:
# Genesis imports MJCF position actuators as non-PD-reducible act_gain/act_bias that
# FIGHT control_dofs_position (probe finding, 2026-07-03); explicit kp/kv instead.
KP = [400., 300., 200., 400., 300., 200., 200., 150., 80., 200., 150., 80.,
      400., 200., 400., 200.]
KV = [40., 30., 20., 40., 30., 20., 20., 15., 8., 20., 15., 8.,
      40., 20., 40., 20.]
DT_SIM = 0.002
DECIMATION = 10         # control at 50 Hz
# run3 (INC-141): 0.8 m/s was kinematically unreachable for the 11-deg sin gait
# (stride-limited max ~0.24 m/s) -> the travel reward died within 2 s and the
# policy settled into marching in place (run1, run2). Curriculum: reachable
# target with a longer/faster stride first; raise speed later.
GAIT_PERIOD = 1.2       # seconds per gait cycle
TARGET_VX = 0.25        # m/s forward along FWD_AXIS
# INC-141 trap #6 (user caught it): hips are separated along X => X is the
# LATERAL axis and sagittal hip swing (about X) moves the legs in the Y-Z plane,
# so walking direction is +Y. Runs 1-4 rewarded velocity along X (sideways).
# The exporter also put the TOES along +X (sideways feet); the XML rewrite in
# Env.__init__ rotates foot geoms to point +Y.
FWD_AXIS = 1            # 0=x, 1=y
# Dev probe: the gait naturally propels at -0.5..-1.0 m/s along -Y, and the
# Blender V50 also faces -Y (front camera sits at -Y). Forward = -Y.
FWD_SIGN = -1.0
ACTION_SCALE = 0.35
# 2026-07-22 姿勢アンチ前傾(.bak_posture_20260722): dive_hack対策→freeze対策の次段。
# 残存失敗=「前傾ランジで1.7-1.85m歩くが4-6秒で転倒」。Genesis公式Go2例にある
# base_height/lin_vel_z 罰則がこの実装に欠けていた。過度な傾き/胴体沈み/上下動のみを
# デッドバンド付きで罰則化(自然な歩容・良い静止は無罰=freeze再誘発しない)。
TILT_DEADBAND = 0.07   # grav_x^2+grav_y^2(≈sin^2傾き)。約15degまで無罰、超過分のみ罰則
W_TILT = 1.0           # 過度な傾き(前傾/横倒れ)罰則の重み
HEIGHT_DEADBAND = 0.08 # 胴体がstand_zからこの[m]以上沈んだ分のみ罰則
W_LOW = 20.0           # 胴体沈み罰則の重み
W_VZ = 0.5             # 鉛直速度(上下動/ダイブ)罰則の重み
EP_LEN = 400            # 8 s
OBS_DIM = 46          # B-1: +8 (4 roll pose-err + 4 roll vel)
ACT_DIM = 16          # B-1: +4 roll DOFs


# ---- U6: 地形生成(spec: skill_pipeline_implementation_spec.md) ----
TERRAIN_STAIR_H = 0.10      # 段高(人間比0.17より低いカリキュラム開始点)
TERRAIN_STAIR_D = 0.30      # 段奥行
TERRAIN_SLOPE_DEG = 8.0
TERRAIN_FLAT_RUNUP = 0.6    # 平地助走(m)。前方=-Y
# 斜面板の寸法。terrain_xml と terrain_dz の両方がこれを使う(二重管理禁止:
# 片方だけ変えると地面の実高さと期待高さが静かにズレる → 下記T067補注)。
TERRAIN_SLOPE_HALF = 1.5    # 斜面板の半長(斜面に沿った長さの半分)
TERRAIN_SLOPE_THICK = 0.05  # 斜面板の半厚。ロボットは板の「上面」に立つ


# --- (a)質量再配分 2026-07-10 ユーザー承認 (HANDOVER_QUEUE5 §4.6 処方a) ---
# 実測47%トップヘビー(torso 112/238kg)が fall-and-crawl の根本原因仮説。
# シム専用: torso x0.7 / 脚系 x1.4 → 総質量238.0kg厳密保存・胴比33%へ(重心低下)。
# diaginertia も同倍率(同一形状仮定 I∝m)。正解基準XML(artifacts/)は不変更。
# 不足なら次段 0.6/1.6 を人間承認のうえ適用。報酬・ゲートは一切変更しない。
MASS_REDIST = {
    "torso": 0.7,
    "upper_leg_L": 1.4, "lower_leg_L": 1.4, "foot_L": 1.4,
    "upper_leg_R": 1.4, "lower_leg_R": 1.4, "foot_R": 1.4,
}


def apply_mass_redistribution(xml: str) -> str:
    """body毎のinertial mass/diaginertiaをMASS_REDIST倍率でスケール(純関数)。"""
    def _redist(m):
        blk = m.group(0)
        f = MASS_REDIST.get(m.group(1))
        if not f:
            return blk
        def _scale(mm):
            vals = " ".join(str(round(float(v) * f, 6)) for v in mm.group(2).split())
            return f'{mm.group(1)}"{vals}"'
        blk = re.sub(r'(mass=)"([^"]+)"', _scale, blk, count=1)
        blk = re.sub(r'(diaginertia=)"([^"]+)"', _scale, blk, count=1)
        return blk
    return re.sub(r'<body name="([^"]+)"[^>]*>\s*<inertial[^/]*/>', _redist, xml)


TERRAIN_STAIR_N = 10        # 段数(昇降とも)
FLOOR_TOP = -0.92           # 床plane天面z(モデル固有)


def terrain_xml(terrain, stair_h=None):
    """worldbodyに挿入する地形geom文字列。noneは空。

    stair_h: 段高の実行時上書き(段高カリキュラム用)。None=既定 TERRAIN_STAIR_H。
    stairs_down: 昇りと違い床plane(無限)より下へは掘れないので、助走+スポーンを
      h*N だけ持ち上げた台の上から始め、そこから床まで降りる(env が spawn を
      terrain_dz(0) 分だけ持ち上げる。二重管理禁止=高さの真は terrain_dz)。"""
    import math as _m
    if terrain in (None, "", "none"):
        return ""
    h = TERRAIN_STAIR_H if stair_h is None else stair_h
    d = TERRAIN_STAIR_D
    N = TERRAIN_STAIR_N
    g = []
    if terrain == "stairs":
        for i in range(N):
            yc = -(TERRAIN_FLAT_RUNUP + d * i + d / 2)
            zc = FLOOR_TOP + h * (i + 0.5)
            g.append(f'<geom name="stair_{i}" type="box" size="0.8 {d/2:.3f} {h/2:.3f}" '
                     f'pos="0 {yc:.3f} {zc:.3f}" friction="1.2 0.01 0.001"/>')
        top_y = -(TERRAIN_FLAT_RUNUP + d * N + 1.0)
        g.append(f'<geom name="stair_top" type="box" size="0.8 1.0 {h*N/2:.3f}" '
                 f'pos="0 {top_y:.3f} {FLOOR_TOP + h*N/2:.3f}" friction="1.2 0.01 0.001"/>')
    elif terrain == "stairs_down":
        top = FLOOR_TOP + h * N              # 上段台(スポーン+助走)の天面
        # 上段台: 助走域を覆う厚い箱(天面=top)。前方=-Y、助走は 0..-runup。
        plat_far, plat_near = 2.0, -TERRAIN_FLAT_RUNUP
        plat_hy = (plat_far - plat_near) / 2
        plat_yc = (plat_far + plat_near) / 2
        g.append(f'<geom name="stair_plat" type="box" size="0.8 {plat_hy:.3f} 1.0" '
                 f'pos="0 {plat_yc:.3f} {top - 1.0:.3f}" friction="1.2 0.01 0.001"/>')
        for i in range(N):
            yc = -(TERRAIN_FLAT_RUNUP + d * i + d / 2)
            top_face = top - h * (i + 1)      # 段0=top-h, 段N-1=床
            g.append(f'<geom name="stair_d_{i}" type="box" size="0.8 {d/2:.3f} {h/2:.3f}" '
                     f'pos="0 {yc:.3f} {top_face - h/2:.3f}" friction="1.2 0.01 0.001"/>')
        bot_y = -(TERRAIN_FLAT_RUNUP + d * N + 1.0)
        g.append(f'<geom name="stair_bot" type="box" size="0.8 1.0 0.05" '
                 f'pos="0 {bot_y:.3f} {FLOOR_TOP - 0.05:.3f}" friction="1.2 0.01 0.001"/>')
    elif terrain in ("slope_up", "slope_down"):
        th = _m.radians(TERRAIN_SLOPE_DEG)
        half = TERRAIN_SLOPE_HALF
        sign = 1.0 if terrain == "slope_up" else -1.0
        yc = -(TERRAIN_FLAT_RUNUP + half * _m.cos(th))
        zc = -0.92 + sign * half * _m.sin(th)
        g.append(f'<geom name="slope" type="box" size="0.8 {half} {TERRAIN_SLOPE_THICK}" '
                 f'pos="0 {yc:.3f} {zc:.3f}" euler="{-sign * TERRAIN_SLOPE_DEG} 0 0" '
                 f'friction="1.2 0.01 0.001"/>')
    else:
        raise ValueError(f"unknown terrain: {terrain}")
    return "".join(g)


def terrain_dz(y, terrain, stair_h=None):
    """前方位置y(tensor)における期待地面上昇量(床天面 -0.92 基準)。転倒判定と
    base_height 報酬・height-scan の唯一の高さ源。stair_h で段高を上書き可。

    2026-07-24 T067補注 — 実ジオメトリとの解析照合で2つの系統誤差を修正:
      ①階段の1段ズレ: 旧 `floor(prog/D)*H` は段0の上に立っている間 dz=0 を返して
        いたが、段0の天面は既に床から H だけ高い。36点中30点で 0.100m ちょうど
        過小報告していた。正しくは `floor(prog/D)+1` 段ぶん。
      ②斜面板厚の無視: 旧式は板の「中心線」高さを返していたが、ロボットが立つのは
        「上面」で、これは中心線より thick/cos(θ)=0.051m 高い。全点で 0.051m 過小。
    影響: expect_z が低く出るため転倒判定が鈍るだけでなく、base_height 報酬が
    「正しく段上に立っている姿勢」を"高すぎる"と減点し、**登坂そのものを罰して**
    いた。地形学習を始める前に必ず直す必要があった。
    """
    import math as _m
    if terrain in (None, "", "none"):
        return torch.zeros_like(y)
    h = TERRAIN_STAIR_H if stair_h is None else stair_h
    N = TERRAIN_STAIR_N
    prog = (-y - TERRAIN_FLAT_RUNUP).clamp(min=0.0)
    on_terrain = (prog > 0).to(y.dtype)          # 平地助走の上では常に0
    if terrain == "stairs":
        # 段i の上 = 床から H*(i+1)。天面高なので +1 段。
        # clamp は最上段(=stair_top の踊り場 h*N)と一致する。
        steps = ((prog / TERRAIN_STAIR_D).floor() + 1.0).clamp(0, N)
        return on_terrain * steps * h
    if terrain == "stairs_down":
        # 助走(上段台)は一律 h*N。そこから段ごとに h ずつ床(0)まで降りる。
        step = (prog / TERRAIN_STAIR_D).floor().clamp(0, N - 1)
        descended = torch.where(on_terrain.bool(), (step + 1.0) * h, torch.zeros_like(y))
        return (h * N - descended).clamp(min=0.0)
    th = _m.radians(TERRAIN_SLOPE_DEG)
    sign = 1.0 if terrain == "slope_up" else -1.0
    # 斜面の水平方向の実効長(板長×cosθ)。板を越えた先は外挿しない。
    span = 2.0 * TERRAIN_SLOPE_HALF * _m.cos(th)
    rise = sign * _m.tan(th) * prog.clamp(max=span)
    return on_terrain * (rise + TERRAIN_SLOPE_THICK / _m.cos(th))


# Stage B: retargeted real-mocap reference (set via load_reference / --ref-json).
# None のときは従来の解析sin歩容にフォールバック。
REF_TABLE = None            # torch (P,12) on cuda, lazily converted
_REF_TABLE_NP = None


def load_reference(path):
    """bvh_retarget.py が出力した参照JSONを読み、周期・目標速度・テーブルを差し替える。"""
    global _REF_TABLE_NP, GAIT_PERIOD, TARGET_VX
    import json as _json
    d = _json.load(open(path, encoding="utf-8"))
    # 参照は矢状面12DOF。roll4DOFはゼロパディング(_pad_rolls)される。
    assert d["dof_order"] == DOF_NAMES[:N_SAGITTAL], "DOF order mismatch with retargeted reference"
    import numpy as _np
    _REF_TABLE_NP = _np.array(d["frames"], dtype=_np.float32)
    GAIT_PERIOD = float(d["period_sec"])
    TARGET_VX = min(float(d["clip_vx_mps"]), 0.6)   # 安定側にキャップ
    print(f"REF loaded: {path} period={GAIT_PERIOD}s target_vx={TARGET_VX} "
          f"samples={_REF_TABLE_NP.shape[0]}", flush=True)


def gait_reference(phase):
    """phase (N,) in [0,1) -> reference joint targets (N,12) in radians.
    REF_TABLE があれば実モーション参照を線形補間、無ければ解析sin歩容。"""
    global REF_TABLE
    if _REF_TABLE_NP is not None:
        if REF_TABLE is None:
            REF_TABLE = torch.tensor(_REF_TABLE_NP, device=phase.device)
        n = REF_TABLE.shape[0]
        x = phase * n
        i0 = x.long() % n
        i1 = (i0 + 1) % n
        w = (x - x.floor()).unsqueeze(1)
        sag = REF_TABLE[i0] * (1 - w) + REF_TABLE[i1] * w   # (N,12)
        return _pad_rolls(sag)
    return _pad_rolls(_sin_gait(phase))


def _pad_rolls(sag):
    """(N,12)矢状面参照の末尾にroll 4DOFのゼロ(直立中立)を付ける。
    rollの使い方(バランス)は参照ではなくRLが発見する。"""
    return torch.cat([sag, torch.zeros(sag.shape[0], len(DOF_NAMES) - N_SAGITTAL,
                                       device=sag.device)], dim=1)


def _sin_gait(phase):
    """従来の解析sin歩容(Stage Aフォールバック)。
    Amplitudes mirror v50_final_walk_preview.py + arm counterswing."""
    two_pi = 2.0 * math.pi
    s = torch.sin(phase * two_pi)
    hip_l = 0.30 * s                                 # 17 deg (run3: longer stride)
    hip_r = -0.30 * s
    knee_l = 0.26 * torch.clamp(-s, min=0.0)         # 15 deg, stance-flex
    knee_r = 0.26 * torch.clamp(s, min=0.0)
    ank_l = -0.12 * torch.clamp(-s, min=0.0)         # 7 deg
    ank_r = -0.12 * torch.clamp(s, min=0.0)
    sh_l = -0.18 * s                                 # counter-phase arm swing
    sh_r = 0.18 * s
    elb = torch.full_like(s, -0.15)                  # slight constant elbow bend
    wr = torch.zeros_like(s)
    return torch.stack([hip_l, knee_l, ank_l, hip_r, knee_r, ank_r,
                        sh_l, elb, wr, sh_r, elb, wr], dim=1)


def quat_angvel(q, q_prev, dt):
    """Approximate world-frame angular velocity from consecutive quats (wxyz)."""
    # r = q * conj(q_prev); omega ~= 2 * r.xyz / dt  (small-angle)
    w1, x1, y1, z1 = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    w2, x2, y2, z2 = q_prev[:, 0], -q_prev[:, 1], -q_prev[:, 2], -q_prev[:, 3]
    rw = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    rx = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    ry = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    rz = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    sign = torch.where(rw < 0, -1.0, 1.0).unsqueeze(1)
    return sign * 2.0 * torch.stack([rx, ry, rz], dim=1) / dt


def quat_gravity(quat):
    """(N,4) wxyz -> gravity direction in body frame (N,3); upright => (0,0,-1)."""
    w, x, y, z = quat[:, 0], quat[:, 1], quat[:, 2], quat[:, 3]
    # R^T @ [0,0,-1] = third row of R negated per column -> compute directly
    gx = -(2 * (x * z - w * y))
    gy = -(2 * (y * z + w * x))
    gz = -(1 - 2 * (x * x + y * y))
    return torch.stack([gx, gy, gz], dim=1)


def build_model_xml(terrain="none", stair_h=None):
    """V50 MJCF -> 学習/評価共通のシムモデルXML。
    **唯一の正**: render_walk.py も必ずこれを使う。二重管理禁止
    (INC-141 罠#8: レンダー側の複製XMLがB-1のroll注入を持たず、レンダーチェックが
    静かに失敗→フォールバックのfell=true固定で習得判定が構造的に不可能になっていた)。
    含む処理: actuator除去(罠#1) / 足を前方向き+かかと(罠#6) / 接地面を四角形化(v3) /
    hip・ankle roll注入(B-1) / 地形(U6)。"""
    xml = open(MJCF_SRC, encoding="utf-8").read()
    xml = apply_mass_redistribution(xml)  # (a)質量再配分 2026-07-10
    xml = re.sub(r"<actuator>.*?</actuator>", "", xml, flags=re.S)
    xml = xml.replace('fromto="0 0 0 0.15 0 -0.05"',
                      'fromto="0 0.06 -0.05 0 -0.15 -0.05"')
    xml = xml.replace('pos="0.15 0 -0.08"', 'pos="0 -0.15 -0.08"')
    xml = re.sub(r'(<geom name="foot_(L|R)_contact"[^>]*/>)',
                 r'\1<geom name="foot_\2_heel" type="sphere" size="0.04" '
                 r'pos="0 0.06 -0.08" condim="6" friction="1.5 0.01 0.001"/>'
                 r'<geom name="foot_\2_out" type="sphere" size="0.04" '
                 r'pos="0.06 -0.045 -0.08" condim="6" friction="1.5 0.01 0.001"/>'
                 r'<geom name="foot_\2_in" type="sphere" size="0.04" '
                 r'pos="-0.06 -0.045 -0.08" condim="6" friction="1.5 0.01 0.001"/>',
                 xml)
    xml = re.sub(r'(<joint name="hip_(L|R)"[^/]*/>)',
                 r'\1<joint name="hip_\2_roll" type="hinge" axis="0 1 0" pos="0 0 0" '
                 r'limited="true" range="-20.0 20.0" damping="5" stiffness="0"/>', xml)
    xml = re.sub(r'(<joint name="ankle_(L|R)"[^/]*/>)',
                 r'\1<joint name="ankle_\2_roll" type="hinge" axis="0 1 0" pos="0 0 0" '
                 r'limited="true" range="-15.0 15.0" damping="3" stiffness="0"/>', xml)
    xml = xml.replace("</worldbody>", terrain_xml(terrain, stair_h) + "</worldbody>")
    return xml


class Env:
    def __init__(self, n_envs, out_dir, terrain="none"):
        import genesis as gs
        self.gs = gs
        self.terrain = terrain
        noact = os.path.join(out_dir, "v50_mecha_noact.xml")
        with open(noact, "w", encoding="utf-8") as f:
            f.write(build_model_xml(terrain))
        gs.init(backend=gs.gpu, logging_level="warning")
        self.scene = gs.Scene(show_viewer=False,
                              sim_options=gs.options.SimOptions(dt=DT_SIM, substeps=2))
        self.robot = self.scene.add_entity(gs.morphs.MJCF(file=noact))
        self.scene.build(n_envs=n_envs)
        self.n = n_envs
        self.dof_idx = [self.robot.get_joint(nm).dof_idx_local for nm in DOF_NAMES]
        dev = "cuda"
        self.robot.set_dofs_kp(torch.tensor(KP, device=dev), self.dof_idx)
        self.robot.set_dofs_kv(torch.tensor(KV, device=dev), self.dof_idx)
        self.qpos0 = self.robot.get_qpos().clone()          # native spawn (N,19)
        # settle to find true standing height (contact equilibrium)
        for _ in range(300):
            self.scene.step()
        self.stand_z = float(self.robot.get_qpos()[:, 2].mean())
        self.phase = torch.rand(n_envs, device=dev)
        self.steps = torch.zeros(n_envs, device=dev, dtype=torch.long)
        self.x0 = torch.zeros(n_envs, device=dev)           # root x at episode start
        # INC-141 trap #4: get_vel()/get_ang() (and links_vel) return zeros for this
        # MJCF articulated entity in genesis 1.2.1 — all three runs trained with a
        # blind/zero velocity signal. Velocities are now finite-differenced from
        # get_qpos() (the only getter verified to report true world state).
        self.lin_vel = torch.zeros(n_envs, 3, device=dev)
        self.ang_vel = torch.zeros(n_envs, 3, device=dev)
        self.prev_pos = torch.zeros(n_envs, 3, device=dev)
        self.prev_quat = torch.zeros(n_envs, 4, device=dev)
        self.reset(torch.arange(n_envs, device=dev))

    def reset(self, idx):
        if idx.numel() == 0:
            return
        self.robot.set_qpos(self.qpos0[idx], envs_idx=idx, zero_velocity=True)
        self.phase[idx] = torch.rand(idx.numel(), device="cuda")
        ref = gait_reference(self.phase[idx])
        self.robot.set_dofs_position(ref, dofs_idx_local=self.dof_idx, envs_idx=idx,
                                     zero_velocity=True)
        self.steps[idx] = 0
        qpos = self.robot.get_qpos()
        self.x0[idx] = FWD_SIGN * qpos[idx, FWD_AXIS]
        self.prev_pos[idx] = qpos[idx, :3]
        self.prev_quat[idx] = qpos[idx, 3:7]
        self.lin_vel[idx] = 0.0
        self.ang_vel[idx] = 0.0

    def root_state(self):
        qpos = self.robot.get_qpos()
        return qpos[:, :3], qpos[:, 3:7]                    # world pos, quat (wxyz)

    def obs(self):
        q = self.robot.get_dofs_position(self.dof_idx)
        qd = self.robot.get_dofs_velocity(self.dof_idx)
        pos, quat = self.root_state()
        vel = self.lin_vel
        ang = self.ang_vel
        grav = quat_gravity(quat)
        ref = gait_reference(self.phase)
        two_pi = 2.0 * math.pi
        dt_ctrl = DT_SIM * DECIMATION
        x_err = (FWD_SIGN * pos[:, FWD_AXIS] - (self.x0 + self.steps.float() * dt_ctrl * TARGET_VX))
        return torch.cat([
            q - ref,                       # 12 pose error
            qd * 0.05,                     # 12
            (pos[:, 2:3] - self.stand_z),  # 1
            vel * 0.25,                    # 3
            ang * 0.25,                    # 3
            grav,                          # 3
            torch.sin(self.phase * two_pi).unsqueeze(1),
            torch.cos(self.phase * two_pi).unsqueeze(1),
            (x_err * 0.5).clamp(-2, 2).unsqueeze(1),  # forward-progress error
            torch.zeros(self.n, 1, device="cuda"),    # reserved (skill embed slot)
        ], dim=1)

    def step(self, action):
        ref = gait_reference(self.phase)
        target = ref + ACTION_SCALE * torch.tanh(action)
        self.robot.control_dofs_position(target, self.dof_idx)
        for _ in range(DECIMATION):
            self.scene.step()
        self.phase = (self.phase + DT_SIM * DECIMATION / GAIT_PERIOD) % 1.0
        self.steps += 1

        q = self.robot.get_dofs_position(self.dof_idx)
        pos, quat = self.root_state()
        dt_c = DT_SIM * DECIMATION
        self.lin_vel = (pos - self.prev_pos) / dt_c
        self.ang_vel = quat_angvel(quat, self.prev_quat, dt_c)
        self.prev_pos = pos.clone()
        self.prev_quat = quat.clone()
        vel = self.lin_vel
        ang = self.ang_vel
        grav = quat_gravity(quat)

        pose_err = ((q - ref) ** 2).mean(dim=1)
        r_pose = torch.exp(-8.0 * pose_err)
        # INC-141 follow-up: exp velocity reward let the policy settle into
        # marching-in-place (vx=0 local optimum, run1). Linear velocity reward has
        # a clear forward gradient at vx=0, and root-position tracking (DeepMimic
        # convention) pays continuously for actual travel.
        upright = (-grav[:, 2]).clamp(0.0, 1.0)          # 1 when upright
        # trap #7 (reward hacking, run7 visual check): ungated velocity reward let
        # the policy dive forward and CRAWL for speed. Velocity/travel only pay
        # while upright (x upright^2), and falling costs more (-5, tighter tilt cut).
        # 2026-07-19 walk_cycle01 dive_hack再発 (supervisor escalation: "reward
        # gating may be insufficient"): upright**2 は前傾ダイブ中(upright~0.7)でも
        # ~0.5の部分報酬を残し、初速ダイブ+滑走で travel を稼げてしまう。
        # ハードゲート化: upright>0.85 からのみ立ち上がり、0.85未満は速度/前進
        # 報酬ゼロ。姿勢報酬(r_pose)・直立報酬(r_up)は連続のまま維持。
        gate = ((upright - 0.85) / 0.15).clamp(0.0, 1.0) ** 2
        # run10: plateau-shaped velocity reward peaking AT the target pace.
        # History: linear->sprint 0.4 & fall at 2s (run8); hard cap->freeze at
        # 0.05 (run9). A peak at 0.25 penalizes both idling and overspeed while
        # keeping a dense gradient from either side.
        fwd_v = FWD_SIGN * vel[:, FWD_AXIS]
        r_vel = torch.exp(-10.0 * (fwd_v - TARGET_VX) ** 2) * gate
        dt_ctrl = DT_SIM * DECIMATION
        x_expect = self.x0 + self.steps.float() * dt_ctrl * TARGET_VX
        r_travel = torch.exp(-2.0 * (FWD_SIGN * pos[:, FWD_AXIS] - x_expect) ** 2) * gate
        r_up = upright
        # 2026-07-21 anti-freeze(.bak_antifreeze_20260721): dive_hack対策の強ゲート+転倒-10で
        # 今度は「立ち止まれば安全に稼げる」freeze局所解に収束(7/21: fell=false・upright0.94・
        # travel0.6→0.2mへregression)。exp系のr_vel/r_travelは静止時に勾配が弱く/消える一方、
        # 定数0.25+0.5*r_upが静止の無償収入(~0.725/step)を保証していた。対策:
        #  ①静止の無償収入を削減(定数0.25→0.1, r_up重み0.5→0.3)
        #  ②線形の前進報酬 r_prog を追加: 前進速度に比例(0..目標で0..1)、静止=0。
        #     upright>0.85ゲート共有=ダイブ(upright<0.85)には出ない→dive再誘発しない。
        r_prog = gate * (fwd_v.clamp(min=0.0, max=TARGET_VX) / TARGET_VX)
        pen_act = (action ** 2).mean(dim=1)
        pen_ang = (ang ** 2).sum(dim=1)
        # 2026-07-22 姿勢アンチ前傾: デッドバンド付きで「過度な傾き/沈み/上下動」のみ罰則。
        # 自然な歩行(小さな傾き・一定高・小さな上下動)は各penがゼロ→前進報酬r_progを損なわない。
        # 前傾転倒(大傾き+沈み+下向き速度)でのみ強く効く=freezeへ退行させずに直立歩行へ誘導。
        pen_tilt = (grav[:, 0] ** 2 + grav[:, 1] ** 2 - TILT_DEADBAND).clamp(min=0.0)
        pen_low = (self.stand_z - pos[:, 2] - HEIGHT_DEADBAND).clamp(min=0.0) ** 2
        pen_vz = vel[:, 2] ** 2
        reward = 0.8 * r_pose + 1.5 * r_vel + 1.0 * r_travel + 0.8 * r_prog + 0.3 * r_up + 0.1 \
                 - 0.01 * pen_act - 0.02 * pen_ang \
                 - W_TILT * pen_tilt - W_LOW * pen_low - W_VZ * pen_vz

        expected_z = self.stand_z + terrain_dz(pos[:, FWD_AXIS], self.terrain)
        # 2026-07-19 dive_hack対策: 転倒カット 0.65→0.75(ダイブ軌道の早期打切り)、
        # ペナルティ -5→-10(初速ダイブの割引報酬合計を確実に負にする)。
        fallen = (pos[:, 2] < expected_z - 0.25) | (upright < 0.75)
        timeout = self.steps >= EP_LEN
        done = fallen | timeout
        reward = torch.where(fallen, reward - 10.0, reward)

        idx = torch.nonzero(done).squeeze(-1)
        metrics = {"vx": (FWD_SIGN * vel[:, FWD_AXIS]).mean().item(), "up": upright.mean().item(),
                   "pose_err": pose_err.mean().item(), "falls": fallen.float().sum().item()}
        self.reset(idx)
        return self.obs(), reward, done, metrics


class ActorCritic(nn.Module):
    def __init__(self):
        super().__init__()
        def mlp(out):
            return nn.Sequential(nn.Linear(OBS_DIM, 256), nn.ELU(),
                                 nn.Linear(256, 128), nn.ELU(), nn.Linear(128, out))
        self.actor = mlp(ACT_DIM)
        self.critic = mlp(1)
        self.log_std = nn.Parameter(torch.full((ACT_DIM,), -0.7))

    def dist(self, obs):
        return torch.distributions.Normal(self.actor(obs), self.log_std.exp())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=60)
    ap.add_argument("--n-envs", type=int, default=256)
    ap.add_argument("--rollout", type=int, default=32)
    ap.add_argument("--out", default=r"C:\v50_work\stage_a_smoke")
    ap.add_argument("--resume", default=None)
    # run6: anneal exploration so the walk consolidates into the deterministic
    # mean (run5 walked at +0.14 stochastically but +0.02 deterministically —
    # noise-driven propulsion).
    ap.add_argument("--entropy", type=float, default=0.005)
    ap.add_argument("--init-log-std", type=float, default=None)
    # Stage B: retargeted real-mocap reference JSON (bvh_retarget.py output)
    ap.add_argument("--ref-json", default=None)
    # U6: 地形カリキュラム
    ap.add_argument("--terrain", default="none",
                    choices=["none", "stairs", "stairs_down", "slope_up", "slope_down"])
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if args.ref_json:
        load_reference(args.ref_json)

    env = Env(args.n_envs, args.out, args.terrain)
    ac = ActorCritic().cuda()
    if args.resume:
        ac.load_state_dict(torch.load(args.resume, weights_only=True))
    if args.init_log_std is not None:
        with torch.no_grad():
            ac.log_std.fill_(args.init_log_std)
    opt = torch.optim.Adam(ac.parameters(), lr=3e-4)
    obs = env.obs()
    N, T = args.n_envs, args.rollout
    gamma, lam, clip = 0.99, 0.95, 0.2
    best = -1e9
    t_start = time.time()

    for it in range(1, args.iterations + 1):
        buf_obs = torch.zeros(T, N, OBS_DIM, device="cuda")
        buf_act = torch.zeros(T, N, ACT_DIM, device="cuda")
        buf_logp = torch.zeros(T, N, device="cuda")
        buf_rew = torch.zeros(T, N, device="cuda")
        buf_done = torch.zeros(T, N, device="cuda")
        buf_val = torch.zeros(T + 1, N, device="cuda")
        m_acc = {"vx": 0.0, "up": 0.0, "pose_err": 0.0, "falls": 0.0}
        with torch.no_grad():
            for t in range(T):
                dist = ac.dist(obs)
                act = dist.sample()
                buf_obs[t] = obs; buf_act[t] = act
                buf_logp[t] = dist.log_prob(act).sum(-1)
                buf_val[t] = ac.critic(obs).squeeze(-1)
                obs, rew, done, m = env.step(act)
                buf_rew[t] = rew; buf_done[t] = done.float()
                for k in m_acc: m_acc[k] += m[k] / T
            buf_val[T] = ac.critic(obs).squeeze(-1)
            adv = torch.zeros(T, N, device="cuda"); gae = 0
            for t in reversed(range(T)):
                nd = 1.0 - buf_done[t]
                delta = buf_rew[t] + gamma * buf_val[t + 1] * nd - buf_val[t]
                gae = delta + gamma * lam * nd * gae
                adv[t] = gae
            ret = adv + buf_val[:T]
            adv = (adv - adv.mean()) / (adv.std() + 1e-8)

        b_obs = buf_obs.reshape(-1, OBS_DIM); b_act = buf_act.reshape(-1, ACT_DIM)
        b_logp = buf_logp.reshape(-1); b_adv = adv.reshape(-1); b_ret = ret.reshape(-1)
        n_batch = b_obs.shape[0]
        for _ in range(4):
            perm = torch.randperm(n_batch, device="cuda")
            for mb in perm.chunk(4):
                dist = ac.dist(b_obs[mb])
                logp = dist.log_prob(b_act[mb]).sum(-1)
                ratio = (logp - b_logp[mb]).exp()
                s1 = ratio * b_adv[mb]
                s2 = torch.clamp(ratio, 1 - clip, 1 + clip) * b_adv[mb]
                loss_pi = -torch.min(s1, s2).mean()
                loss_v = ((ac.critic(b_obs[mb]).squeeze(-1) - b_ret[mb]) ** 2).mean()
                loss = loss_pi + 0.5 * loss_v - args.entropy * dist.entropy().sum(-1).mean()
                opt.zero_grad(); loss.backward()
                nn.utils.clip_grad_norm_(ac.parameters(), 1.0)
                opt.step()

        mean_rew = buf_rew.mean().item()
        print(f"it {it:4d} | rew/step {mean_rew:6.3f} | vx {m_acc['vx']:5.2f} | "
              f"up {m_acc['up']:4.2f} | pose_err {m_acc['pose_err']:.4f} | falls {m_acc['falls']:.0f}",
              flush=True)
        if mean_rew > best:
            best = mean_rew
            torch.save(ac.state_dict(), os.path.join(args.out, "best.pt"))
        if it % 10 == 0 or it == args.iterations:
            torch.save(ac.state_dict(), os.path.join(args.out, "latest.pt"))
            with open(os.path.join(args.out, "status.json"), "w", encoding="utf-8") as f:
                json.dump({"schema": "clawstack.stage_a_walk_tracking.v1",
                           "iteration": it, "iterations_total": args.iterations,
                           "mean_reward_per_step": round(mean_rew, 4),
                           "best_reward_per_step": round(best, 4),
                           "vx_mean": round(m_acc["vx"], 3), "upright": round(m_acc["up"], 3),
                           "pose_err": round(m_acc["pose_err"], 5),
                           "elapsed_sec": round(time.time() - t_start, 1),
                           "n_envs": N}, f, indent=2)

    # eval: forward travel over 400 control steps (8 s), deterministic AND
    # stochastic (run5 walked only with exploration noise — measure both).
    eval_res = {"target_vx": TARGET_VX,
                "note": "travel is lower bound (env auto-resets on falls)"}
    with torch.no_grad():
        for mode in ("deterministic", "stochastic"):
            env.reset(torch.arange(N, device="cuda"))
            obs_e = env.obs()
            x0 = (FWD_SIGN * env.robot.get_qpos()[:, FWD_AXIS]).clone()
            vx_acc = 0.0
            for _ in range(EP_LEN):
                act = ac.actor(obs_e) if mode == "deterministic" else ac.dist(obs_e).sample()
                obs_e, _, _, m = env.step(act)
                vx_acc += m["vx"] / EP_LEN
            travel = (FWD_SIGN * env.robot.get_qpos()[:, FWD_AXIS] - x0).mean().item()
            eval_res[f"{mode}_travel_m_8s"] = round(travel, 3)
            eval_res[f"{mode}_vx_mean"] = round(vx_acc, 3)
    eval_res["eval_forward_travel_m_8s"] = eval_res["deterministic_travel_m_8s"]
    eval_res["eval_vx_mean"] = eval_res["deterministic_vx_mean"]
    with open(os.path.join(args.out, "eval.json"), "w", encoding="utf-8") as f:
        json.dump(eval_res, f, indent=2)
    print("EVAL:", json.dumps(eval_res))
    print("DONE")


if __name__ == "__main__":
    main()
