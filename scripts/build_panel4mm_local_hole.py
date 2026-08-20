# -*- coding: utf-8 -*-
"""PANEL4MM: KISTEC実測点(丸穴+V字ノッチ周辺)に対象を絞ったローカル解析。
2026-08-20 導入。

## 背景

build_panel4mm_sol2sph_local.py(PANEL4MM_P4)でパンチ輪郭からの距離で
Sol2SPH対象をエッジ近傍(閾値150um)に絞ったが、NUMSPH=339,624で推定
完走時間2.9日と依然として非実用的だった。

KISTEC実測(試験結果_ミツイ精密_20260630.pdf)の測定点Point A-Hは、
顕微鏡写真からV字ノッチパンチ(tag=10)と丸パンチ(tag=13、丸穴中心と
完全一致)の周辺に位置することが確認できた(tag10とtag13の中心間距離
4.5mm、他パンチtag11/12は同程度の距離だが写真に写っていない)。
KISTEC実測との比較が目的である以上、対象を丸穴中心周辺のローカル
領域(既定±10mm)・関連パンチ2個(tag10,13)のみに縮小する。

## 実装方針

ブランクは全体(46万要素)を一度メッシュしてから、丸穴中心を基準とした
ローカルボックスで要素を絞り込む(gmshでの幾何学的クリップより単純)。
ダイ・ストリッパーは全体形状を保持する(ローカル材料片への支持・接触面
としての実在性を保つため。ローカル材料片だけを浮遊させると境界条件が
非物理的になる)。

## 忠実度の制約(重要)

材料をローカルにクリップすると、実際にはボックス外へ連続している板と
の接続剛性が失われる。ボックスを機能寸法(パンチ形状のスケール)より
十分大きく取ることで影響を緩和しているが、境界近くの応力は実際より
柔らかく評価される可能性がある(報告時に明記すること)。

usage:
  python scripts/build_panel4mm_local_hole.py --tag P5 --box-margin 10e-3
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
    i10, f20, TAG_BLANK, TAG_DIE, TAG_STRIPPER, MM, TOOL_GAP, HOLE_CENTER,
    REF_STARTER, TRIALS, DEFAULT_BLANK_ELEM, DEFAULT_TOOL_ELEM, DEFAULT_STROKE,
    DEFAULT_SPEED, DEFAULT_GAP_MAX, DEFAULT_STFAC, DEFAULT_NSTEP, STRIPPER_CLOSE_T,
)
from build_panel4mm_sol2sph import DT_MIN  # noqa: E402

LOCAL_PUNCH_TAGS = [10, 13]  # V字ノッチ + 丸パンチ(KISTEC測定点周辺)
NDIR = 2
SPH_PART_ID = 7
SPH_PROP_ID = 7
SPH_MAT_ID = 3
NEAR_PART_ID = 2
FAR_PART_ID = 5
FAR_PROP_ID = 5


def build(tag: str, blank_elem: float, tool_elem: float, stroke: float, speed: float,
          gap_max: float, stfac: float, nstep: int, eps_eff: float, eps_s: float,
          near_thresh: float, box_margin: float, ndir: int,
          retract_frac: float, settle_frac: float):
    ref_txt = REF_STARTER.read_text(encoding="utf-8", errors="replace")
    fail_block = override_gene1(extract_block(ref_txt, r"^/FAIL/GENE1/2\b"), nstep)
    fail_lines = fail_block.splitlines()
    assert "Eps_eff" in fail_lines[5], fail_lines[5]
    fail_lines[6] = f"{i10(0)}{f20(0.0)}{f20(0.0)}{f20(eps_eff)}{f20(0.0)}"
    assert "Eps_s" in fail_lines[7], fail_lines[7]
    fail_lines[8] = f"{f20(0.0)}{f20(eps_s)}{i10(0)}{i10(0)}{i10(0)}"
    fail_block = "\n".join(fail_lines)

    ref = {
        "mat_blank": extract_block(ref_txt, r"^/MAT/LAW2/2\b"),
        "mat_tool": extract_block(ref_txt, r"^/MAT/LAW1/1\b"),
        "fail": fail_block,
        "inter1": extract_block(ref_txt, r"^/INTER/TYPE25/1\b"),
        "inter2": extract_block(ref_txt, r"^/INTER/TYPE25/2\b"),
        "inter3": extract_block(ref_txt, r"^/INTER/TYPE25/3\b"),
    }
    mat_data = ref["mat_blank"].splitlines()[2:]
    mat_dup = [f"/MAT/LAW2/{SPH_MAT_ID}", "MR536_H34_AA5052_SPH_no_fail"] + mat_data

    blank_dz = -(0.6 - 0.5 - TOOL_GAP / MM)

    print("[mesh] 材料を融合してメッシュ中(全体)...")
    c_blank_full, t_blank_full = mesh_group(TAG_BLANK, blank_elem / MM, fuse=True,
                                            add_slug=True, dz_mm=blank_dz)
    print(f"[mesh]   材料(全体) TET4={len(t_blank_full):,}")

    hx, hy = HOLE_CENTER
    bm = box_margin / MM
    blank_ids_all = sorted(c_blank_full.keys())
    idx_of = {n: k for k, n in enumerate(blank_ids_all)}
    coords_m_all = np.array([(c_blank_full[n][0], c_blank_full[n][1]) for n in blank_ids_all])
    cent_all = np.array([coords_m_all[[idx_of[int(v)] for v in tet]].mean(axis=0)
                         for tet in t_blank_full])
    in_box = ((np.abs(cent_all[:, 0] - hx) < bm) & (np.abs(cent_all[:, 1] - hy) < bm))
    t_blank = t_blank_full[in_box]
    used = {int(v) for v in t_blank.reshape(-1)}
    c_blank = {k: v for k, v in c_blank_full.items() if k in used}
    print(f"[local] 丸穴中心({hx:.3f},{hy:.3f})から±{box_margin*1e3:g}mm: "
          f"{len(t_blank):,} / {len(t_blank_full):,} 要素 "
          f"({len(t_blank)/len(t_blank_full)*100:.1f}%)")

    print("[mesh] Punch形状(V字ノッチ+丸)ごとに輪郭を抽出中...")
    boundaries = []
    for t in LOCAL_PUNCH_TAGS:
        c, _ = mesh_group([t], tool_elem / MM, fuse=False, add_slug=False)
        pts = [(v[0] * MM, v[1] * MM) for v in c.values()]
        hull = shapely.concave_hull(MultiPoint(pts), ratio=0.3)
        boundaries.append(hull.boundary if hull.geom_type == "Polygon" else hull)

    blank_ids = sorted(c_blank.keys())
    idx_of2 = {n: k for k, n in enumerate(blank_ids)}
    coords_m = np.array([(c_blank[n][0] * MM, c_blank[n][1] * MM) for n in blank_ids])
    centroids = np.array([coords_m[[idx_of2[int(v)] for v in tet]].mean(axis=0)
                          for tet in t_blank])
    cent_pts = shapely.points(centroids)
    dist = np.full(len(centroids), np.inf)
    for b in boundaries:
        dist = np.minimum(dist, shapely.distance(cent_pts, b))
    near_mask = dist < near_thresh
    t_near = t_blank[near_mask]
    t_far = t_blank[~near_mask]
    print(f"[split] エッジ近傍(閾値{near_thresh*1e6:.0f}um): {len(t_near):,} / "
          f"遠方: {len(t_far):,} (近傍比率 {near_mask.mean()*100:.1f}%)")

    groups = [("Blank_Near", NEAR_PART_ID, c_blank, t_near),
              ("Blank_Far", FAR_PART_ID, c_blank, t_far)]
    for name, pid, tags in (("Die", 1, TAG_DIE), ("Stripper", 3, TAG_STRIPPER),
                            ("Punch", 4, LOCAL_PUNCH_TAGS)):
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
        f"{i10(2022)}{i10(0)}",
        f"{'kg':>20}{'m':>20}{'s':>20}",
        f"{'kg':>20}{'m':>20}{'s':>20}",
        "/TITLE", f"Panel 4mm ASSY 3D blanking ({tag}) - local hole region, Sol2SPH edge-only",
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
    L.append(ref["fail"])
    L.extend(tetra_prop(1, "Tool_Solid"))
    near_prop = tetra_prop(NEAR_PART_ID, "Blank_Solid_Near")
    near_prop.append(f"{i10(ndir)}{i10(SPH_PART_ID)}{i10(0)}")
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
                (FAR_PART_ID, "Blank_Far", FAR_PROP_ID, 2),
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
        "/ANIM/ELEM/EPSP", "/ANIM/ELEM/VONM", "/ANIM/VECT/DISP", "/END", "",
    ]), encoding="utf-8")

    print(f"\n[deck] 節点 {len(nodes):,}")
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
    ap.add_argument("--near-thresh", type=float, default=0.15e-3)
    ap.add_argument("--box-margin", type=float, default=10e-3,
                    help="丸穴中心からの局所領域の半幅[m](既定10mm)")
    ap.add_argument("--ndir", type=int, default=NDIR)
    ap.add_argument("--retract-frac", type=float, default=1.0)
    ap.add_argument("--settle-frac", type=float, default=2.0)
    a = ap.parse_args()
    build(a.tag, a.blank_elem, a.tool_elem, a.stroke, a.speed, a.gap_max, a.stfac,
          a.nstep, a.eps_eff, a.eps_s, a.near_thresh, a.box_margin, a.ndir,
          a.retract_frac, a.settle_frac)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
