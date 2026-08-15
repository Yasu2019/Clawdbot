# -*- coding: utf-8 -*-
"""旧 4mm×4mm モデルでの 3D-MPM 打ち抜き評価。2026-08-16 導入。

ユーザー指摘: 新PM7T1C(~15mm角)ドメインでは一様グリッドMPMが接触時に
発散した(scripts/build_panel4mm_mpm.py 参照)。旧 4mmx4mm_ASSY_20260104.inp
はドメインが約1/4なので、同一セル数予算でも dx を約4倍細かくできる
(60um -> 16um相当)。これを実測で検証する。

旧STEP(4mmx4mm_ASSY.step)は部品名が Cut/Cut001.../Unnamed で不明瞭なため、
既に個別工具への分離に成功している INP(要素セット4つ、Punch は連結成分で
個別分離済み)を直接読む。Punch の3形状(丸/四角x2/トリム)は同時に動く
単一ラムなので、MPM の剛体境界としては1つにまとめて扱ってよい
(FEM接触インターフェースの分離とは異なり、剛体運動の表現には不要)。

材料 From_parts-Material (10,183節点) は既に一体のブランクで、
PANEL4MM_P2 のような「抜き後スクラップに分解済み+穴を塞ぐ」処理は不要。

usage:
  python scripts/build_4mm_mpm.py --smoke --smoke-steps 60000 --dx 1.6e-5
  python scripts/build_4mm_mpm.py --run --dx 1.6e-5
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023
sys.path.insert(0, str(Path(__file__).parent))
from build_panel4mm_mpm import PanelMPM, RHO  # noqa: E402

INP = Path(r"C:\Users\yasu\OneDrive\デスクトップ\Panel\4mmx4mm_ASSY_20260104.inp")
ROOT = Path(r"D:\Clawdbot_Docker_20260125")
OUT = ROOT / "data" / "workspace" / "openradioss_inc188_trials" / "mpm_4mm"
OUT.mkdir(parents=True, exist_ok=True)

MM = 1.0e-3
STROKE = 3.0e-3     # m。ユーザー指示のストロークをそのまま踏襲
SPEED = 5.0
T_STOP = STROKE / SPEED
STRIPPER_CLOSE_T = 1.0e-4


def load_inp():
    """旧INPを読み、材料はtet重心粒子、工具はtet重心の剛体ボクセルにする。"""
    nodes = {}
    elsets = {"Solid_part-Stripper": [], "Solid_part-Die": [],
             "From_parts-Material": [], "From_parts-Punch": []}
    cur = None
    with open(INP, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s.startswith("*Node"):
                cur = "NODE"; continue
            if s.upper().startswith("*ELEMENT"):
                name = s.split("Elset=")[1].strip() if "Elset=" in s else None
                cur = ("ELEM", name); continue
            if s.startswith("*"):
                cur = None; continue
            if cur == "NODE":
                p = s.split(",")
                try:
                    nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
                except (ValueError, IndexError):
                    pass
            elif isinstance(cur, tuple) and cur[0] == "ELEM" and cur[1] in elsets:
                p = [x for x in s.split(",") if x.strip() != ""]
                try:
                    elsets[cur[1]].append([int(x) for x in p[1:]])
                except ValueError:
                    pass

    def centroids_vols(elems):
        pts = np.array([[nodes[n] for n in e] for e in elems], dtype=np.float64)
        p0, p1, p2, p3 = pts[:, 0], pts[:, 1], pts[:, 2], pts[:, 3]
        c = (p0 + p1 + p2 + p3) / 4.0
        v = np.abs(np.einsum("ij,ij->i", p1 - p0, np.cross(p2 - p0, p3 - p0))) / 6.0
        return c, v

    blank_c, blank_v = centroids_vols(elsets["From_parts-Material"])
    die_c, _ = centroids_vols(elsets["Solid_part-Die"])
    strip_c, _ = centroids_vols(elsets["Solid_part-Stripper"])
    punch_c, _ = centroids_vols(elsets["From_parts-Punch"])
    print(f"[geom] 材料粒子={len(blank_c):,} 総体積={blank_v.sum():.4f}mm3")
    print(f"[geom] die={len(die_c):,} stripper={len(strip_c):,} punch={len(punch_c):,}")
    return blank_c, blank_v, {"die": die_c, "stripper": strip_c, "punch": punch_c}


def build_domain(blank_c, tools, dx):
    allc = [blank_c] + list(tools.values())
    lo = np.min([c.min(axis=0) for c in allc], axis=0) - 0.3
    hi = np.max([c.max(axis=0) for c in allc], axis=0) + 0.3
    hi[2] += STROKE * 1e3 + 0.3
    n_grid = np.ceil(((hi - lo) * MM) / dx).astype(np.int32) + 1
    return lo, n_grid


def run(smoke: bool, smoke_steps: int, dx: float):
    import taichi as ti
    import time
    ti.init(arch=ti.cuda, default_fp=ti.f32)
    blank_c, blank_v, tools = load_inp()
    origin_mm, n_grid = build_domain(blank_c, tools, dx)
    print(f"[mpm] グリッド {tuple(n_grid)} = {int(np.prod(n_grid)):,} セル "
          f"/ 粒子 {blank_c.shape[0]:,}  dx={dx*1e6:.1f}um")

    # 工具すきまの解像度チェック(参考表示のみ)
    die_top = tools["die"][:, 2].max()
    blank_bot = blank_c[:, 2].min()
    gap_die_mm = blank_bot - die_top
    print(f"[mpm] ダイ上面-材料下面 概算すきま = {gap_die_mm:.4f}mm "
          f"= {gap_die_mm*1e3/dx*1e-3:.2f}セル相当")

    # ストリッパー実すきま(mm)を幾何から直接算出する。新モデルの値(0.19mm)を
    # 誤って流用すると過剰に押し込むバグになる(実測で発覚: t=0.07-0.08msで
    # 爆発、パンチ接触より前=ダイ+ストリッパーの挟み込み過剰が原因だった)。
    strip_gap_mm = tools["stripper"][:, 2].min() - blank_c[:, 2].max()
    print(f"[mpm] ストリッパー実すきま = {strip_gap_mm:.4f}mm(幾何実測、ハードコード値は使わない)")

    sim = PanelMPM(blank_c, blank_v, tools, dx, origin_mm, n_grid)

    E = 69.0e9
    wave_speed = (E / RHO) ** 0.5
    dt = 0.2 * dx / wave_speed
    n_steps = smoke_steps if smoke else int(T_STOP / dt) + 1
    print(f"[mpm] dt={dt:.3e}s  ステップ数={n_steps:,}{'（健全性確認）' if smoke else ''}")

    CONTACT_TRAVEL_GUESS = None  # 旧モデルは接触travel未確立。ソフトスタートは
                                  # substep側でCONTACT_TRAVEL定数を使うが、ここでは
                                  # 汎用的に「パンチZ最小-材料Z最大」からその場で推定する
    punch_bottom0 = tools["punch"][:, 2].min()
    blank_top0 = blank_c[:, 2].max()
    contact_travel = max(punch_bottom0 - blank_top0, 0.0) * MM
    print(f"[mpm] 推定パンチ接触travel = {contact_travel*1e3:.4f}mm")

    t0 = time.time()
    t = 0.0
    dump_every = max(1, n_steps // 40)
    frames = []
    out_npz = OUT / ("smoke.npz" if smoke else "full.npz")

    def save():
        np.savez_compressed(out_npz, origin_mm=origin_mm, dx=dx,
                            steps=[f[0] for f in frames], times=[f[1] for f in frames],
                            x=np.array([f[2] for f in frames]),
                            alive=np.array([f[3] for f in frames]),
                            eps_p=np.array([f[4] for f in frames]))

    strip_gap_m = strip_gap_mm * MM
    for step in range(n_steps):
        punch_disp = min(t * SPEED, STROKE)
        punch_vz = -SPEED if t * SPEED < STROKE else 0.0
        # ストリッパーは smoothstep(始点・終点とも速度0)で駆動する。線形+瞬時停止
        # だと t=STRIPPER_CLOSE_T の瞬間に速度が不連続に0へ落ち、そこが爆発の
        # 起点になっていた(実測: t=0.096-0.101msでv|max 0.03->8.14m/s)。
        # 立ち上がりも滑らかになるので初期の衝撃も同時に緩和される。
        u = min(t / STRIPPER_CLOSE_T, 1.0)
        strip_disp = strip_gap_m * (3 * u**2 - 2 * u**3)
        strip_vz = -strip_gap_m / STRIPPER_CLOSE_T * (6 * u - 6 * u**2) if t < STRIPPER_CLOSE_T else 0.0
        ramp = min(max((punch_disp - contact_travel) / (2 * dx), 0.0), 1.0)
        punch_blend = 0.25 * ramp
        sim.clear_grid()
        sim.p2g(dt)
        sim.grid_update(
            dt, -9.8,
            sim.tool_z0["die"], sim.tool_z1["die"],
            sim.tool_z0["stripper"] - strip_disp, sim.tool_z1["stripper"] - strip_disp, strip_vz,
            sim.tool_z0["punch"] - punch_disp, sim.tool_z1["punch"] - punch_disp, punch_vz,
            punch_blend,
        )
        sim.g2p(dt)
        t += dt
        if step % dump_every == 0 or step == n_steps - 1:
            xs = sim.x.to_numpy()
            eps = sim.eps_p.to_numpy()
            vmax = np.abs(sim.v.to_numpy()).max()
            nan = not np.isfinite(xs).all()
            print(f"[mpm] step={step:>7,} t={t*1e3:6.3f}ms |v|max={vmax:8.2f}m/s "
                  f"eps_p_max={eps.max():.4f} NaN={nan} elapsed={time.time()-t0:7.1f}s",
                  flush=True)
            if nan:
                print("[mpm] !!! NaN 検出。停止。"); break
            frames.append((step, t, xs.copy(), sim.alive.to_numpy().copy(), eps.copy()))
            save()

    print(f"[mpm] 保存 -> {out_npz}")
    return out_npz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--smoke-steps", type=int, default=60000)
    ap.add_argument("--dx", type=float, default=1.6e-5)
    a = ap.parse_args()
    run(smoke=a.smoke and not a.run, smoke_steps=a.smoke_steps, dx=a.dx)


if __name__ == "__main__":
    main()
