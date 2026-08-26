# -*- coding: utf-8 -*-
"""丸穴(φ0.56mm)専用の局所打ち抜き診断モデル。

P1(材料要素100um、板厚5層)で丸パンチだけが破断しなかった問題を切り分ける。
直線せん断帯(build_inc188_slice3d.py)は10um/100umとも Eps_s で校正できたが、
丸穴は要素5-6個分の解像度しかなく曲率も違うため、同じ基準が通用するかは未検証。

本スクリプトは真の円形パンチ・ダイを細かい格子(既定20um)で直接メッシュする
小さな局所パッチ(既定1.2mm角)。直線スライスのような対称面は使えない
(軸対称だが平面ひずみではない)ため、パッチ外周を拘束する簡略境界条件を使う。
これは診断用の簡略化であり、本番の周辺剛性を厳密に表さないことを明記する。

usage:
  python scripts/build_round_hole_test.py --tag RH1 --eps-s 0.5
"""
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

ROOT = Path(r"D:\Clawdbot_Docker_20260125")
TRIALS = ROOT / "data" / "workspace" / "openradioss_inc188_trials"
REF_STARTER = TRIALS / "INC188AC_shear_coupon_0000.rad"

THICKNESS = 0.51e-3
HOLE_R = 0.28e-3                 # 実測 φ0.56mm (build_panel4mm_3d_blanking.py と同値)
DEFAULT_PATCH = 1.2e-3           # 局所パッチの一辺(中心が穴中心)
DEFAULT_ELEM = 20.0e-6           # 材料要素サイズ(直線スライスの校正値と同一)
DEFAULT_NZ = 26                  # 板厚方向分割(板厚0.51mm / 20um ≈ 26)
DEFAULT_CLEARANCE = 40.0e-6      # ダイ隙間。STEPから未取得のため直線スライスと同値を仮定
TOOL_GAP = 5.0e-6
DEFAULT_GAP_MAX = 15.0e-6
DEFAULT_STFAC = 1.0
DEFAULT_NSTEP = 10
TOOL_DEPTH = 0.3e-3
TOOL_ELEM = 20.0e-6              # 材料と同等以下。粗いと円形パンチの階段近似が
                                  # 材料の細メッシュに対して不均一な接触段差を作り、
                                  # 局所的な食い込みでdtが崩壊する(RH1で実証)。

I10 = "{:>10d}"
F20 = "{:>20.10g}"


def i10(v: int) -> str:
    return I10.format(int(v))


def f20(v: float) -> str:
    return F20.format(float(v))


def extract_block(text: str, start_pat: str) -> str:
    lines = text.splitlines()
    out, capturing = [], False
    for ln in lines:
        if not capturing and re.match(start_pat, ln):
            capturing = True
            out.append(ln)
            continue
        if capturing:
            if ln.startswith("/"):
                break
            out.append(ln)
    if not out:
        raise RuntimeError(f"参照デックに {start_pat} が見つかりません")
    return "\n".join(out)


def override_gene1(block: str, eps_s: float, eps_eff: float) -> str:
    lines = block.splitlines()
    out = []
    for i, ln in enumerate(lines):
        prev = lines[i - 1] if i else ""
        if "Eps_max" in prev and "Eps_eff" in prev:
            ln = f"{i10(0)}{f20(0.0)}{f20(0.0)}{f20(eps_eff)}{f20(0.0)}"
        elif "Eps_min" in prev and "Eps_s" in prev:
            ln = f"{f20(0.0)}{f20(eps_s)}{i10(0)}{i10(0)}{i10(0)}"
        out.append(ln)
    return "\n".join(out)


def load_reference_cards() -> dict[str, str]:
    txt = REF_STARTER.read_text(encoding="utf-8", errors="replace")
    return {
        "mat_blank": extract_block(txt, r"^/MAT/LAW2/2\b"),
        "mat_tool": extract_block(txt, r"^/MAT/LAW1/1\b"),
        "fail": extract_block(txt, r"^/FAIL/GENE1/2\b"),
        "funct_punch": extract_block(txt, r"^/FUNCT/1\b"),
        "prop1": extract_block(txt, r"^/PROP/SOLID/1\b"),
        "prop2": extract_block(txt, r"^/PROP/SOLID/2\b"),
        "inter1": extract_block(txt, r"^/INTER/TYPE25/1\b"),
    }


