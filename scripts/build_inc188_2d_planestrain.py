# -*- coding: utf-8 -*-
"""INC-188 推奨1: 切断線断面の2D平面ひずみモデルを生成する。

## なぜ2Dなのか

3D陽解法では切断輪郭の亀裂が成長しない。メッシュを8倍細かく(20x20x5 -> 40x40x10)しても
輪郭破断は 9.3% -> 6.7% と伸びなかった(引き継ぎ §3 AB->AC)。
一方、収集文献で打抜き面予測に成功しているものは**すべて2次元**である。

  PMC11066666: 軸対称 CAX4R、1mm板に12,257要素、MMC3破壊則
  PMC11012880: せん断帯 21-44um を **10um要素**で解像

せん断帯を解像するには10um級が要る。3Dで10um一様は100万要素で不可能だが、2Dなら数千要素で足りる。
本モデルで荷重-ストロークを実測と突き合わせて破断則を校正し、得た値を3Dへ持ち込む。
RCA が要求していた force-stroke calibration を実現する唯一の現実的な道(引き継ぎ §6)。

## OpenRadioss 2D の要件(一次情報で確認済み)

  /ANALY の N2D3D = 2 が平面ひずみ。X が平面ひずみ方向
      hm_cfg_files/config/CFG/radioss2023/CARDS/analy.cfg
      書式 CARD("%10d          %10d", N2D3D, IPARITH)
  /QUAD/part_ID ブロック。1行に quad_ID と節点4つ
  節点は**グローバルYZ平面**上に置き、要素法線は+X方向
  モデルは Y+ / Z+ 象限に置くことが推奨される

## 校正の等価性

材料(/MAT/LAW2)、破断(/FAIL/GENE1)、パンチ変位曲線(/FUNCT/1)は
3Dデック INC188AC_shear_coupon_0000.rad から**そのまま引き写す**。
ここが違うと校正値を3Dへ持ち込めない。

  python scripts/build_inc188_2d_planestrain.py --tag 2DA
  python scripts/build_inc188_2d_planestrain.py --tag 2DB --shear-elem 5e-6
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

# --- 単位系は3Dデックと同じ kg / m / s -------------------------------------
THICKNESS = 0.51e-3      # 板厚 [m] (実測材 MR536-H34)
BLANK_HALF_WIDTH = 2.0e-3  # 切断線から左右へ確保する材料幅 [m]
TOOL_DEPTH = 0.6e-3      # 工具の見かけ厚み [m] (剛性が出れば十分)
DEFAULT_SHEAR_ELEM = 10.0e-6   # せん断帯の要素寸法 [m] (文献 PMC11012880 と同じ10um)
DEFAULT_BAND = 0.20e-3   # 細メッシュ帯の半幅 [m]
DEFAULT_COARSE = 100.0e-6  # 遠方の最大要素寸法 [m]
DEFAULT_CLEARANCE = 0.0  # ダイ隙間 [m]。3DはTrial Xで隙間を解消しているので既定0

I10 = "{:>10d}"
F20 = "{:>20.10g}"


def i10(v: int) -> str:
    return I10.format(int(v))


def f20(v: float) -> str:
    return F20.format(float(v))


# --------------------------------------------------------------------------
# 3Dデックからの引き写し
# --------------------------------------------------------------------------
def extract_block(text: str, start_pat: str) -> str:
    """`/CARD` 行から次の `/` 行の直前までを取り出す。"""
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


def override_gene1(block: str, eps_pmax: float | None, eps_eff: float | None,
                   eps_s: float | None, volfrac: float | None) -> str:
    """/FAIL/GENE1 のしきい値を差し替える。

    カード書式 (hm_cfg_files .../FAIL/fail_gene1.cfg):
      行A "# fct_IDps  Eps_dot_ps  Eps_max  Eps_eff  Eps_vol"  -> 塑性ひずみ系
      行B "#  Eps_min  Eps_s  fct_IDg12 fct_IDg13 fct_IDe1c"   -> せん断ひずみ
      行C "#  Volfrac  Pthickfail  NCS  Temp_max"              -> 固体の削除体積率

    3Dデックは Eps_max=0(無効) で、実効ひずみ Eps_eff と せん断 Eps_s だけを使っていた。
    実測では塑性ひずみが 2.167 まで達しているのに要素が1つも削除されないため、
    塑性ひずみ基準(Eps_max)を明示的に有効化できるようにする。
    """
    lines = block.splitlines()
    out = []
    for i, ln in enumerate(lines):
        prev = lines[i - 1] if i else ""
        if "Eps_max" in prev and "Eps_eff" in prev and eps_pmax is not None:
            # fct_IDps(i10) Eps_dot_ps(f20) Eps_max(f20) Eps_eff(f20) Eps_vol(f20)
            ln = (f"{i10(0)}{f20(0.0)}{f20(eps_pmax)}"
                  f"{f20(eps_eff if eps_eff is not None else 0.12)}{f20(0.0)}")
        elif "Eps_min" in prev and "Eps_s" in prev and eps_s is not None:
            ln = f"{f20(0.0)}{f20(eps_s)}{i10(0)}{i10(0)}{i10(0)}"
        elif "Volfrac" in prev and "NCS" in prev and volfrac is not None:
            ln = f"{f20(volfrac)}{f20(0.0)}{i10(1)}{f20(0.0)}"
        out.append(ln)
    return "\n".join(out)


def override_law2_epsmax(block: str, eps_p_max: float) -> str:
    """/MAT/LAW2 の EPS_p_max（材料則に内蔵された塑性ひずみ破断）を差し替える。

    3Dデックは 10.0 で、実質無効になっている。/FAIL/GENE1 側は
    しきい値を 0.05 まで下げても要素が1つも削除されなかった(962要素が超過しても
    EROSION_STATUS が全て生存)ため、固体要素で標準的に働く LAW2 内蔵の破断で
    機構そのものを確認する。

    データ行の書式: a(f20) b(f20) n(f20) EPS_p_max(f20) Xmax(f20)
    """
    lines = block.splitlines()
    out = []
    for i, ln in enumerate(lines):
        prev = lines[i - 1] if i else ""
        if "EPS_p_max" in prev and "Xmax" in prev:
            toks = ln.split()
            if len(toks) >= 5:
                a, b, n = toks[0], toks[1], toks[2]
                xmax = toks[4]
                ln = (f"{a:>20}{b:>20}{n:>20}{f20(eps_p_max)}{xmax:>20}")
        out.append(ln)
    return "\n".join(out)


def load_reference_cards() -> dict[str, str]:
    """材料・破断・パンチ変位曲線を3Dデックから読む。校正の等価性のため改変しない。"""
    if not REF_STARTER.exists():
        raise RuntimeError(f"参照デックがありません: {REF_STARTER}")
    txt = REF_STARTER.read_text(encoding="utf-8", errors="replace")
    return {
        "mat_blank": extract_block(txt, r"^/MAT/LAW2/2\b"),
        "mat_tool": extract_block(txt, r"^/MAT/LAW1/1\b"),
        "fail": extract_block(txt, r"^/FAIL/GENE1/2\b"),
        "funct_punch": extract_block(txt, r"^/FUNCT/1\b"),
    }


# --------------------------------------------------------------------------
# 1次元の分割生成（細メッシュ帯 + 幾何級数グレーディング）
# --------------------------------------------------------------------------
def graded_axis(center: float, half_lo: float, half_hi: float,
                fine: float, band: float, coarse: float) -> list[float]:
    """center を挟む [center-half_lo, center+half_hi] を分割する座標列を返す。

    center から ±band は fine 一定。そこから外側は fine -> coarse へ幾何級数で粗くする。
    せん断帯だけを細かくし、遠方の要素数を抑えるため。
    """
    pts = [center]
    # 中央帯（両側）
    n_band = max(1, int(round(band / fine)))
    for i in range(1, n_band + 1):
        pts.append(center + i * fine)
        pts.append(center - i * fine)

    def extend(sign: int, limit: float):
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


def uniform_axis(lo: float, hi: float, size: float) -> list[float]:
    n = max(1, int(round((hi - lo) / size)))
    return [lo + (hi - lo) * i / n for i in range(n + 1)]


# --------------------------------------------------------------------------
# メッシュ生成
# --------------------------------------------------------------------------
class Mesh2D:
    """YZ平面のQUADメッシュ。節点は (y, z)、X は常に 0。"""

    def __init__(self) -> None:
        self.nodes: dict[int, tuple[float, float]] = {}
        self.quads: dict[int, tuple[int, int, int, int]] = {}
        self._nid = 0
        self._eid = 0
        self.parts: dict[int, list[int]] = {}

    def add_node(self, y: float, z: float) -> int:
        self._nid += 1
        self.nodes[self._nid] = (y, z)
        return self._nid

    def add_grid(self, ys: list[float], zs: list[float], part_id: int) -> dict:
        """格子状にQUADを張る。戻り値に境界の節点群を含める。"""
        grid: dict[tuple[int, int], int] = {}
        for j, z in enumerate(zs):
            for i, y in enumerate(ys):
                grid[(i, j)] = self.add_node(y, z)
        ids = self.parts.setdefault(part_id, [])
        for j in range(len(zs) - 1):
            for i in range(len(ys) - 1):
                # 反時計回り(YZ平面で見て)にすると法線が+X。/QUAD の要件。
                n1 = grid[(i, j)]
                n2 = grid[(i + 1, j)]
                n3 = grid[(i + 1, j + 1)]
                n4 = grid[(i, j + 1)]
                self._eid += 1
                self.quads[self._eid] = (n1, n2, n3, n4)
                ids.append(self._eid)
        return {
            "grid": grid,
            "top": [grid[(i, len(zs) - 1)] for i in range(len(ys))],
            "bottom": [grid[(i, 0)] for i in range(len(ys))],
            "left": [grid[(0, j)] for j in range(len(zs))],
            "right": [grid[(len(ys) - 1, j)] for j in range(len(zs))],
            "all": list(grid.values()),
        }


# --------------------------------------------------------------------------
# デック出力
# --------------------------------------------------------------------------
def fmt_nodes(mesh: Mesh2D) -> list[str]:
    out = ["/NODE"]
    for nid, (y, z) in mesh.nodes.items():
        # X=0 固定。2D は YZ 平面上でなければならない
        out.append(f"{i10(nid)}{f20(0.0)}{f20(y)}{f20(z)}")
    return out


def fmt_quads(mesh: Mesh2D) -> list[str]:
    out = []
    for pid, eids in sorted(mesh.parts.items()):
        out.append(f"/QUAD/{pid}")
        for eid in eids:
            n1, n2, n3, n4 = mesh.quads[eid]
            out.append(f"{i10(eid)}{i10(n1)}{i10(n2)}{i10(n3)}{i10(n4)}")
    return out


def fmt_grnod(gid: int, name: str, nodes: list[int]) -> list[str]:
    out = [f"/GRNOD/NODE/{gid}", name]
    uniq = sorted(set(nodes))
    for k in range(0, len(uniq), 10):
        out.append("".join(i10(n) for n in uniq[k:k + 10]))
    return out


def build(tag: str, shear_elem: float, band: float, coarse: float,
          clearance: float, tstop: float, eps_pmax: float | None = None,
          eps_eff: float | None = None, eps_s: float | None = None,
          volfrac: float | None = None,
          law2_eps_p_max: float | None = None) -> tuple[Path, Path]:
    ref = load_reference_cards()
    if any(v is not None for v in (eps_pmax, eps_eff, eps_s, volfrac)):
        ref["fail"] = override_gene1(ref["fail"], eps_pmax, eps_eff, eps_s, volfrac)
    if law2_eps_p_max is not None:
        ref["mat_blank"] = override_law2_epsmax(ref["mat_blank"], law2_eps_p_max)
    mesh = Mesh2D()

    # 切断線の位置。Y+ / Z+ 象限に置く（Altair 推奨）
    y_cut = BLANK_HALF_WIDTH
    z0 = 0.0
    z1 = THICKNESS

    # --- 材料(ブランク) ---
    ys = graded_axis(y_cut, BLANK_HALF_WIDTH, BLANK_HALF_WIDTH,
                     shear_elem, band, coarse)
    zs = uniform_axis(z0, z1, shear_elem)
    blank = mesh.add_grid(ys, zs, part_id=2)

    # --- 工具。粗メッシュで十分（弾性LAW1、変形は見ない） ---
    tool_elem = max(coarse, 50.0e-6)
    # パンチ: 切断線の左側、板の上
    punch = mesh.add_grid(uniform_axis(0.0, y_cut, tool_elem),
                          uniform_axis(z1, z1 + TOOL_DEPTH, tool_elem), part_id=1)
    # ダイ: 切断線の右側(隙間分ずらす)、板の下
    die = mesh.add_grid(uniform_axis(y_cut + clearance, 2 * y_cut, tool_elem),
                        uniform_axis(z0 - TOOL_DEPTH, z0, tool_elem), part_id=3)
    # ストリッパー: 切断線の右側、板の上（材料の浮きを押さえる）
    strip = mesh.add_grid(uniform_axis(y_cut + clearance, 2 * y_cut, tool_elem),
                          uniform_axis(z1, z1 + TOOL_DEPTH, tool_elem), part_id=4)

    L: list[str] = []
    L.append("#RADIOSS STARTER")
    L.append("/BEGIN")
    L.append(f"INC188_2D_{tag}")
    L.append(f"{i10(2022)}{i10(0)}")
    L.append(f"{'kg':>20}{'m':>20}{'s':>20}")
    L.append(f"{'kg':>20}{'m':>20}{'s':>20}")
    L.append("/TITLE")
    L.append(f"INC188 2D plane strain shear calibration ({tag})")

    # 平面ひずみ。N2D3D=2、X が平面ひずみ方向
    L.append("/ANALY")
    L.append("#    N2D3D             IPARITH")
    L.append(f"{i10(2)}          {i10(1)}")

    L.extend(fmt_nodes(mesh))
    L.extend(fmt_quads(mesh))

    # --- 材料・破断は3Dから引き写し ---
    L.append(ref["mat_tool"])
    L.append(ref["mat_blank"])
    L.append(ref["fail"])

    # --- プロパティ ---
    # 書式は3Dデックで実績のあるものと同一にする（タイトル + データ3行）。
    # 行数が足りないと Starter が「card is missing」で次のブロックを食い違って読む。
    for pid, name in ((1, "Tool_Solid_2D"), (2, "Blank_Solid_2D")):
        L.append(f"/PROP/SOLID/{pid}")
        L.append(name)
        L.append("#   Isolid    Ismstr                               Dn                Qa                Hm")
        # 2D では Isolid=1 が使えず Starter が 2 へ強制する(WARNING 321)。最初から2にする。
        L.append(f"{i10(2)}{i10(-1)}{i10(0)}{i10(0)}{i10(2)}{i10(0)}{i10(3)}{i10(1)}{f20(0.1)}")
        L.append(f"{i10(0)}{i10(0)}{f20(0.1)}{i10(0)}{i10(0)}")
        L.append(f"{i10(0)}{i10(0)}{i10(0)}{i10(0)}{i10(0)}")

    # --- パート ---
    for pid, pname, prop, mat in ((1, "Punch_2D", 1, 1), (2, "Blank_2D", 2, 2),
                                  (3, "Die_2D", 1, 1), (4, "Stripper_2D", 1, 1)):
        L.append(f"/PART/{pid}")
        L.append(pname)
        L.append("#    Prop_ID     Mat_ID")
        L.append(f"{i10(prop)}{i10(mat)}")

    # --- 節点群 ---
    # TYPE5 の第1引数は grnd_IDs（節点群）であってサーフェスではない。
    # ここをサーフェスIDにすると REFERENCE TO UNDEFINED GROUP ID で落ちる。
    L.extend(fmt_grnod(200, "Blank_Nodes", blank["all"]))
    L.extend(fmt_grnod(100, "Punch_Nodes", punch["all"]))
    L.extend(fmt_grnod(300, "Die_Nodes", die["all"]))
    L.extend(fmt_grnod(400, "Stripper_Nodes", strip["all"]))
    # 材料の左右端は面内固定（3Dの外周Z固定が真因2だったので、Zは拘束しない）
    L.extend(fmt_grnod(500, "Blank_Edges_Y", blank["left"] + blank["right"]))

    # --- 接触面 ---
    for sid, pid in ((1, 1), (2, 2), (3, 3), (4, 4)):
        L.append(f"/SURF/PART/EXT/{sid}00/0")
        L.append(f"Surf_Part_{pid}")
        L.append(f"{i10(pid)}")

    # --- パンチ変位（3Dと同一のクランク曲線） ---
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

    # 工具は面内で動かさない / ダイとストリッパーは固定
    for iid, gid, name in ((2, 100, "Punch_Fixed_Y"), (3, 300, "Die_Fixed_Y"),
                           (4, 400, "Stripper_Fixed_Y")):
        L.append(f"/IMPVEL/{iid}")
        L.append(name)
        L.append("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe")
        L.append(f"{i10(2)}{'Y':>10}{i10(0)}{i10(0)}{i10(gid)}{i10(0)}{i10(0)}")
        L.append("#             Ascale_x            Fscale_y              Tstart               Tstop")
        L.append(f"{f20(1.0)}{f20(1.0)}{f20(0.0)}{f20(1.0e30)}")
    for iid, gid, name in ((5, 300, "Die_Fixed_Z"), (6, 400, "Stripper_Fixed_Z")):
        L.append(f"/IMPVEL/{iid}")
        L.append(name)
        L.append("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe")
        L.append(f"{i10(2)}{'Z':>10}{i10(0)}{i10(0)}{i10(gid)}{i10(0)}{i10(0)}")
        L.append("#             Ascale_x            Fscale_y              Tstart               Tstop")
        L.append(f"{f20(1.0)}{f20(1.0)}{f20(0.0)}{f20(1.0e30)}")

    # --- 接触 ---
    # TYPE7 は 2D 非対応。Starter が明示的に拒否する:
    #   "INTERFACE TYPE7 IS NOT COMPATIBLE WITH 2D ANALYSIS." (ERROR 2097)
    # 2D で使えるのは TYPE3 / TYPE5。ここは汎用接触の TYPE5 を使う。
    # 書式は hm_cfg_files/config/CFG/radioss2018/INTER/inter_type5.cfg (データ4行)。
    for iid, sec, mst, label in ((1, 200, 100, "Blank_to_Punch"),
                                 (2, 200, 300, "Blank_to_Die"),
                                 (3, 200, 400, "Blank_to_Stripper")):
        L.append(f"/INTER/TYPE5/{iid}")
        L.append(label)
        L.append("# grnd_IDs  surf_IDm                                              Ibag      Idel")
        L.append(f"{i10(sec)}{i10(mst)}{'':>40}{i10(0)}{i10(0)}")
        L.append("#              Stfac                Fric                 Gap              Tstart               Tstop")
        L.append(f"{f20(1.0)}{f20(0.1)}{f20(0.0)}{f20(0.0)}{f20(1.0e30)}")
        L.append("#      IBC                 IRm    Inacti")
        L.append(f"{'':>7}{0}{0}{0}{'':>10}{i10(0)}{i10(0)}")
        L.append("#    Ifric    Ifiltr               Xfreq             sens_ID               Ptlim")
        L.append(f"{i10(0)}{i10(0)}{f20(0.0)}{'':>10}{i10(0)}{f20(0.0)}")

    # --- 時刻歴: 荷重-ストローク校正に必須 ---
    L.append("/TH/INTER/1")
    L.append("Contact_Forces")
    L.append("#      var")
    L.append("DEF")
    L.append(f"{i10(1)}{i10(2)}{i10(3)}")
    L.append("/TH/NODE/2")
    L.append("Punch_Stroke")
    L.append("DEF")
    L.append(f"{i10(punch['all'][0])}")

    L.append("/END")

    starter = TRIALS / f"INC188_2D_{tag}_0000.rad"
    starter.write_text("\n".join(L) + "\n", encoding="utf-8")

    engine = TRIALS / f"INC188_2D_{tag}_0001.rad"
    engine.write_text("\n".join([
        f"/RUN/INC188_2D_{tag}/1",
        f"{f20(tstop)}",
        "/DT/NODA/0",
        f"{f20(0.9)}{f20(0.0)}",
        "/RFILE/50000",
        "/TFILE/4",
        f"{f20(1.0e-5)}",
        "/ANIM/DT",
        f"{f20(0.0)}{f20(4.0e-4)}",
        "/ANIM/ELEM/EPSP",
        "/ANIM/ELEM/VONM",
        "/ANIM/VECT/DISP",
        "/END",
        "",
    ]), encoding="utf-8")

    print(f"[2D] 節点 {len(mesh.nodes)} / QUAD {len(mesh.quads)}")
    for pid, eids in sorted(mesh.parts.items()):
        print(f"[2D]   part {pid}: {len(eids)} 要素")
    print(f"[2D] せん断帯要素 {shear_elem*1e6:.1f} um / 板厚方向 {len(zs)-1} 分割")
    print(f"[2D] ダイ隙間 {clearance*1e6:.1f} um / tstop {tstop:g} s")
    print(f"[2D] starter -> {starter}")
    print(f"[2D] engine  -> {engine}")
    return starter, engine


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="INC-188 2D平面ひずみ校正モデルを生成")
    ap.add_argument("--tag", default="2DA")
    ap.add_argument("--shear-elem", type=float, default=DEFAULT_SHEAR_ELEM,
                    help="せん断帯の要素寸法[m] 既定10e-6 (文献 PMC11012880 と同じ)")
    ap.add_argument("--band", type=float, default=DEFAULT_BAND, help="細メッシュ帯の半幅[m]")
    ap.add_argument("--coarse", type=float, default=DEFAULT_COARSE, help="遠方の最大要素寸法[m]")
    ap.add_argument("--clearance", type=float, default=DEFAULT_CLEARANCE, help="ダイ隙間[m]")
    ap.add_argument("--tstop", type=float, default=3.2402e-3,
                    help="終了時刻[s] 既定は引き継ぎ§5の推奨値")
    ap.add_argument("--eps-pmax", type=float, default=None,
                    help="塑性ひずみ破断しきい値。3Dデックは0(無効)")
    ap.add_argument("--eps-eff", type=float, default=None, help="実効ひずみしきい値")
    ap.add_argument("--eps-s", type=float, default=None, help="せん断ひずみしきい値")
    ap.add_argument("--volfrac", type=float, default=None,
                    help="固体要素の削除体積率")
    ap.add_argument("--law2-eps-p-max", type=float, default=None,
                    help="/MAT/LAW2 の EPS_p_max。3Dデックは10.0(実質無効)")
    a = ap.parse_args(argv)
    build(a.tag, a.shear_elem, a.band, a.coarse, a.clearance, a.tstop,
          a.eps_pmax, a.eps_eff, a.eps_s, a.volfrac, a.law2_eps_p_max)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
