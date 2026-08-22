# -*- coding: utf-8 -*-
"""PANEL4MM フル3D: Sol2SPH を切断エッジ近傍のみに限定し、計算コストを抑える。
2026-08-20 導入。

## 背景

build_panel4mm_sol2sph.py(PANEL4MM_P3)でブランク全体(461,052要素)へ
Sol2SPHを一律適用したところ、NUMSPH(潜在SPH粒子数)=1,844,208となり、
1サイクルあたり2.9秒(Sol2SPHなしのPANEL4MM_P2の0.122秒の約24倍)、
推定完走時間が約14日という計算不能な結果になった。詳細:
finding_sol2sphは潜在的sph粒子数に比例してオーバーヘッドが増大_全パネル規模.md

Sol2SPHの近傍探索コストは実際に変換される粒子数でなく、変換されうる
全要素数(NUMSPH)に比例して増大すると推定される。実際に破断が起きるのは
切断エッジ近傍のごく一部(slice3dでは4,896要素中57件=1.2%)なので、
ブランクを「エッジ近傍(Sol2SPH適用)」「遠方(通常FEM)」の2パートに分割し、
Sol2SPHの対象要素数を削減する。

## 近傍判定

各パンチ(TAG_PUNCH内の4形状: V字ノッチ・矩形・トリム・丸穴)の節点群を
XY平面へ投影し、ブランク各要素の重心からの最近傍距離が閾値未満なら
「エッジ近傍」とする。パンチ節点は境界だけでなく内部も含むため厳密な
輪郭距離ではないが、実用上十分な近似(実装コストとのトレードオフ、
2026-08-20 ユーザー承認済み)。

usage:
  python scripts/build_panel4mm_sol2sph_local.py --tag P4 --near-thresh 1.0e-3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import MultiPoint

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023
sys.path.insert(0, str(Path(__file__).parent))

from build_panel4mm_3d_blanking import (  # noqa: E402
    mesh_group, tetra_prop, remap_type25, fmt_grnod, extract_block, override_gene1,
    i10, f20, TAG_BLANK, TAG_DIE, TAG_STRIPPER, TAG_PUNCH, MM, TOOL_GAP,
    REF_STARTER, TRIALS, DEFAULT_BLANK_ELEM, DEFAULT_TOOL_ELEM, DEFAULT_STROKE,
    DEFAULT_SPEED, DEFAULT_GAP_MAX, DEFAULT_STFAC, DEFAULT_NSTEP, STRIPPER_CLOSE_T,
)
from build_panel4mm_sol2sph import DT_MIN  # noqa: E402

NDIR = 2
SPH_PART_ID = 7
SPH_PROP_ID = 7
SPH_MAT_ID = 3
NEAR_PART_ID = 2      # Blank_Near(Sol2SPH適用)
FAR_PART_ID = 5        # Blank_Far(通常FEM、GENE1削除のみ)
FAR_PROP_ID = 5
FAR_MAT_ID = 4          # Blank_Far専用: 同一物理特性・低いEps_eff(暴走防止)


def build(tag: str, blank_elem: float, tool_elem: float, stroke: float, speed: float,
          gap_max: float, stfac: float, nstep: int, eps_eff: float, eps_s: float,
          near_thresh: float, ndir: int, retract_frac: float, settle_frac: float,
          far_eps_eff: float = 0.3, vdef_min: float = 0.0, vdef_max: float = 0.0,
          asp_max: float = 0.0, col_min: float = 0.0):
    ref_txt = REF_STARTER.read_text(encoding="utf-8", errors="replace")

    def make_fail_block(mat_id: int, eps_eff_v: float, eps_s_v: float) -> str:
        block = override_gene1(extract_block(ref_txt, r"^/FAIL/GENE1/2\b"), nstep)
        lines = block.splitlines()
        lines[0] = f"/FAIL/GENE1/{mat_id}"
        assert "Eps_eff" in lines[5], lines[5]
        lines[6] = f"{i10(0)}{f20(0.0)}{f20(0.0)}{f20(eps_eff_v)}{f20(0.0)}"
        assert "Eps_s" in lines[7], lines[7]
        lines[8] = f"{f20(0.0)}{f20(eps_s_v)}{i10(0)}{i10(0)}{i10(0)}"
        return "\n".join(lines)

    # 2026-08-21 実証済みバグ対策: Blank_Near/Farが同一MAT_ID=2・同一Eps_eff=0.85
    # を共有していたところ、KISTEC比較に無関係な遠方領域(Sol2SPH非適用)で
    # 高いEps_effのまま連鎖破断が起きSIGSEGVでクラッシュした(P4c実測)。
    # 遠方専用にFAR_MAT_ID=4・より低いfar_eps_effを割り当て、早期安全側で
    # 削除させることで暴走を防ぐ。近傍(Sol2SPH保護域)はeps_effのまま維持。
    fail_near = make_fail_block(2, eps_eff, eps_s)
    fail_far = make_fail_block(FAR_MAT_ID, far_eps_eff, eps_s)

    mat_blank_block = extract_block(ref_txt, r"^/MAT/LAW2/2\b")
    mat_far_data = mat_blank_block.splitlines()[2:]
    mat_far_dup = [f"/MAT/LAW2/{FAR_MAT_ID}", "MR536_H34_AA5052_Far_lowEpsEff"] + mat_far_data

    ref = {
        "mat_blank": mat_blank_block,
        "mat_far": mat_far_dup,
        "mat_tool": extract_block(ref_txt, r"^/MAT/LAW1/1\b"),
        "fail": fail_near,
        "fail_far": fail_far,
        "inter1": extract_block(ref_txt, r"^/INTER/TYPE25/1\b"),
        "inter2": extract_block(ref_txt, r"^/INTER/TYPE25/2\b"),
        "inter3": extract_block(ref_txt, r"^/INTER/TYPE25/3\b"),
    }
    mat_data = ref["mat_blank"].splitlines()[2:]
    mat_dup = [f"/MAT/LAW2/{SPH_MAT_ID}", "MR536_H34_AA5052_SPH_no_fail"] + mat_data

    blank_dz = -(0.6 - 0.5 - TOOL_GAP / MM)

    print("[mesh] 材料を融合してメッシュ中...")
    c_blank, t_blank = mesh_group(TAG_BLANK, blank_elem / MM, fuse=True,
                                  add_slug=True, dz_mm=blank_dz)
    print(f"[mesh]   材料 TET4={len(t_blank):,}")

    print("[mesh] Punch形状ごとに輪郭(concave hull)を抽出中...")
    # パンチ内部点への距離だと「フラット面の下」まで近傍扱いになり絞り込め
    # ない(閾値1mmで69.7%が近傍という実測あり)。各パンチ形状の concave hull
    # 境界線への距離で判定し、実際の切断エッジ近傍だけに限定する。
    boundaries = []
    for t in TAG_PUNCH:
        c, _ = mesh_group([t], tool_elem / MM, fuse=False, add_slug=False)
        pts = [(v[0] * MM, v[1] * MM) for v in c.values()]
        hull = shapely.concave_hull(MultiPoint(pts), ratio=0.3)
        boundaries.append(hull.boundary if hull.geom_type == "Polygon" else hull)

    blank_ids = sorted(c_blank.keys())
    idx_of = {n: k for k, n in enumerate(blank_ids)}
    coords_m = np.array([(c_blank[n][0] * MM, c_blank[n][1] * MM) for n in blank_ids])
    centroids = np.array([coords_m[[idx_of[int(v)] for v in tet]].mean(axis=0)
                          for tet in t_blank])
    cent_pts = shapely.points(centroids)
    dist = np.full(len(centroids), np.inf)
    for b in boundaries:
        dist = np.minimum(dist, shapely.distance(cent_pts, b))
    near_mask = dist < near_thresh
    t_near = t_blank[near_mask]
    t_far = t_blank[~near_mask]
    print(f"[split] エッジ近傍(閾値{near_thresh*1e6:.0f}um, 輪郭距離): {len(t_near):,} / "
          f"遠方: {len(t_far):,} (近傍比率 {near_mask.mean()*100:.1f}%)")

    groups = [("Blank_Near", NEAR_PART_ID, c_blank, t_near),
              ("Blank_Far", FAR_PART_ID, c_blank, t_far)]
    for name, pid, tags in (("Die", 1, TAG_DIE), ("Stripper", 3, TAG_STRIPPER),
                            ("Punch", 4, TAG_PUNCH)):
        print(f"[mesh] {name} をメッシュ中...")
        c, t = mesh_group(tags, tool_elem / MM, fuse=False, add_slug=False)
        print(f"[mesh]   {name} TET4={len(t):,}")
        groups.append((name, pid, c, t))

    nodes: dict[int, tuple[float, float, float]] = {}
    part_elems: dict[int, list[tuple[int, tuple[int, int, int, int]]]] = {}
    part_nodes: dict[int, list[int]] = {}
    nid = 0
    eid = 0
    remap_blank: dict[int, int] | None = None
    for name, pid, coord, tets in groups:
        if name in ("Blank_Near", "Blank_Far"):
            # 近傍/遠方は同一メッシュ(c_blank)を共有するので節点remapも共有する。
            if remap_blank is None:
                remap_blank = {}
                for old, xyz in coord.items():
                    nid += 1
                    remap_blank[old] = nid
                    nodes[nid] = (xyz[0] * MM, xyz[1] * MM, xyz[2] * MM)
            remap = remap_blank
        else:
            remap = {}
            for old, xyz in coord.items():
                nid += 1
                remap[old] = nid
                nodes[nid] = (xyz[0] * MM, xyz[1] * MM, xyz[2] * MM)
        used_nodes = set()
        el = []
        for t in tets:
            eid += 1
            nn = tuple(remap[int(v)] for v in t)
            el.append((eid, nn))
            used_nodes.update(nn)
        part_elems[pid] = el
        part_nodes[pid] = sorted(used_nodes)

    t_stop_orig = stroke / speed
    t_retract_done = t_stop_orig + t_stop_orig * retract_frac
    t_final = t_retract_done + t_stop_orig * settle_frac

    L: list[str] = [
        "#RADIOSS STARTER", "/BEGIN", f"PANEL4MM_{tag}",
        # 2026-08-21 実証済み: radioss2022形式の/PROP/SOLIDは
        # "deltaT_min(f20) Istrain(i10) Imod(i10)"の3項目(40文字)であり、
        # Vdef_min/Vdef_max/ASP_max/COL_minは存在しない(OpenRadiossソース
        # starter/source/properties/solid/hm_read_prop14.F + hm_cfg_files/
        # config/CFG/radioss2022/PROP/prop_p14_solid.cfg で確認)。これらの
        # フィールドはradioss2023形式で新設され、5項目(f20×5=100文字)
        # "deltaT_min vdef_min vdef_max ASP_max COL_min"になる
        # (radioss2023/PROP/prop_p14_solid.cfgで確認)。幾何品質トリガーを
        # 使うにはバージョンを2023へ上げる必要がある。
        f"{i10(2023)}{i10(0)}",
        f"{'kg':>20}{'m':>20}{'s':>20}",
        f"{'kg':>20}{'m':>20}{'s':>20}",
        "/TITLE", f"Panel 4mm ASSY 3D blanking ({tag}) - Sol2SPH local to edges",
        "/ANALY", "#    N2D3D             IPARITH", f"{i10(0)}          {i10(1)}",
        "/NODE",
    ]
    for n, (x, y, z) in nodes.items():
        L.append(f"{i10(n)}{f20(x)}{f20(y)}{f20(z)}")

    for pid in (NEAR_PART_ID, FAR_PART_ID, 1, 3, 4):
        L.append(f"/TETRA4/{pid}")
        for e, nn in part_elems[pid]:
            L.append(i10(e) + "".join(i10(v) for v in nn))

    L.append(ref["mat_tool"])
    L.append(ref["mat_blank"])
    L.extend(mat_dup)
    L.extend(ref["mat_far"])
    L.append(ref["fail"])
    L.append(ref["fail_far"])
    L.extend(tetra_prop(1, "Tool_Solid"))
    near_prop = tetra_prop(NEAR_PART_ID, "Blank_Solid_Near")
    # radioss2023形式で実証確認済みの正しい配置(2026-08-21):
    #   5行目(index5): deltaT_min, vdef_min, vdef_max, ASP_max, COL_min (f20x5)
    #   6行目(新規):   Ndir, SPHPART_ID (i10x2のみ。Icontrolはこの行に無い)
    # Isolid=1は既にSol2SPHの要件(1/2/24)を満たすため変更不要(build_inc188と
    # 異なりPANEL4MM系のtetra_propは元からIsolid=1)。
    if any(v > 0 for v in (vdef_min, vdef_max, asp_max, col_min)):
        near_prop[5] = f"{f20(0.0)}{f20(vdef_min)}{f20(vdef_max)}{f20(asp_max)}{f20(col_min)}"
    near_prop.append(f"{i10(ndir)}{i10(SPH_PART_ID)}")
    L.extend(near_prop)
    L.extend(tetra_prop(FAR_PROP_ID, "Blank_Solid_Far"))
    h = 1.5 * blank_elem / ndir
    L += [
        f"/PROP/TYPE34/{SPH_PROP_ID}", "Sol2SPH_Particles",
        "#                 Mp                Beta               Alpha            Alpha_cs    Skew_ID    h_1D",
        f"{f20(0.0)}{f20(0.0)}{f20(0.0)}{f20(0.0)}{i10(0)}{f20(0.0)}",
        "#     order                   h              Xi_stab                Hmin                Hmax",
        f"{i10(0)}{f20(h)}{f20(0.3)}{f20(0.0)}{f20(0.0)}",
        "#               Hcst", f"{f20(0.0)}",
    ]

    part_defs = [(1, "Die", 1, 1), (NEAR_PART_ID, "Blank_Near", NEAR_PART_ID, 2),
                (3, "Stripper", 1, 1), (4, "Punch", 1, 1),
                (FAR_PART_ID, "Blank_Far", FAR_PROP_ID, FAR_MAT_ID),
                (SPH_PART_ID, "Sol2SPH_Blank_Part", SPH_PROP_ID, SPH_MAT_ID)]
    for pid, pname, prop, mat in part_defs:
        L.append(f"/PART/{pid}")
        L.append(pname)
        L.append("#    Prop_ID     Mat_ID")
        L.append(f"{i10(prop)}{i10(mat)}")

    blank_all_nodes = sorted(set(part_nodes[NEAR_PART_ID]) | set(part_nodes[FAR_PART_ID]))
    L.extend(fmt_grnod(100, "Punch_Nodes", part_nodes[4]))
    L.extend(fmt_grnod(200, "Blank_Nodes", blank_all_nodes))
    L.extend(fmt_grnod(300, "Die_Nodes", part_nodes[1]))
    L.extend(fmt_grnod(400, "Stripper_Nodes", part_nodes[3]))

    for sid, pid in ((1, 1), (3, 3), (4, 4)):
        L.append(f"/SURF/PART/EXT/{sid}00/0")
        L.append(f"Surf_Part_{pid}")
        L.append(f"{i10(pid)}")
    L.append("/SURF/PART/EXT/200/0")
    L.append("Surf_Blank")
    L.append(f"{i10(NEAR_PART_ID)}")
    L.append(f"{i10(FAR_PART_ID)}")

    # retract_frac=settle_frac=0 の場合、t_stop_orig=t_retract_done=t_final と
    # なり同一時刻に異なるY値を持つ不正な関数点(重複)ができてしまう。切断のみ
    # 検証(2026-08-20 ユーザー方針: まず短縮版で健全性を確認してから引き抜き
    # を追加)ではこの3点構成(引き抜きなし)にフォールバックする。
    cutting_only = retract_frac <= 0 and settle_frac <= 0
    if cutting_only:
        L += ["/FUNCT/1", "Punch_Stroke", "#                  X                   Y",
              f"{f20(0.0)}{f20(0.0)}", f"{f20(t_stop_orig)}{f20(-stroke)}",
              f"{f20(t_stop_orig*10)}{f20(-stroke)}"]
        strip_close = (1.2 - (1.1 + blank_dz)) * MM - TOOL_GAP
        L += ["/FUNCT/2", "Stripper_Close", "#                  X                   Y",
              f"{f20(0.0)}{f20(0.0)}", f"{f20(STRIPPER_CLOSE_T)}{f20(-strip_close)}",
              f"{f20(t_stop_orig*10)}{f20(-strip_close)}"]
        L += ["/FUNCT/3", "Zero", "#                  X                   Y",
              f"{f20(0.0)}{f20(0.0)}", f"{f20(t_stop_orig*10)}{f20(0.0)}"]
        t_final = t_stop_orig
    else:
        L += ["/FUNCT/1", "Punch_Stroke", "#                  X                   Y",
              f"{f20(0.0)}{f20(0.0)}", f"{f20(t_stop_orig)}{f20(-stroke)}",
              f"{f20(t_retract_done)}{f20(0.0)}", f"{f20(t_final)}{f20(0.0)}"]
        strip_close = (1.2 - (1.1 + blank_dz)) * MM - TOOL_GAP
        L += ["/FUNCT/2", "Stripper_Close", "#                  X                   Y",
              f"{f20(0.0)}{f20(0.0)}", f"{f20(STRIPPER_CLOSE_T)}{f20(-strip_close)}",
              f"{f20(t_retract_done)}{f20(0.0)}", f"{f20(t_final)}{f20(0.0)}"]
        L += ["/FUNCT/3", "Zero", "#                  X                   Y",
              f"{f20(0.0)}{f20(0.0)}", f"{f20(t_final)}{f20(0.0)}"]

    for iid, fid, gid, name in ((1, 1, 100, "Punch_Stroke_Z"),
                                (2, 2, 400, "Stripper_Close_Z")):
        L += [f"/IMPDISP/{iid}", name,
              "#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor",
              f"{i10(fid)}{'Z':>10}{i10(0)}{i10(0)}{i10(gid)}{i10(0)}",
              "#             Ascale_x            Fscale_y              Tstart               Tstop",
              f"{f20(1.0)}{f20(1.0)}{f20(0.0)}{f20(1.0e30)}"]

    imp = 3
    for gid, d, name in ((100, "X", "Punch_X"), (100, "Y", "Punch_Y"),
                         (300, "X", "Die_X"), (300, "Y", "Die_Y"), (300, "Z", "Die_Z"),
                         (400, "X", "Stripper_X"), (400, "Y", "Stripper_Y")):
        L += [f"/IMPVEL/{imp}", name,
              "#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe",
              f"{i10(3)}{d:>10}{i10(0)}{i10(0)}{i10(gid)}{i10(0)}{i10(0)}",
              "#             Ascale_x            Fscale_y              Tstart               Tstop",
              f"{f20(1.0)}{f20(1.0)}{f20(0.0)}{f20(1.0e30)}"]
        imp += 1

    for iid, s1, s2, label in ((1, 100, 200, "Punch_Blank_Contact"),
                               (2, 300, 200, "Die_Blank_Contact"),
                               (3, 400, 200, "Stripper_Blank_Contact")):
        L.append(remap_type25(ref[f"inter{iid}"], iid, label, s1, s2, gap_max, stfac))

    L.append("/END")

    starter = TRIALS / f"PANEL4MM_{tag}_0000.rad"
    starter.write_text("\n".join(L) + "\n", encoding="utf-8")
    engine = TRIALS / f"PANEL4MM_{tag}_0001.rad"
    engine.write_text("\n".join([
        f"/RUN/PANEL4MM_{tag}/1", f"{f20(t_final)}", "/DT/NODA/CST2/0",
        f"{f20(0.9)}{f20(DT_MIN)}", "/RFILE/50000", "/TFILE/4", f"{f20(1.0e-6)}",
        "/ANIM/DT", f"{f20(0.0)}{f20(t_final / 60)}",
        "/ANIM/ELEM/EPSP", "/ANIM/ELEM/VONM",
        # 2026-08-23: KISTEC実測残留応力(-5.49〜+9.21MPa、負値含む特定方向の
        # 垂直応力成分)との比較にはVONM(常に正のスカラー)は使えない。
        # 符号付き応力テンソル成分を出力する。
        "/ANIM/ELEM/SIGX", "/ANIM/ELEM/SIGY", "/ANIM/ELEM/SIGZ",
        "/ANIM/VECT/DISP", "/END", "",
    ]), encoding="utf-8")

    print(f"\n[deck] 節点 {len(nodes):,}")
    print(f"[deck] 引き抜き: t_stop_orig={t_stop_orig*1e3:.3f}ms -> "
          f"t_retract_done={t_retract_done*1e3:.3f}ms -> t_final={t_final*1e3:.3f}ms")
    print(f"[deck] starter -> {starter}")
    print(f"[deck] engine  -> {engine}")
    return starter, engine


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--blank-elem", type=float, default=DEFAULT_BLANK_ELEM)
    ap.add_argument("--tool-elem", type=float, default=DEFAULT_TOOL_ELEM)
    ap.add_argument("--stroke", type=float, default=DEFAULT_STROKE)
    ap.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    ap.add_argument("--gap-max", type=float, default=DEFAULT_GAP_MAX, dest="gap_max")
    ap.add_argument("--stfac", type=float, default=DEFAULT_STFAC)
    ap.add_argument("--nstep", type=int, default=DEFAULT_NSTEP)
    ap.add_argument("--eps-eff", type=float, default=0.85)
    ap.add_argument("--eps-s", type=float, default=1.0)
    ap.add_argument("--near-thresh", type=float, default=1.0e-3,
                    help="切断エッジ近傍とみなすXY距離[m](既定1mm)")
    ap.add_argument("--ndir", type=int, default=NDIR)
    ap.add_argument("--retract-frac", type=float, default=1.0)
    ap.add_argument("--settle-frac", type=float, default=2.0)
    ap.add_argument("--far-eps-eff", type=float, default=0.3,
                    help="遠方(Sol2SPH非適用)領域専用の安全側Eps_eff")
    ap.add_argument("--vdef-min", type=float, default=0.0,
                    help="V/V0がこれ未満で先行SPH変換(radioss2023形式限定,0=無効)")
    ap.add_argument("--vdef-max", type=float, default=0.0,
                    help="V/V0がこれ超で先行SPH変換(radioss2023形式限定,0=無効)")
    ap.add_argument("--asp-max", type=float, default=0.0,
                    help="最大辺長/最小辺長がこれ超で先行SPH変換(radioss2023形式限定,0=無効)")
    ap.add_argument("--col-min", type=float, default=0.0,
                    help="最小辺長/最大辺長がこれ未満で先行SPH変換(radioss2023形式限定,0=無効)")
    a = ap.parse_args()
    build(a.tag, a.blank_elem, a.tool_elem, a.stroke, a.speed, a.gap_max, a.stfac,
          a.nstep, a.eps_eff, a.eps_s, a.near_thresh, a.ndir, a.retract_frac, a.settle_frac,
          a.far_eps_eff, a.vdef_min, a.vdef_max, a.asp_max, a.col_min)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