def remap_type25(block: str, iid: int, label: str, surf1: int, surf2: int, gap_max: float,
                 stfac: float) -> str:
    lines = block.splitlines()
    lines[0] = f"/INTER/TYPE25/{iid}/0"
    lines[1] = label
    lines[3] = f"{i10(surf1)}{i10(surf2)}" + lines[3][20:]
    lines[5] = lines[5][:-40] + f20(gap_max) + f20(gap_max)
    lines[9] = f20(stfac) + lines[9][20:]
    return "\n".join(lines)


class Mesh:
    def __init__(self):
        self.nodes: dict[int, tuple] = {}
        self.bricks: dict[int, list] = {}
        self.parts: dict[int, list] = {}
        self._nid = 1
        self._eid = 1
        self._grid: dict[tuple, int] = {}

    def node(self, x, y, z):
        key = (round(x, 12), round(y, 12), round(z, 12))
        if key in self._grid:
            return self._grid[key]
        nid = self._nid
        self._nid += 1
        self.nodes[nid] = (x, y, z)
        self._grid[key] = nid
        return nid

    def brick(self, part, n8):
        eid = self._eid
        self._eid += 1
        self.bricks[eid] = n8
        self.parts.setdefault(part, []).append(eid)
        return eid


def grid_axis(lo, hi, elem):
    n = max(1, int(round((hi - lo) / elem)))
    return [lo + (hi - lo) * i / n for i in range(n + 1)]


def add_box(mesh: Mesh, part, x0, x1, y0, y1, z0, z1, elem, nz=None):
    xs = grid_axis(x0, x1, elem)
    ys = grid_axis(y0, y1, elem)
    zs = grid_axis(z0, z1, elem) if nz is None else [z0 + (z1 - z0) * k / nz for k in range(nz + 1)]
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            for k in range(len(zs) - 1):
                n8 = [
                    mesh.node(xs[i], ys[j], zs[k]),
                    mesh.node(xs[i + 1], ys[j], zs[k]),
                    mesh.node(xs[i + 1], ys[j + 1], zs[k]),
                    mesh.node(xs[i], ys[j + 1], zs[k]),
                    mesh.node(xs[i], ys[j], zs[k + 1]),
                    mesh.node(xs[i + 1], ys[j], zs[k + 1]),
                    mesh.node(xs[i + 1], ys[j + 1], zs[k + 1]),
                    mesh.node(xs[i], ys[j + 1], zs[k + 1]),
                ]
                mesh.brick(part, n8)
    return xs, ys, zs


def add_disc(mesh: Mesh, part, r_out, z0, z1, elem, nz=None, r_in=0.0):
    """円盤(r_in<=r<=r_out)を正方格子でスタイヤケース近似する。"""
    xs = grid_axis(-r_out, r_out, elem)
    ys = grid_axis(-r_out, r_out, elem)
    zs = grid_axis(z0, z1, elem) if nz is None else [z0 + (z1 - z0) * k / nz for k in range(nz + 1)]
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            xm = (xs[i] + xs[i + 1]) / 2
            ym = (ys[j] + ys[j + 1]) / 2
            rm = math.hypot(xm, ym)
            if rm > r_out or rm < r_in:
                continue
            for k in range(len(zs) - 1):
                n8 = [
                    mesh.node(xs[i], ys[j], zs[k]),
                    mesh.node(xs[i + 1], ys[j], zs[k]),
                    mesh.node(xs[i + 1], ys[j + 1], zs[k]),
                    mesh.node(xs[i], ys[j + 1], zs[k]),
                    mesh.node(xs[i], ys[j], zs[k + 1]),
                    mesh.node(xs[i + 1], ys[j], zs[k + 1]),
                    mesh.node(xs[i + 1], ys[j + 1], zs[k + 1]),
                    mesh.node(xs[i], ys[j + 1], zs[k + 1]),
                ]
                mesh.brick(part, n8)
    return xs, ys, zs


def add_annulus(mesh: Mesh, part, r_in, r_out, z0, z1, elem, nz=None):
    return add_disc(mesh, part, r_out, z0, z1, elem, nz=nz, r_in=r_in)


def fmt_grnod(gid: int, name: str, node_ids) -> list[str]:
    uniq = sorted(set(node_ids))
    out = [f"/GRNOD/NODE/{gid}", name, f"{i10(len(uniq))}"]
    for k in range(0, len(uniq), 10):
        out.append("".join(i10(n) for n in uniq[k:k + 10]))
    return out


