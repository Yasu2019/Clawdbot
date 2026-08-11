# -*- coding: utf-8 -*-
"""INC-188: 切断線断面を「X方向1要素の3Dスライス」で解く（擬似2D）。

## なぜ純2Dをやめたか

OpenRadioss の 2D(QUAD, N2D3D=2) では要素削除が起きない。実測:

  3D (INC188AC, BRICK/TETRA, /FAIL/GENE1)      -> RUPTURE OF SOLID ELEMENT が 2,042件
  2D (INC188_2D_2DA/2DB/2DC, QUAD, 同じカード) -> 0件

2D側はしきい値を 13分の1(Eps_eff 0.12 -> Eps_max 0.05)まで下げても、
962要素が超過した状態で EROSION_STATUS が全て生存のままだった。
同一の破断カードが3Dでは2,042要素を削除しているので、しきい値ではなく
「2D QUAD に対する要素削除の経路」が働いていないと判断した。

## 代わりに何をするか

3D のまま、平面ひずみ方向(X)を **1要素だけ**にしたスライスを解く。

  - 要素削除は 3D の実績ある経路をそのまま使える
  - 切断面内は 10um まで細かくできる。要素数は 2D と同オーダー
  - 両側のX面を X 方向拘束すれば平面ひずみと等価
  - 校正して得た値は、同じ要素種別・同じ破断カードなのでフル3Dへそのまま持ち込める

  python scripts/build_inc188_slice3d.py --tag S1 --clearance 40e-6
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

ROOT = Path(r"D:\Clawdbot_Docker_20260125")
TRIALS = ROOT / "data" / "workspace" / "openradioss_inc188_trials"
REF_STARTER = TRIALS / "INC188AC_shear_coupon_0000.rad"

THICKNESS = 0.51e-3
BLANK_HALF_WIDTH = 2.0e-3
TOOL_DEPTH = 0.6e-3
DEFAULT_SHEAR_ELEM = 10.0e-6
DEFAULT_BAND = 0.20e-3
DEFAULT_COARSE = 100.0e-6
DEFAULT_CLEARANCE = 40.0e-6      # 板厚の約7.8%。隙間ゼロだと剪断帯が立たない(2DAで実証)
DEFAULT_SLICE = 20.0e-6          # X方向のスライス厚（1要素）
TOOL_GAP = 5.0e-6                # 工具と板の初期すきま。初期貫入エラーを避ける

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
        raise RuntimeError(f"3Dデックに {start_pat} が見つかりません")
    return "\n".join(out)


def override_gene1(block: str, eps_pmax, eps_eff, eps_s, volfrac) -> str:
    lines = block.splitlines()
    out = []
    for i, ln in enumerate(lines):
        prev = lines[i - 1] if i else ""
        if "Eps_max" in prev and "Eps_eff" in prev and eps_pmax is not None:
            ln = (f"{i10(0)}{f20(0.0)}{f20(eps_pmax)}"
                  f"{f20(eps_eff if eps_eff is not None else 0.12)}{f20(0.0)}")
        elif "Eps_min" in prev and "Eps_s" in prev and eps_s is not None:
            ln = f"{f20(0.0)}{f20(eps_s)}{i10(0)}{i10(0)}{i10(0)}"
        elif "Volfrac" in prev and "NCS" in prev and volfrac is not None:
            ln = f"{f20(volfrac)}{f20(0.0)}{i10(1)}{f20(0.0)}"
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
    }


def graded_axis(center, half_lo, half_hi, fine, band, coarse) -> list[float]:
    pts = [center]
    n_band = max(1, int(round(band / fine)))
    for i in range(1, n_band + 1):
        pts.append(center + i * fine)
        pts.append(center - i * fine)

    def extend(sign, limit):
        x = center + sign * band
        size = fine
        while True:
            size = min(size * 1.15, coarse)
            nxt = x + sign * size
            if (sign > 0 and nxt > center + limit) or (sign < 0 and nxt < center - limit):
                if abs((center + sign * limit) - x) > fine * 0.25:
                    pts.append(center + sign * limit)
                break
            pts.append(nxt)
            x = nxt

    extend(+1, half_hi)
    extend(-1, half_lo)
    return sorted(set(round(p, 12) for p in pts))


def uniform_axis(lo, hi, size) -> list[float]:
    n = max(1, int(round((hi - lo) / size)))
    return [lo + (hi - lo) * i / n for i in range(n + 1)]


class MeshSlice:
    """X方向1層のBRICKメッシュ。X=0 と X=dx の2枚の節点面を持つ。"""

    def __init__(self, dx: float) -> None:
        self.dx = dx
        self.nodes: dict[int, tuple[float, float, float]] = {}
        self.bricks: dict[int, tuple[int, ...]] = {}
        self._nid = 0
        self._eid = 0
        self.parts: dict[int, list[int]] = {}
        self.x0_nodes: list[int] = []
        self.x1_nodes: list[int] = []

    def add_node(self, x, y, z) -> int:
        self._nid += 1
        self.nodes[self._nid] = (x, y, z)
        return self._nid

    def add_grid(self, ys, zs, part_id) -> dict:
        g0: dict[tuple[int, int], int] = {}
        g1: dict[tuple[int, int], int] = {}
        for j, z in enumerate(zs):
            for i, y in enumerate(ys):
                n0 = self.add_node(0.0, y, z)
                n1 = self.add_node(self.dx, y, z)
                g0[(i, j)] = n0
                g1[(i, j)] = n1
                self.x0_nodes.append(n0)
                self.x1_nodes.append(n1)
        ids = self.parts.setdefault(part_id, [])
        for j in range(len(zs) - 1):
            for i in range(len(ys) - 1):
                # 下面(X=0)を反時計回り、続いて上面(X=dx)を同順。BRICKの標準結線。
                a, b = g0[(i, j)], g0[(i + 1, j)]
                c, d = g0[(i + 1, j + 1)], g0[(i, j + 1)]
                e, f = g1[(i, j)], g1[(i + 1, j)]
                gg, h = g1[(i + 1, j + 1)], g1[(i, j + 1)]
                self._eid += 1
                self.bricks[self._eid] = (a, b, c, d, e, f, gg, h)
                ids.append(self._eid)
        alln = list(g0.values()) + list(g1.values())
        return {"all": alln,
                "left": [g0[(0, j)] for j in range(len(zs))] + [g1[(0, j)] for j in range(len(zs))],
                "right": [g0[(len(ys) - 1, j)] for j in range(len(zs))]
                         + [g1[(len(ys) - 1, j)] for j in range(len(zs))]}


def fmt_grnod(gid, name, nodes) -> list[str]:
    out = [f"/GRNOD/NODE/{gid}", name]
    uniq = sorted(set(nodes))
    for k in range(0, len(uniq), 10):
        out.append("".join(i10(n) for n in uniq[k:k + 10]))
    return out


def build(tag, shear_elem, band, coarse, clearance, tstop, slice_dx,
          eps_pmax, eps_eff, eps_s, volfrac):
    ref = load_reference_cards()
    if any(v is not None for v in (eps_pmax, eps_eff, eps_s, volfrac)):
        ref["fail"] = override_gene1(ref["fail"], eps_pmax, eps_eff, eps_s, volfrac)

    mesh = MeshSlice(slice_dx)
    y_cut = BLANK_HALF_WIDTH
    z0, z1 = 0.0, THICKNESS

    ys = graded_axis(y_cut, BLANK_HALF_WIDTH, BLANK_HALF_WIDTH, shear_elem, band, coarse)
    zs = uniform_axis(z0, z1, shear_elem)
    blank = mesh.add_grid(ys, zs, 2)

    tool_elem = max(coarse, 50.0e-6)
    # 工具は板面から微小ギャップだけ離して置く。面接触で置くと Starter が
    # "SECONDARY NODE IS ON THE MAIN SURFACE" を全接触節点分(268件)出して止まる。
    # INACTI で逃がす手もあるが、フィールド位置が版で変わるため幾何側で解消する。
    gap = TOOL_GAP
    punch = mesh.add_grid(uniform_axis(0.0, y_cut, tool_elem),
                          uniform_axis(z1 + gap, z1 + gap + TOOL_DEPTH, tool_elem), 1)
    die = mesh.add_grid(uniform_axis(y_cut + clearance, 2 * y_cut, tool_elem),
                        uniform_axis(z0 - TOOL_DEPTH - gap, z0 - gap, tool_elem), 3)
    strip = mesh.add_grid(uniform_axis(y_cut + clearance, 2 * y_cut, tool_elem),
                          uniform_axis(z1 + gap, z1 + gap + TOOL_DEPTH, tool_elem), 4)

    L: list[str] = ["#RADIOSS STARTER", "/BEGIN", f"INC188_S_{tag}",
                    f"{i10(2022)}{i10(0)}",
                    f"{'kg':>20}{'m':>20}{'s':>20}",
                    f"{'kg':>20}{'m':>20}{'s':>20}",
                    "/TITLE", f"INC188 quasi-2D slice ({tag})"]
    # 3D解析。2Dにすると要素削除が働かないため(実測)
    L.append("/ANALY")
    L.append("#    N2D3D             IPARITH")
    L.append(f"{i10(0)}          {i10(1)}")

    L.append("/NODE")
    for nid, (x, y, z) in mesh.nodes.items():
        L.append(f"{i10(nid)}{f20(x)}{f20(y)}{f20(z)}")

    for pid, eids in sorted(mesh.parts.items()):
        L.append(f"/BRICK/{pid}")
        for eid in eids:
            n = mesh.bricks[eid]
            L.append(i10(eid) + "".join(i10(v) for v in n))

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

    L.extend(fmt_grnod(100, "Punch_Nodes", punch["all"]))
    L.extend(fmt_grnod(200, "Blank_Nodes", blank["all"]))
    L.extend(fmt_grnod(300, "Die_Nodes", die["all"]))
    L.extend(fmt_grnod(400, "Stripper_Nodes", strip["all"]))
    # 平面ひずみ条件: 全節点のX変位を止める。X方向1要素なので両面拘束と等価。
    L.extend(fmt_grnod(900, "All_X_Constrained", list(mesh.nodes.keys())))

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

    L.append("/IMPDISP/1")
    L.append("Punch_Displacement_Z")
    L.append("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor")
    L.append(f"{i10(1)}{'Z':>10}{i10(0)}{i10(0)}{i10(100)}{i10(0)}")
    L.append("#             Ascale_x            Fscale_y              Tstart               Tstop")
    L.append(f"{f20(1.0)}{f20(1.0)}{f20(0.0)}{f20(1.0e30)}")

    imp = 2
    for gid, d, name in ((900, "X", "PlaneStrain_X"), (100, "Y", "Punch_Y"),
                         (300, "Y", "Die_Y"), (300, "Z", "Die_Z"),
                         (400, "Y", "Strip_Y"), (400, "Z", "Strip_Z")):
        L.append(f"/IMPVEL/{imp}")
        L.append(name)
        L.append("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe")
        L.append(f"{i10(2)}{d:>10}{i10(0)}{i10(0)}{i10(gid)}{i10(0)}{i10(0)}")
        L.append("#             Ascale_x            Fscale_y              Tstart               Tstop")
        L.append(f"{f20(1.0)}{f20(1.0)}{f20(0.0)}{f20(1.0e30)}")
        imp += 1

    # 3D なので TYPE7 が使える（2Dでは非対応だった）
    for iid, sec, mst, label in ((1, 200, 100, "Blank_to_Punch"),
                                 (2, 200, 300, "Blank_to_Die"),
                                 (3, 200, 400, "Blank_to_Stripper")):
        L.append(f"/INTER/TYPE7/{iid}")
        L.append(label)
        L.append("# grnod_id   surf_id      Istf                Igap   Multimp      Ibag      Idel     Icurv")
        L.append(f"{i10(sec)}{i10(mst)}{i10(0)}{'':>10}{i10(0)}{i10(0)}{i10(0)}{i10(0)}{i10(0)}")
        L.append("#          Gap_scale             Gap_max")
        L.append(f"{f20(0.0)}{f20(0.0)}")
        L.append("#              STMIN               STMAX")
        L.append(f"{f20(0.0)}{f20(0.0)}")
        L.append("#       N1        N2")
        L.append(f"{i10(0)}{i10(0)}")
        L.append("#              STFAC                FRIC              GAPmin              Tstart               Tstop")
        L.append(f"{f20(1.0)}{f20(0.1)}{f20(0.0)}{f20(0.0)}{f20(1.0e30)}")
        L.append("#      IBC                        INACTI               VIS_S               VIS_F              BUMULT")
        # INACTI=5: 初期貫入をギャップ縮小で解消する。パンチを板面に接して置いているため
        # INACTI=0 のままだと "SECONDARY NODE IS ON THE MAIN SURFACE" で268件のエラーになる。
        L.append(f"{'':>7}{0}{0}{0}{'':>20}{i10(5)}{f20(0.0)}{f20(0.0)}{f20(0.0)}")
        L.append("#    Ifric    Ifiltr               Xfreq     Iform")
        L.append(f"{i10(0)}{i10(0)}{f20(0.0)}{i10(0)}")

    L.append("/END")

    starter = TRIALS / f"INC188_S_{tag}_0000.rad"
    starter.write_text("\n".join(L) + "\n", encoding="utf-8")
    engine = TRIALS / f"INC188_S_{tag}_0001.rad"
    engine.write_text("\n".join([
        f"/RUN/INC188_S_{tag}/1", f"{f20(tstop)}", "/DT/NODA/0",
        f"{f20(0.9)}{f20(0.0)}", "/RFILE/50000", "/TFILE/4", f"{f20(1.0e-5)}",
        "/ANIM/DT", f"{f20(0.0)}{f20(2.0e-4)}",
        "/ANIM/ELEM/EPSP", "/ANIM/ELEM/VONM", "/ANIM/VECT/DISP", "/END", "",
    ]), encoding="utf-8")

    print(f"[slice] 節点 {len(mesh.nodes)} / BRICK {len(mesh.bricks)}")
    for pid, eids in sorted(mesh.parts.items()):
        print(f"[slice]   part {pid}: {len(eids)}")
    print(f"[slice] せん断帯 {shear_elem*1e6:.1f}um / 隙間 {clearance*1e6:.1f}um "
          f"/ スライス厚 {slice_dx*1e6:.1f}um / tstop {tstop:g}")
    print(f"[slice] starter -> {starter}")
    return starter, engine


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="INC-188 擬似2Dスライスモデル")
    ap.add_argument("--tag", default="S1")
    ap.add_argument("--shear-elem", type=float, default=DEFAULT_SHEAR_ELEM)
    ap.add_argument("--band", type=float, default=DEFAULT_BAND)
    ap.add_argument("--coarse", type=float, default=DEFAULT_COARSE)
    ap.add_argument("--clearance", type=float, default=DEFAULT_CLEARANCE)
    ap.add_argument("--tstop", type=float, default=2.2e-3)
    ap.add_argument("--slice", type=float, default=DEFAULT_SLICE, dest="slice_dx")
    ap.add_argument("--eps-pmax", type=float, default=None)
    ap.add_argument("--eps-eff", type=float, default=None)
    ap.add_argument("--eps-s", type=float, default=None)
    ap.add_argument("--volfrac", type=float, default=None)
    a = ap.parse_args(argv)
    build(a.tag, a.shear_elem, a.band, a.coarse, a.clearance, a.tstop, a.slice_dx,
          a.eps_pmax, a.eps_eff, a.eps_s, a.volfrac)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
