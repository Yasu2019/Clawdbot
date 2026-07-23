# -*- coding: utf-8 -*-
"""Stage B: BVH -> V50 12-DOF sagittal reference motion (position-based retarget).

回転チャンネルの規約差(rig依存)を避けるため、BVHをFKでワールド座標に展開し、
セグメントベクトルの矢状面投影から関節角を幾何的に計算する。
出力: ref JSON {phase点×12DOF, 前進速度, 周期} — train_v50_walk_tracking.py が読む。

usage:
  python bvh_retarget.py --bvh <file.bvh> --out ref_walk.json [--phase-samples 64]
"""
import argparse, json, math, re
import numpy as np

# V50 DOF順(train_v50_walk_tracking.DOF_NAMES と一致必須)
DOF_NAMES = ["hip_L","knee_L","ankle_L","hip_R","knee_R","ankle_R",
             "shoulder_L","elbow_L","wrist_L","shoulder_R","elbow_R","wrist_R"]
# V50関節可動域(MJCF実測: probe7)。mocap角はここへクリップされる。
LIMITS = {"hip": (-0.7, 0.7), "knee": (-0.52, 0.17), "ankle": (-0.35, 0.35),
          "shoulder": (-1.75, 1.75), "elbow": (-2.09, 0.17), "wrist": (-0.52, 0.52)}


# ---------- BVH parser + FK ----------
class Joint:
    def __init__(self, name, parent):
        self.name, self.parent = name, parent
        self.offset = np.zeros(3)
        self.channels = []
        self.children = []


def parse_bvh(path):
    toks = re.split(r"\s+", open(path, encoding="utf-8", errors="replace").read().strip())
    i = 0
    joints, stack, root = [], [], None

    def expect(t):
        nonlocal i
        assert toks[i].upper() == t, f"expected {t} got {toks[i]} @{i}"
        i += 1

    expect("HIERARCHY")
    while toks[i].upper() != "MOTION":
        t = toks[i].upper()
        if t in ("ROOT", "JOINT"):
            j = Joint(toks[i + 1], stack[-1] if stack else None)
            if stack:
                stack[-1].children.append(j)
            else:
                root = j
            joints.append(j)
            i += 2
            expect("{")
            stack.append(j)
        elif t == "END":               # End Site
            j = Joint(stack[-1].name + "_end", stack[-1])
            stack[-1].children.append(j)
            joints.append(j)
            i += 2
            expect("{")
            stack.append(j)
        elif t == "OFFSET":
            stack[-1].offset = np.array([float(toks[i + 1]), float(toks[i + 2]), float(toks[i + 3])])
            i += 4
        elif t == "CHANNELS":
            n = int(toks[i + 1])
            stack[-1].channels = [c for c in toks[i + 2:i + 2 + n]]
            i += 2 + n
        elif t == "}":
            stack.pop()
            i += 1
        else:
            raise ValueError(f"unexpected token {toks[i]}")
    expect("MOTION")
    assert toks[i].lower() == "frames:"; i += 1
    n_frames = int(toks[i]); i += 1
    assert toks[i].lower() == "frame" and toks[i + 1].lower() == "time:"; i += 2
    dt = float(toks[i]); i += 1
    vals = np.array([float(v) for v in toks[i:]], dtype=np.float64)
    n_ch = sum(len(j.channels) for j in joints)
    frames = vals[:n_frames * n_ch].reshape(n_frames, n_ch)
    return root, joints, frames, dt


def rot(axis, deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    if axis == "X": return np.array([[1,0,0],[0,c,-s],[0,s,c]])
    if axis == "Y": return np.array([[c,0,s],[0,1,0],[-s,0,c]])
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])


def fk_positions(root, joints, frame_vals, wanted):
    """1フレーム分のFK。wanted名のワールド座標dictを返す。"""
    idx = 0
    ch_index = {}
    for j in joints:
        ch_index[j.name] = (idx, j.channels)
        idx += len(j.channels)
    out = {}

    def walk(j, parent_R, parent_p):
        base, chs = ch_index[j.name]
        p_local = j.offset.copy()
        R = np.eye(3)
        t_extra = np.zeros(3)
        for k, ch in enumerate(chs):
            v = frame_vals[base + k]
            cu = ch.upper()
            if cu.endswith("POSITION"):
                t_extra["XYZ".index(cu[0])] = v
            else:
                R = R @ rot(cu[0], v)
        p_world = parent_p + parent_R @ (p_local + t_extra)
        R_world = parent_R @ R
        if j.name in wanted:
            out[j.name] = p_world
        for c in j.children:
            walk(c, R_world, p_world)

    walk(root, np.eye(3), np.zeros(3))
    return out


# ---------- sagittal angle extraction ----------
def sagittal_angle(vec, fwd, up):
    """セグメントベクトルの矢状面(fwd-up平面)投影角。真下=0、前方倒れ=+。"""
    f = float(np.dot(vec, fwd)); u = float(np.dot(vec, up))
    return math.atan2(f, -u)   # 真下(-up)基準、前方成分で+