def build(tag, elem, patch, clearance, tstop, eps_s, eps_eff, nz, punch_speed):
    ref = load_reference_cards()
    ref["fail"] = override_gene1(ref["fail"], eps_s, eps_eff)

    mesh = Mesh()
    half = patch / 2.0
    r_out_domain = half

    blank_xs, blank_ys, blank_zs = add_box(
        mesh, 2, -half, half, -half, half, 0.0, THICKNESS, elem, nz=nz)
    blank_all = [n for eid in mesh.parts[2] for n in mesh.bricks[eid]]

    gap = TOOL_GAP
    punch_xs, _, _ = add_disc(
        mesh, 1, HOLE_R, THICKNESS + gap, THICKNESS + gap + TOOL_DEPTH, TOOL_ELEM)
    die_xs, _, _ = add_annulus(
        mesh, 3, HOLE_R + clearance, r_out_domain,
        0.0 - TOOL_DEPTH - gap, 0.0 - gap, TOOL_ELEM)
    strip_xs, _, _ = add_annulus(
        mesh, 4, HOLE_R + clearance, r_out_domain,
        THICKNESS + gap, THICKNESS + gap + TOOL_DEPTH, TOOL_ELEM)

    L: list[str] = ["#RADIOSS STARTER", "/BEGIN", f"ROUND_HOLE_{tag}",
                    f"{i10(2022)}{i10(0)}",
                    f"{'kg':>20}{'m':>20}{'s':>20}",
                    f"{'kg':>20}{'m':>20}{'s':>20}",
                    "/TITLE", f"Round hole diagnostic ({tag})"]
    L.append("/ANALY")
    L.append("#    N2D3D             IPARITH")
    L.append(f"{i10(0)}          {i10(1)}")

    L.append("/NODE")
    for nid, (x, y, z) in mesh.nodes.items():
        L.append(f"{i10(nid)}{f20(x)}{f20(y)}{f20(z)}")

    for pid, eids in sorted(mesh.parts.items()):
        L.append(f"/BRICK/{pid}")
        for eid in eids:
            n8 = mesh.bricks[eid]
            L.append(f"{i10(eid)}" + "".join(i10(n) for n in n8))

    L.append(ref["mat_tool"])
    L.append(ref["mat_blank"])
    L.append(ref["fail"])
    L.append(ref["prop1"])
    L.append(ref["prop2"])

    for pid, pname, prop, mat in ((1, "Punch", 1, 1), (2, "Blank", 2, 2),
                                  (3, "Die", 1, 1), (4, "Stripper", 1, 1)):
        L.append(f"/PART/{pid}")
        L.append(pname)
        L.append("#    Prop_ID     Mat_ID")
        L.append(f"{i10(prop)}{i10(mat)}")

    punch_nodes = [n for eid in mesh.parts[1] for n in mesh.bricks[eid]]
    die_nodes = [n for eid in mesh.parts[3] for n in mesh.bricks[eid]]
    strip_nodes = [n for eid in mesh.parts[4] for n in mesh.bricks[eid]]

    L.extend(fmt_grnod(100, "Punch_Nodes", punch_nodes))
    L.extend(fmt_grnod(200, "Blank_Nodes", blank_all))
    L.extend(fmt_grnod(300, "Die_Nodes", die_nodes))
    L.extend(fmt_grnod(400, "Stripper_Nodes", strip_nodes))

    # 外周固定: 局所パッチの簡略境界条件。周辺母材の剛性を厳密には表さない。
    tol = elem * 0.5
    rim = [n for n in blank_all if abs(abs(mesh.nodes[n][0]) - half) < tol
          or abs(abs(mesh.nodes[n][1]) - half) < tol]
    L.extend(fmt_grnod(900, "Blank_Rim_Fixed", rim))

    for sid, pid in ((1, 1), (2, 2), (3, 3), (4, 4)):
        L.append(f"/SURF/PART/EXT/{sid}00/0")
        L.append(f"Surf_Part_{pid}")
        L.append(f"{i10(pid)}")

    L.append(ref["funct_punch"])
    L.append("/FUNCT/2")
    L.append("Zero")
    L.append("#                  X                   Y")
    L.append(f"{f20(0.0)}{f20(0.0)}")
    L.append(f"{f20(1.0)}{f20(0.0)}")
    # 速度指令は必ず滑らかな立ち上がりにする。瞬間発進は円周全体が同時接触する
    # 丸穴形状で局所貫入(pinch)を誘発しdtを崩壊させる(過去のMPM調査と同じ教訓、
    # RH1/RH2で実証済み)。smoothstep(3x^2-2x^3)でramp_time秒かけて立ち上げる。
    ramp_time = max(tstop * 0.08, 3.0e-6)
    n_ramp = 12
    L.append("/FUNCT/3")
    L.append("Punch_Smooth_Ramp")
    L.append("#                  X                   Y")
    for k in range(n_ramp + 1):
        x = ramp_time * k / n_ramp
        s = k / n_ramp
        v = -punch_speed * (3 * s * s - 2 * s * s * s)
        L.append(f"{f20(x)}{f20(v)}")
    L.append(f"{f20(tstop * 2)}{f20(-punch_speed)}")

    L.append("/IMPVEL/1")
    L.append("Punch_Z")
    L.append("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe")
    L.append(f"{i10(3)}{'Z':>10}{i10(0)}{i10(0)}{i10(100)}{i10(0)}{i10(0)}")
    L.append("#             Ascale_x            Fscale_y              Tstart               Tstop")
    L.append(f"{f20(1.0)}{f20(1.0)}{f20(0.0)}{f20(1.0e30)}")

    imp = 2
    for gid, d in ((900, "X"), (900, "Y"), (900, "Z")):
        L.append(f"/IMPVEL/{imp}")
        L.append(f"Rim_Fixed_{d}")
        L.append("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe")
        L.append(f"{i10(2)}{d:>10}{i10(0)}{i10(0)}{i10(gid)}{i10(0)}{i10(0)}")
        L.append("#             Ascale_x            Fscale_y              Tstart               Tstop")
        L.append(f"{f20(1.0)}{f20(1.0)}{f20(0.0)}{f20(1.0e30)}")
        imp += 1
    for gid, d in ((300, "X"), (300, "Y"), (300, "Z"), (400, "X"), (400, "Y"), (400, "Z")):
        L.append(f"/IMPVEL/{imp}")
        L.append(f"Fixed_{gid}_{d}")
        L.append("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe")
        L.append(f"{i10(2)}{d:>10}{i10(0)}{i10(0)}{i10(gid)}{i10(0)}{i10(0)}")
        L.append("#             Ascale_x            Fscale_y              Tstart               Tstop")
        L.append(f"{f20(1.0)}{f20(1.0)}{f20(0.0)}{f20(1.0e30)}")
        imp += 1

    for iid, s1, s2, label in ((1, 100, 200, "Punch_Material_Contact"),
                               (2, 300, 200, "Die_Material_Contact"),
                               (3, 400, 200, "Stripper_Material_Contact")):
        L.append(remap_type25(ref["inter1"], iid, label, s1, s2, DEFAULT_GAP_MAX, DEFAULT_STFAC))

    L.append("/END")

    starter = TRIALS / f"ROUND_HOLE_{tag}_0000.rad"
    starter.write_text("\n".join(L) + "\n", encoding="utf-8")
    engine = TRIALS / f"ROUND_HOLE_{tag}_0001.rad"
    engine.write_text("\n".join([
        f"/RUN/ROUND_HOLE_{tag}/1", f"{f20(tstop)}", "/DT/NODA/0",
        f"{f20(0.9)}{f20(0.0)}", "/RFILE/50000", "/TFILE/4", f"{f20(1.0e-6)}",
        "/ANIM/DT", f"{f20(0.0)}{f20(tstop/12)}",
        "/ANIM/ELEM/EPSP", "/ANIM/ELEM/VONM", "/ANIM/VECT/DISP", "/END", "",
    ]), encoding="utf-8")

    print(f"[round] 節点 {len(mesh.nodes)} / BRICK {len(mesh.bricks)}")
    for pid, eids in sorted(mesh.parts.items()):
        print(f"[round]   part {pid}: {len(eids)}")
    print(f"[round] HOLE_R {HOLE_R*1e6:.1f}um / 隙間 {clearance*1e6:.1f}um / "
          f"要素 {elem*1e6:.1f}um / パッチ {patch*1e3:.2f}mm / eps_s {eps_s}")
    print(f"[round] starter -> {starter}")
    return starter, engine


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="丸穴(φ0.56mm)診断モデル")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--elem", type=float, default=DEFAULT_ELEM)
    ap.add_argument("--patch", type=float, default=DEFAULT_PATCH)
    ap.add_argument("--clearance", type=float, default=DEFAULT_CLEARANCE)
    ap.add_argument("--tstop", type=float, default=6.0e-5)
    ap.add_argument("--eps-s", type=float, default=0.5)
    ap.add_argument("--eps-eff", type=float, default=100.0)
    ap.add_argument("--nz", type=int, default=DEFAULT_NZ)
    ap.add_argument("--punch-speed", type=float, default=5.0)
    a = ap.parse_args(argv)
    build(a.tag, a.elem, a.patch, a.clearance, a.tstop, a.eps_s, a.eps_eff, a.nz, a.punch_speed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
