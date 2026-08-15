# -*- coding: utf-8 -*-
"""Panel 4mm ASSY の実形状 3D MPM (Material Point Method) 打ち抜き解析。2026-08-15 導入。

FEM(PANEL4MM_P2, build_panel4mm_3d_blanking.py)と同一の STEP 幾何・同一の
校正済み材料定数を使い、ソルバーだけを Lagrangian FEM から MLS-MPM
(Hu et al., SIGGRAPH 2018 の定式化 / Taichi 公式 mpm3d 系デモに準拠)へ
置き換える。目的は比較: 同条件で2手法の打ち抜き挙動を突き合わせる。

材料はブランクのみを MPM 粒子として離散化する。ダイ・ストリッパー・
パンチは剛体境界として背景グリッドへラスタライズし、剛体変位だけ
毎ステップ更新する(P2G/G2P の対象にしない = 標準的な MPM の剛体工具表現)。

⚠ 2026-08-15 スコープ変更(ユーザー承認): 背景グリッド dx=150um は板厚 0.5mm
    (3.3セル)・工具すきま 5-40um のいずれも解像できず、初回接触の瞬間に
    材料が数値的に「爆発」した(位置クランプの壁 9.150mm にeps_p<<しきい値の
    まま張り付いた)。dx=30umへの微細化はセル数125倍・ステップ数5倍で非現実的、
    かつそれでも工具すきまは解像できない。よって本スクリプトは**破断予測を
    行わない**。相当塑性ひずみ eps_p は参考表示のみで残し、粒子の削除
    (破断)判定には使わない。剛体境界条件も瞬間上書きでなく緩和(ソフト)化し、
    大局的な材料の流動・変形挙動の定性観察に限定する。定量的な破断面・
    貫入率・荷重の予測には使えない(FEM側が引き続き正)。

usage:
  python scripts/build_panel4mm_mpm.py --smoke        # 数百ステップの健全性確認
  python scripts/build_panel4mm_mpm.py --run          # フルラン
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import taichi as ti

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023
sys.path.insert(0, str(Path(__file__).parent))
from build_panel4mm_3d_blanking import (  # noqa: E402
    TAG_BLANK, TAG_DIE, TAG_STRIPPER, TAG_PUNCH, mesh_group, MM,
)

ROOT = Path(r"D:\Clawdbot_Docker_20260125")
OUT = ROOT / "data" / "workspace" / "openradioss_inc188_trials" / "mpm_panel4mm"
OUT.mkdir(parents=True, exist_ok=True)

# --- 校正済み材料定数(PANEL4MM_P2_0000.rad /MAT/LAW2/2 と同一値) ---
RHO = 2700.0          # kg/m^3
E = 69.0e9            # Pa
NU = 0.33
MU = E / (2 * (1 + NU))
LAM = E * NU / ((1 + NU) * (1 - 2 * NU))
YIELD_A = 196.4e6     # Pa
HARD_B = 524.73e6     # Pa
HARD_N = 0.7183
EPS_EFF_FAIL = 0.12   # ⚠ 未校正。FEM S5 と同値(bd n47u)

STROKE = 3.0e-3       # m。ユーザー指示
SPEED = 5.0           # m/s。FEM PANEL4MM_P2 と同一
T_STOP = STROKE / SPEED
CONTACT_TRAVEL = 0.795e-3  # 四角パンチ最初の接触travel(FEM PANEL4MM_P2実測と同一)
STRIPPER_CLOSE_T = 1.0e-4
STRIPPER_GAP = 0.19e-3  # FEM と同一(0.190mm閉じ)


def load_geometry(blank_elem_mm=0.10, tool_elem_mm=0.30):
    """PANEL4MM_3D と同じ関数で幾何を取得し、MPM 粒子・剛体ボクセルへ変換する。"""
    print("[geom] blank をメッシュ中(粒子=tet重心)...")
    c_blank, t_blank = mesh_group(TAG_BLANK, blank_elem_mm, fuse=True,
                                  add_slug=True, dz_mm=-(0.6 - 0.5 - 5e-6 / MM))
    pts = np.array([c_blank[i] for i in sorted(c_blank)], dtype=np.float64)
    idx = {old: k for k, old in enumerate(sorted(c_blank))}
    tets = np.array([[idx[int(v)] for v in t] for t in t_blank], dtype=np.int64)
    p0, p1, p2, p3 = pts[tets[:, 0]], pts[tets[:, 1]], pts[tets[:, 2]], pts[tets[:, 3]]
    centroid_mm = (p0 + p1 + p2 + p3) / 4.0
    vol_mm3 = np.abs(np.einsum("ij,ij->i", p1 - p0, np.cross(p2 - p0, p3 - p0))) / 6.0
    print(f"[geom]   blank 粒子(tet重心) = {len(centroid_mm):,}  "
          f"総体積 = {vol_mm3.sum():.4f} mm3")

    tools = {}
    for name, tags in (("die", TAG_DIE), ("stripper", TAG_STRIPPER), ("punch", TAG_PUNCH)):
        print(f"[geom] {name} をメッシュ中(剛体ボクセル用)...")
        c, t = mesh_group(tags, tool_elem_mm, fuse=False, add_slug=False)
        p = np.array([c[i] for i in sorted(c)], dtype=np.float64)
        j = {old: k for k, old in enumerate(sorted(c))}
        tt = np.array([[j[int(v)] for v in e] for e in t], dtype=np.int64)
        q0, q1, q2, q3 = p[tt[:, 0]], p[tt[:, 1]], p[tt[:, 2]], p[tt[:, 3]]
        tool_centroid_mm = (q0 + q1 + q2 + q3) / 4.0
        tools[name] = tool_centroid_mm
        print(f"[geom]   {name} ボクセル種 = {len(tool_centroid_mm):,}")
    return centroid_mm, vol_mm3, tools


def build_domain(blank_c, tools, dx):
    """全形状を包含するローカル座標系(m)へ再原点化し、グリッド範囲を決める。"""
    allc = [blank_c] + list(tools.values())
    lo = np.min([c.min(axis=0) for c in allc], axis=0) - 1.0   # mm 余白1mm
    hi = np.max([c.max(axis=0) for c in allc], axis=0) + 1.0
    hi[2] += STROKE * 1e3 + 1.0   # パンチのストローク分 + 余白(mm)
    origin_mm = lo
    size_m = (hi - lo) * MM
    n_grid = np.ceil(size_m / dx).astype(np.int32) + 1
    return origin_mm, n_grid


@ti.data_oriented
class PanelMPM:
    def __init__(self, blank_c_mm, blank_v_mm3, tools_mm, dx, origin_mm, n_grid):
        self.dx = dx
        self.inv_dx = 1.0 / dx
        self.origin = ti.Vector(origin_mm * MM)
        self.n_grid = tuple(int(x) for x in n_grid)
        self.n_particles = blank_c_mm.shape[0]

        self.x = ti.Vector.field(3, ti.f32, self.n_particles)
        self.v = ti.Vector.field(3, ti.f32, self.n_particles)
        self.C = ti.Matrix.field(3, 3, ti.f32, self.n_particles)
        self.F = ti.Matrix.field(3, 3, ti.f32, self.n_particles)
        self.mass_p = ti.field(ti.f32, self.n_particles)
        self.eps_p = ti.field(ti.f32, self.n_particles)   # 累積相当塑性ひずみ
        self.alive = ti.field(ti.i32, self.n_particles)

        self.grid_v = ti.Vector.field(3, ti.f32, self.n_grid)
        self.grid_m = ti.field(ti.f32, self.n_grid)

        x0 = (blank_c_mm * MM - origin_mm * MM).astype(np.float32)
        self.x.from_numpy(x0)
        self.mass_p.from_numpy((blank_v_mm3 * (MM ** 3) * RHO).astype(np.float32))
        self.v.from_numpy(np.zeros_like(x0, dtype=np.float32))
        self.C.from_numpy(np.zeros((self.n_particles, 3, 3), dtype=np.float32))
        self.F.from_numpy(np.tile(np.eye(3, dtype=np.float32), (self.n_particles, 1, 1)))
        self.eps_p.from_numpy(np.zeros(self.n_particles, dtype=np.float32))
        self.alive.from_numpy(np.ones(self.n_particles, dtype=np.int32))

        # 剛体工具: パンチ/ダイ/ストリッパーは押出形状(XY断面はZに依らず一定)。
        # XY足跡だけを2Dマスクとして固定保持し、Z範囲は毎ステップ連続値で判定する。
        # (t=0のグリッド添字を固定するだけでは工具の移動が境界条件に反映されない
        #  ——初回実装のバグ。健全性確認で |v|max が接触後も 0.00 のままと判明し発覚)
        self.tool_xy_mask = {}
        self.tool_z0 = {}
        self.tool_z1 = {}
        nx, ny = self.n_grid[0], self.n_grid[1]
        for name, c_mm in tools_mm.items():
            local = (c_mm * MM - origin_mm * MM) * self.inv_dx
            ij = np.round(local[:, :2]).astype(np.int32)
            ij = np.clip(ij, 0, [nx - 1, ny - 1])
            mask = np.zeros((nx, ny), dtype=np.int32)
            mask[ij[:, 0], ij[:, 1]] = 1
            self.tool_xy_mask[name] = ti.field(ti.i32, (nx, ny))
            self.tool_xy_mask[name].from_numpy(mask)
            z_local = local[:, 2] * dx  # 再度メートルに戻す(局所原点基準)
            self.tool_z0[name] = float(z_local.min())
            self.tool_z1[name] = float(z_local.max())

        self.dead_count = ti.field(ti.i32, ())

    @ti.kernel
    def clear_grid(self):
        for I in ti.grouped(self.grid_m):
            self.grid_v[I] = ti.Vector.zero(ti.f32, 3)
            self.grid_m[I] = 0.0

    @ti.kernel
    def p2g(self, dt: float):
        for p in range(self.n_particles):
            if self.alive[p] == 0:
                continue
            base = (self.x[p] * self.inv_dx - 0.5).cast(ti.i32)
            fx = self.x[p] * self.inv_dx - base.cast(ti.f32)
            w = [0.5 * (1.5 - fx) ** 2, 0.75 - (fx - 1) ** 2, 0.5 * (fx - 0.5) ** 2]

            # Neo-Hookean 応力(超弾性) + von Mises J2 リターンマッピング(等方硬化)
            F = self.F[p]
            J = ti.max(F.determinant(), 1.0e-3)  # log/inverse の特異点を避ける防御クランプ
            FinvT = F.inverse().transpose()
            P = MU * (F - FinvT) + LAM * ti.log(J) * FinvT
            # Kirchhoff 応力 -> Cauchy 近似(MLS-MPM 標準の応力寄与式)
            stress = (1.0 / J) * P @ F.transpose()

            affine = self.mass_p[p] * self.C[p] - (4 * self.inv_dx * self.inv_dx) * dt * self.mass_p[p] / RHO * stress
            for i, j, k in ti.static(ti.ndrange(3, 3, 3)):
                offset = ti.Vector([i, j, k])
                dpos = (offset.cast(ti.f32) - fx) * self.dx
                weight = w[i][0] * w[j][1] * w[k][2]
                # 破断・大変形近傍で粒子が飛ぶと base+offset が格子範囲外になり
                # illegal memory access で即クラッシュする(t=0.465msで実際に発生)。
                # 書き込み先を常に有効範囲へクリップして防御する。
                gi = ti.Vector([
                    ti.min(ti.max(base[0] + offset[0], 0), self.n_grid[0] - 1),
                    ti.min(ti.max(base[1] + offset[1], 0), self.n_grid[1] - 1),
                    ti.min(ti.max(base[2] + offset[2], 0), self.n_grid[2] - 1),
                ])
                self.grid_v[gi] += weight * (self.mass_p[p] * self.v[p] + affine @ dpos)
                self.grid_m[gi] += weight * self.mass_p[p]

    @ti.kernel
    def grid_update(self, dt: float, gravity: float,
                    die_z0: float, die_z1: float,
                    strip_z0: float, strip_z1: float, strip_vz: float,
                    punch_z0: float, punch_z1: float, punch_vz: float,
                    punch_blend: float):
        # 工具は押出形状(XY断面はZに依らず一定)。XYマスク×連続Zウィンドウで
        # 各グリッド節点が「今どの工具の内部にあるか」を毎ステップ厳密に判定する。
        # Zウィンドウは die/stripper/punch のその時点の実位置(host側で計算し
        # 引数で渡す)を使うので、工具の移動が正しく境界条件へ反映される。
        for I in ti.grouped(self.grid_m):
            if self.grid_m[I] > 0:
                self.grid_v[I] = self.grid_v[I] / self.grid_m[I]
                self.grid_v[I][2] += dt * gravity
            nz = I[2] * self.dx
            # ソフト接触: 剛体速度を瞬間上書き(Dirichlet)せず、指数的に
            # 引き込む(relax)。dx=150umは接触ギャップを解像できないため、
            # 瞬間上書きは1ステップで巨大な速度不連続を注入し爆発の直接原因
            # だった(2026-08-15フルランで実証: |v|max がクランプの30m/sに
            # 張り付いたまま定常化)。BLEND<1 でその場凌ぎの速度差を数ステップ
            # かけて解消し、力学的にはダンパー付き拘束に相当する。
            BLEND = 0.25
            if self.tool_xy_mask["die"][I[0], I[1]] == 1 and die_z0 <= nz <= die_z1:
                self.grid_v[I] = (1 - BLEND) * self.grid_v[I] + BLEND * ti.Vector([0.0, 0.0, 0.0])
            if self.tool_xy_mask["stripper"][I[0], I[1]] == 1 and strip_z0 <= nz <= strip_z1:
                self.grid_v[I] = (1 - BLEND) * self.grid_v[I] + BLEND * ti.Vector([0.0, 0.0, strip_vz])
            if self.tool_xy_mask["punch"][I[0], I[1]] == 1 and punch_z0 <= nz <= punch_z1:
                # ソフトスタート: パンチだけは初接触直後、拘束強さ punch_blend を
                # 0→BLEND へ穿入深さ 2dx 分だけ徐々に立ち上げる(host側 substep で
                # 計算)。パンチは丸穴φ0.56mm・R0.22角など細かい形状を持ち、
                # dx=60umでの角のギザギザ(エイリアシング)が初接触の瞬間に
                # 5m/sの速度不連続を1-2セルへ集中させ即座に発散していた
                # (2026-08-15確認: 接触から2チェックポイント=約6usで速度クランプ
                # 30m/sに張り付き)。パンチ自体の運動(位置)はFEMと同一のまま変えず、
                # BC の効き始めだけを緩めるので他条件はFEMと同一に保たれる。
                self.grid_v[I] = (1 - punch_blend) * self.grid_v[I] + punch_blend * ti.Vector([0.0, 0.0, punch_vz])

    @ti.kernel
    def g2p(self, dt: float):
        for p in range(self.n_particles):
            if self.alive[p] == 0:
                continue
            base = (self.x[p] * self.inv_dx - 0.5).cast(ti.i32)
            fx = self.x[p] * self.inv_dx - base.cast(ti.f32)
            w = [0.5 * (1.5 - fx) ** 2, 0.75 - (fx - 1) ** 2, 0.5 * (fx - 0.5) ** 2]
            new_v = ti.Vector.zero(ti.f32, 3)
            new_C = ti.Matrix.zero(ti.f32, 3, 3)
            for i, j, k in ti.static(ti.ndrange(3, 3, 3)):
                offset = ti.Vector([i, j, k])
                dpos = (offset.cast(ti.f32) - fx) * self.dx
                weight = w[i][0] * w[j][1] * w[k][2]
                gi = ti.Vector([
                    ti.min(ti.max(base[0] + offset[0], 0), self.n_grid[0] - 1),
                    ti.min(ti.max(base[1] + offset[1], 0), self.n_grid[1] - 1),
                    ti.min(ti.max(base[2] + offset[2], 0), self.n_grid[2] - 1),
                ])
                gv = self.grid_v[gi]
                new_v += weight * gv
                new_C += 4 * self.inv_dx * weight * gv.outer_product(dpos)
            # 速度クランプ: 課しているツール速度(SPEED=5m/s)の6倍を超える粒子は
            # 数値的病理(特異なFに起因する応力スパイク)であって物理ではない。
            # t=0.465msでの実クラッシュ(|v|max 5.55m/s→illegal address)を踏まえた防御。
            vnorm = new_v.norm()
            if vnorm > 30.0:
                new_v = new_v * (30.0 / vnorm)
            self.v[p] = new_v
            self.C[p] = new_C
            self.x[p] += dt * new_v
            for d in ti.static(range(3)):
                self.x[p][d] = ti.min(ti.max(self.x[p][d], 2 * self.dx),
                                      (self.n_grid[d] - 3) * self.dx)

            F_new = (ti.Matrix.identity(ti.f32, 3) + dt * new_C) @ self.F[p]

            # von Mises リターンマッピング(簡易・radial return, 等方硬化)
            U, sig, V = ti.svd(F_new)
            # 特異値クランプ: せん断帯直下で局所的に潰れた粒子がJ→0/∞へ発散し
            # 次ステップのNeo-Hookean応力(1/J項)を吹き飛ばす連鎖を断つ。
            # クランプ後の sig を弾性域でも必ず F_new へ反映する
            # (反映しないと、弾性域では未クランプの F がそのまま残り無意味になる)。
            for d in ti.static(range(3)):
                sig[d, d] = ti.min(ti.max(sig[d, d], 0.4), 2.5)
            F_new = U @ sig @ V.transpose()
            eps = ti.Vector([ti.log(max(sig[0, 0], 1e-6)),
                             ti.log(max(sig[1, 1], 1e-6)),
                             ti.log(max(sig[2, 2], 1e-6))])
            eps_trace = eps.sum()
            eps_dev = eps - eps_trace / 3.0 * ti.Vector([1.0, 1.0, 1.0])
            eps_dev_norm = eps_dev.norm() + 1e-12
            tau_trial = 2 * MU * eps_dev_norm
            yield_stress = YIELD_A + HARD_B * ti.pow(max(self.eps_p[p], 1e-8), HARD_N)
            if tau_trial > yield_stress:
                d_eps_p = (tau_trial - yield_stress) / (2 * MU)
                scale = 1.0 - d_eps_p / eps_dev_norm
                eps_dev *= max(scale, 0.0)
                self.eps_p[p] += d_eps_p
                new_sig = ti.exp(eps_dev + eps_trace / 3.0 * ti.Vector([1.0, 1.0, 1.0]))
                sig[0, 0], sig[1, 1], sig[2, 2] = new_sig[0], new_sig[1], new_sig[2]
                F_new = U @ sig @ V.transpose()

            # 破断予測は行わない(2026-08-15スコープ変更)。eps_p は参考表示の
            # ままとし、しきい値到達による粒子削除(alive=0)は行わない。

            self.F[p] = F_new

    def substep(self, dt, t):
        punch_disp = min(t * SPEED, STROKE)
        punch_vz = -SPEED if t * SPEED < STROKE else 0.0
        strip_disp = min(t / STRIPPER_CLOSE_T, 1.0) * STRIPPER_GAP
        strip_vz = -STRIPPER_GAP / STRIPPER_CLOSE_T if t < STRIPPER_CLOSE_T else 0.0
        # パンチのソフトスタート: 最初の接触(四角パンチ, FEM実測で travel=0.795mm)
        # からの穿入深さ 2dx 分だけ拘束強さを 0->0.25 へ線形に立ち上げる。
        # パンチの位置(punch_disp)自体は変えないので運動タイムラインはFEMと同一。
        ramp = min(max((punch_disp - CONTACT_TRAVEL) / (2 * self.dx), 0.0), 1.0)
        punch_blend = 0.25 * ramp
        self.clear_grid()
        self.p2g(dt)
        self.grid_update(
            dt, -9.8,
            self.tool_z0["die"], self.tool_z1["die"],
            self.tool_z0["stripper"] - strip_disp, self.tool_z1["stripper"] - strip_disp, strip_vz,
            self.tool_z0["punch"] - punch_disp, self.tool_z1["punch"] - punch_disp, punch_vz,
            punch_blend,
        )
        self.g2p(dt)


def run(smoke: bool, smoke_steps: int = 300, dx: float = 1.5e-4):
    ti.init(arch=ti.cuda, default_fp=ti.f32)
    blank_c, blank_v, tools = load_geometry()
    origin_mm, n_grid = build_domain(blank_c, tools, dx)
    print(f"[mpm] グリッド {tuple(n_grid)} = {int(np.prod(n_grid)):,} セル / "
          f"粒子 {blank_c.shape[0]:,}")

    sim = PanelMPM(blank_c, blank_v, tools, dx, origin_mm, n_grid)

    wave_speed = (E / RHO) ** 0.5
    dt = 0.2 * dx / wave_speed
    n_steps = smoke_steps if smoke else int(T_STOP / dt) + 1
    print(f"[mpm] dt={dt:.3e}s  想定波速={wave_speed:.1f}m/s  ステップ数={n_steps:,}"
          f"{'（健全性確認のみ）' if smoke else ''}")

    t0 = time.time()
    t = 0.0
    dump_every = max(1, n_steps // 40)
    frames = []
    out_npz = OUT / ("smoke.npz" if smoke else "full.npz")

    def save():
        # 逐次保存: 途中クラッシュ(t=0.465msで実際に発生)してもそれまでの
        # フレームは失わない。毎チェックポイントで上書き保存する。
        np.savez_compressed(out_npz,
                            origin_mm=origin_mm, dx=dx,
                            steps=[f[0] for f in frames], times=[f[1] for f in frames],
                            x=np.array([f[2] for f in frames]),
                            alive=np.array([f[3] for f in frames]),
                            eps_p=np.array([f[4] for f in frames]))

    for step in range(n_steps):
        sim.substep(dt, t)
        t += dt
        if step % dump_every == 0 or step == n_steps - 1:
            xs = sim.x.to_numpy()
            alive = sim.alive.to_numpy()
            eps = sim.eps_p.to_numpy()
            dead = int(sim.dead_count[None])
            vmax = np.abs(sim.v.to_numpy()).max()
            nan = not np.isfinite(xs).all()
            print(f"[mpm] step={step:>7,} t={t*1e3:6.3f}ms dead={dead:>7,} "
                  f"({dead/sim.n_particles*100:5.2f}%) |v|max={vmax:8.2f}m/s "
                  f"NaN={nan} elapsed={time.time()-t0:7.1f}s", flush=True)
            if nan:
                print("[mpm] !!! NaN 検出。停止。"); break
            frames.append((step, t, xs.copy(), alive.copy(), eps.copy()))
            save()

    print(f"[mpm] 保存 -> {out_npz}")
    return out_npz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--smoke-steps", type=int, default=300)
    ap.add_argument("--dx", type=float, default=1.5e-4)
    a = ap.parse_args()
    if not (a.smoke or a.run):
        a.smoke = True
    run(smoke=a.smoke and not a.run, smoke_steps=a.smoke_steps, dx=a.dx)


if __name__ == "__main__":
    main()