def signed_sagittal_between(a_seg, b_seg, fwd, up):
    """矢状面内で a から b への符号付き角度(rad)。atan2(cross,dot) で分岐なし。

    2026-07-24 T067修正: 旧 series_ankle は sagittal_angle(b)-sagittal_angle(a)
    という二つの atan2 の差を取っていたため、各項が独立に ±π へ折り返し、
    足首系列が min -185° まで飛んで DC が -92° になっていた(足首が可動域上限
    +20° に張り付いて凍結)。角度差は必ずこの分岐フリー版で計算する。"""
    out = []
    for a, b in zip(a_seg, b_seg):
        af, au = float(np.dot(a, fwd)), float(np.dot(a, up))
        bf, bu = float(np.dot(b, fwd)), float(np.dot(b, up))
        out.append(math.atan2(af * bu - au * bf, af * bf + au * bu))
    return np.array(out)


def fit_amplitude(x, lo, hi, target_frac=0.8):
    """中央値でセンタリングし、90パーセンタイル振幅が可動域の target_frac に
    収まるよう頑健スケールしてからクリップする(時相を保ちつつ飽和を防ぐ)。

    足首のように生の振幅(この mocap では p2p 178°)が可動域(±20°)を大きく
    超える系列で、rail-to-rail の矩形波化を避けるために使う。"""
    c = x - np.median(x)
    amp = np.percentile(np.abs(c), 90)
    half = min(abs(lo), abs(hi))
    if amp > 1e-6:
        c = c * (target_frac * half / amp)
    return np.clip(c, lo, hi)


def find_joint(joints, *cands):
    names = {j.name.lower(): j.name for j in joints}
    for c in cands:
        for lname, orig in names.items():
            if c.lower() == lname:
                return orig
    for c in cands:  # 部分一致fallback
        for lname, orig in names.items():
            if c.lower() in lname and not lname.endswith("_end"):
                return orig
    raise KeyError(f"joint not found: {cands}; have {sorted(names.values())[:30]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bvh", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--phase-samples", type=int, default=64)
    ap.add_argument("--start-frac", type=float, default=0.3, help="定常区間の開始(クリップ比)")
    args = ap.parse_args()

    root, joints, frames, dt = parse_bvh(args.bvh)
    J = {}
    J["hips"] = find_joint(joints, "Hips")
    J["upleg_l"] = find_joint(joints, "LeftUpLeg", "LeftHip", "L_UpLeg")
    J["leg_l"] = find_joint(joints, "LeftLeg", "LeftKnee", "L_Leg")
    J["foot_l"] = find_joint(joints, "LeftFoot", "LeftAnkle", "L_Foot")
    J["toe_l"] = find_joint(joints, "LeftToe", "LeftToeBase", "LeftFoot_end")
    J["upleg_r"] = find_joint(joints, "RightUpLeg", "RightHip", "R_UpLeg")
    J["leg_r"] = find_joint(joints, "RightLeg", "RightKnee", "R_Leg")
    J["foot_r"] = find_joint(joints, "RightFoot", "RightAnkle", "R_Foot")
    J["toe_r"] = find_joint(joints, "RightToe", "RightToeBase", "RightFoot_end")
    J["arm_l"] = find_joint(joints, "LeftArm", "LeftShoulder", "LeftUpperArm")
    J["forearm_l"] = find_joint(joints, "LeftForeArm", "LeftElbow", "LeftLowerArm")
    J["hand_l"] = find_joint(joints, "LeftHand", "LeftWrist")
    J["arm_r"] = find_joint(joints, "RightArm", "RightShoulder", "RightUpperArm")
    J["forearm_r"] = find_joint(joints, "RightForeArm", "RightElbow", "RightLowerArm")
    J["hand_r"] = find_joint(joints, "RightHand", "RightWrist")
    wanted = set(J.values())

    n = frames.shape[0]
    sel = range(0, n)
    P = {name: np.zeros((n, 3)) for name in wanted}
    for f in sel:
        pos = fk_positions(root, joints, frames[f], wanted)
        for name, p in pos.items():
            P[name][f] = p

    hips = P[J["hips"]]
    # 上方向: BVHはY-up想定(オフセット分散で検証)、前方向: hipsの平均水平速度
    up = np.array([0.0, 1.0, 0.0])
    disp = hips[-1] - hips[0]
    disp[1] = 0.0
    if np.linalg.norm(disp) < 1e-6:
        raise SystemExit("clip has no horizontal travel; pick a forward-walk clip")
    fwd = disp / np.linalg.norm(disp)

    def seg(a, b):
        return P[J[b]] - P[J[a]]

    def series_hip(side):
        return np.array([sagittal_angle(v, fwd, up) for v in seg(f"upleg_{side}", f"leg_{side}")])

    def series_knee(side):
        th = seg(f"upleg_{side}", f"leg_{side}"); sh = seg(f"leg_{side}", f"foot_{side}")
        out = []
        for a, b in zip(th, sh):
            ca = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
            out.append(math.acos(max(-1, min(1, ca))))   # 屈曲角(常に>=0)
        return np.array(out)

    def series_ankle(side):
        # 足の背屈/底屈 = すねベクトルと足ベクトルの矢状面内符号付き角度。
        # 分岐フリー(signed_sagittal_between)で計算し、中立(≈直角)は後段の
        # fit_amplitude が中央値センタリングで自動除去する。
        sh = seg(f"leg_{side}", f"foot_{side}"); ft = seg(f"foot_{side}", f"toe_{side}")
        return signed_sagittal_between(sh, ft, fwd, up)

    def series_shoulder(side):
        return np.array([sagittal_angle(v, fwd, up) for v in seg(f"arm_{side}", f"forearm_{side}")])

    def series_elbow(side):
        ua = seg(f"arm_{side}", f"forearm_{side}"); fa = seg(f"forearm_{side}", f"hand_{side}")
        out = []
        for a, b in zip(ua, fa):
            ca = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
            out.append(math.acos(max(-1, min(1, ca))))
        return np.array(out)

    hip_l, hip_r = series_hip("l"), series_hip("r")
    knee_l, knee_r = series_knee("l"), series_knee("r")
    ank_l, ank_r = series_ankle("l"), series_ankle("r")
    sh_l, sh_r = series_shoulder("l"), series_shoulder("r")
    el_l, el_r = series_elbow("l"), series_elbow("r")

    # 周期検出: 定常区間の hip_l 自己相関ピーク
    s0 = int(n * args.start_frac)
    sig = hip_l[s0:] - hip_l[s0:].mean()
    ac = np.correlate(sig, sig, "full")[len(sig) - 1:]
    min_lag = int(0.6 / dt)                      # 0.6s未満の周期は棄却
    max_lag = min(int(2.5 / dt), len(ac) - 1)
    period = int(min_lag + np.argmax(ac[min_lag:max_lag]))
    cyc = slice(s0, s0 + period)

    # 前進速度(この1周期の実測)
    travel = float(np.dot(hips[cyc.stop - 1] - hips[cyc.start], fwd))
    scale_len = np.linalg.norm(P[J["upleg_l"]][0] - P[J["foot_l"]][0])  # 脚長(単位系検出)
    unit = 0.01 if scale_len > 3.0 else 1.0      # cm系BVHならm換算
    vx = travel * unit / (period * dt)

    # 位相リサンプル + V50符号/可動域へマップ
    #  - V50 hip: 正=脚が+Y(後方)へ。前方(fwd)+の人間角 → 符号反転
    #  - V50 knee (range -30°..+10°): 屈曲の大可動側は「負」。人間の屈曲角(acos,
    #    常に≥0)を正のままクリップすると +10° 上限に張り付き p2p 9° に潰れる
    #    (T067 の膝振幅バグ)。符号反転して -30° 側へ写すと p2p ≈ 29°、遊脚で
    #    足が持ち上がる。屈曲ピークは -30° でフラットトップにクリップ=接地
    #    クリアランスに有利なのでスケールはしない。
    #  - V50 ankle (range ±20°): 生振幅は p2p 178° と可動域を大きく超えるため、
    #    fit_amplitude で中央値センタリング+頑健スケールしてから写す(凍結防止)。
    def resample(x):
        ph = np.linspace(0, period - 1, args.phase_samples)
        return np.interp(ph, np.arange(period), x[cyc])

    def clip(x, key):
        lo, hi = LIMITS[key]
        return np.clip(x, lo, hi)

    def ankle_map(x):
        lo, hi = LIMITS["ankle"]
        return fit_amplitude(resample(x), lo, hi, target_frac=0.75)

    table = np.stack([
        clip(-resample(hip_l), "hip"), clip(-resample(knee_l), "knee"), ankle_map(ank_l),
        clip(-resample(hip_r), "hip"), clip(-resample(knee_r), "knee"), ankle_map(ank_r),
        clip(-resample(sh_l), "shoulder"), clip(-resample(el_l), "elbow"),
        np.zeros(args.phase_samples),
        clip(-resample(sh_r), "shoulder"), clip(-resample(el_r), "elbow"),
        np.zeros(args.phase_samples),
    ], axis=1)

    out = {"schema": "clawstack.v50_ref_motion.retargeted.v1",
           "source_bvh": args.bvh, "license": "CC-BY-4.0 100STYLE (Mason et al. 2022)",
           "dof_order": DOF_NAMES, "phase_samples": args.phase_samples,
           "period_sec": round(period * dt, 4), "clip_vx_mps": round(abs(vx), 4),
           "frames": [[round(float(v), 5) for v in row] for row in table]}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"period_sec": out["period_sec"], "clip_vx": out["clip_vx_mps"],
                      "hip_range": [round(float(table[:, 0].min()), 3), round(float(table[:, 0].max()), 3)],
                      "knee_range": [round(float(table[:, 1].min()), 3), round(float(table[:, 1].max()), 3)],
                      "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
