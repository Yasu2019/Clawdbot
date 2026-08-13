# -*- coding: utf-8 -*-
"""Panel 4mm ASSY の実形状 3D 打ち抜きデックを生成する。2026-08-13 導入。

入力は ASSY_3D-MPM_PM7T1C_20260813.step。この STEP は「抜き終わった後」の
状態で、材料が製品+スクラップ4片に分解済み・丸穴は空洞になっている。
打ち抜き解析には抜く前の一枚板が要るので、5片を融合し丸穴スラグを補填する。

Z スタック(元 STEP、mm):
    0.0-0.5  ダイ            (tag 6,7)
    0.6-1.1  材料5片         (tag 1..5)  -> 融合して 1 枚に
    1.2-1.7  ストリッパー    (tag 8,9)
    1.8-2.3  四角パンチ x2   (tag 10=V字ノッチ, 11=右下矩形)
    2.4-2.9  トリムパンチ    (tag 12)
    3.0-3.5  丸パンチ φ0.56  (tag 13)

パンチ底面が段違いなので、単一 3mm ストロークで四角→トリム→丸の順に
時間差で接触する。順送の実挙動と同じ。

⚠ 忠実度の制約(報告時に必ず明記すること):
    要素 100um は板厚方向 5 層しかない。せん断帯は文献で 21-44um なので
    破断面・バリ・だれは予測にならない。得られるのは荷重レベルと巨視的な
    分離挙動まで。破断面が要る場合は slice3d 経路(10um)を使う。

usage:
  python scripts/build_panel4mm_3d_blanking.py --tag P1
  python scripts/build_panel4mm_3d_blanking.py --tag P2 --blank-elem 80e-6
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

ROOT = Path(r"D:\Clawdbot_Docker_20260125")
TRIALS = ROOT / "data" / "workspace" / "openradioss_inc188_trials"
REF_STARTER = TRIALS / "INC188AC_shear_coupon_0000.rad"
STEP = Path(r"C:\Users\yasu\OneDrive\デスクトップ\Panel\ASSY_3D-MPM_PM7T1C_20260813.step")

# STEP 内のソリッド tag（gmsh/OCC の読み込み順。実測で確定済み）
TAG_BLANK = [1, 2, 3, 4, 5]
TAG_DIE = [6, 7]
TAG_STRIPPER = [8, 9]
TAG_PUNCH = [10, 11, 12, 13]
HOLE_CENTER = (185.657, -1882.188)   # 丸穴中心 [mm]
HOLE_R = 0.28                        # φ0.56

MM = 1.0e-3                          # STEP は mm、デックは m

DEFAULT_BLANK_ELEM = 100.0e-6        # 板厚 0.5mm に対し 5 層
DEFAULT_TOOL_ELEM = 250.0e-6         # 工具は弾性体。荷重が伝わればよい
TOOL_GAP = 5.0e-6                    # 板と工具の初期すきま。初期貫入エラー回避
DEFAULT_GAP_MAX = 15.0e-6            # TOOL_GAP < Gap_max（slice3d と同じ関係）
DEFAULT_STFAC = 1.0                  # 接触剛性。AC の 0.05 は細メッシュに柔らかすぎた
DEFAULT_NSTEP = 10                   # 破断応力を落とすサイクル数。0 は爆発する
DEFAULT_STROKE = 3.0e-3              # ユーザー指示: 材料方向へ 3mm
DEFAULT_SPEED = 5.0                  # m/s。DOE 既定 5000mm/s と同じ
STRIPPER_CLOSE_T = 1.0e-4            # ストリッパーが閉じ切る時刻 [s]


def i10(v=None) -> str:
    return "" if v is None else f"{int(v):>10d}"


def f20(v=None) -> str:
    return "" if v is None else f"{float(v):>20.7G}"


def extract_block(txt: str, pattern: str) -> str:
    """/KEYWORD から次の / 始まり行の直前までを切り出す。"""
    import re
    lines = txt.splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(pattern, l))
    end = start + 1
    while end < len(lines) and not lines[end].startswith("/"):
        end += 1
    return "\n".join(lines[start:end])


def override_gene1(block: str, nstep: int) -> str:
    """Nstep だけ差し替える。0 のままだと 1 サイクルで解放され連鎖破断する。"""
    out = []
    for i, ln in enumerate(block.splitlines()):
        prev = block.splitlines()[i - 1] if i else ""
        if "Nstep" in prev and "Ismooth" in prev:
            ln = f"{i10(0)}{i10(0)}{f20(0.0)}{i10(nstep)}{i10(0)}{i10(0)}{f20(0.0)}"
        out.append(ln)
    return "\n".join(out)


def tetra_prop(pid: int, title: str) -> list[str]:
    """TETRA4 用 /PROP/SOLID。Isolid=1 / Ismstr=-1（rad_model の tetra_only と同値）。"""
    return [
        f"/PROP/SOLID/{pid}",
        title,
        "#    Isolid    Ismstr                          Icpre     Itetra4    Itetra10     Iframe                   Dn",
        "".join([i10(1), i10(-1), i10(0), i10(0), i10(2), i10(0), i10(3), i10(1), f20(0.1)]),
        "".join([f20(0.0), f20(0), f20(0.1), f20(0), f20(0)]),
        "".join(f20(0) for _ in range(5)),
    ]


def remap_type25(block: str, iid: int, label: str, surf1: int, surf2: int,
                 gap_max: float, stfac: float) -> str:
    """参照デッキ(AC)の TYPE25 を本モデルの面ID・ギャップ・剛性へ読み替える。

    AC のカラム幅は不規則だが破断 2042 件の実績があるので書式は触らない。
    """
    lines = block.splitlines()
    lines[0] = f"/INTER/TYPE25/{iid}/0"
    lines[1] = label
    lines[3] = f"{i10(surf1)}{i10(surf2)}" + lines[3][20:]
    lines[5] = lines[5][:-40] + f20(gap_max) + f20(gap_max)
    lines[9] = f20(stfac) + lines[9][20:]
    return "\n".join(lines)


def fmt_grnod(gid: int, name: str, nodes) -> list[str]:
    out = [f"/GRNOD/NODE/{gid}", name]
    uniq = sorted(set(nodes))
    for k in range(0, len(uniq), 10):
        out.append("".join(i10(n) for n in uniq[k:k + 10]))
    return out


def mesh_group(tags: list[int], elem_mm: float, *, fuse: bool, add_slug: bool,
               dz_mm: float = 0.0):
    """指定 tag だけを別モデルで切り出してメッシュし、節点座標と四面体を返す。

    全体を一度にメッシュすると材料の丸穴まわりが PLC エラーで落ちる。
    接触で繋ぐので各部品が非共形でも問題ない。
    """
    import gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.occ.importShapes(str(STEP))
    gmsh.model.occ.synchronize()
    gmsh.model.occ.remove(
        [(3, t) for d, t in gmsh.model.getEntities(3) if t not in tags],
        recursive=False)
    gmsh.model.occ.synchronize()

    if add_slug:
        # STEP は抜き後の状態で丸穴が空洞。塞がないと丸パンチが切る材料が無い。
        gmsh.model.occ.addCylinder(HOLE_CENTER[0], HOLE_CENTER[1], 0.6,
                                   0, 0, 0.5, HOLE_R)
        gmsh.model.occ.synchronize()
    if fuse:
        o = [(3, t) for d, t in gmsh.model.getEntities(3)]
        gmsh.model.occ.fuse(o[:1], o[1:])
        gmsh.model.occ.removeAllDuplicates()
        gmsh.model.occ.synchronize()
        # fuse は向きの反転した重複ソリッドを残すが、removeAllDuplicates 後は
        # 1 領域として張られるので放置してよい（メッシュ体積で検証済み）。
        # ここで remove すると "Could not fix wire" でカーネルが落ちる。

    gmsh.option.setNumber("Mesh.MeshSizeMin", elem_mm)
    gmsh.option.setNumber("Mesh.MeshSizeMax", elem_mm)
    gmsh.model.mesh.generate(3)

    ntags, ncoord, _ = gmsh.model.mesh.getNodes()
    # Z シフトは CAD 変換でなくメッシュ座標へ加算する。occ.translate は
    # 融合後のソリッドで "Could not fix wire" を起こすため使わない。
    coord = {int(t): (ncoord[3 * k], ncoord[3 * k + 1], ncoord[3 * k + 2] + dz_mm)
             for k, t in enumerate(ntags)}
    etags, enodes = gmsh.model.mesh.getElementsByType(4)
    tets = np.array(enodes, dtype=np.int64).reshape(-1, 4)
    gmsh.finalize()
    return coord, tets


def build(tag: str, blank_elem: float, tool_elem: float, stroke: float,
          speed: float, gap_max: float, stfac: float, nstep: int):
    ref_txt = REF_STARTER.read_text(encoding="utf-8", errors="replace")
    ref = {
        "mat_blank": extract_block(ref_txt, r"^/MAT/LAW2/2\b"),
        "mat_tool": extract_block(ref_txt, r"^/MAT/LAW1/1\b"),
        "fail": override_gene1(extract_block(ref_txt, r"^/FAIL/GENE1/2\b"), nstep),
        "inter1": extract_block(ref_txt, r"^/INTER/TYPE25/1\b"),
        "inter2": extract_block(ref_txt, r"^/INTER/TYPE25/2\b"),
        "inter3": extract_block(ref_txt, r"^/INTER/TYPE25/3\b"),
    }

    # 材料はダイ上面(0.5mm)へ TOOL_GAP だけ浮かせて置く。元位置 0.6mm から下げる。
    blank_dz = -(0.6 - 0.5 - TOOL_GAP / MM)

    print("[mesh] 材料を融合してメッシュ中...")
    c_blank, t_blank = mesh_group(TAG_BLANK, blank_elem / MM, fuse=True,
                                  add_slug=True, dz_mm=blank_dz)
    print(f"[mesh]   材料 TET4={len(t_blank):,}")
    groups = [("Blank", 2, c_blank, t_blank)]
    for name, pid, tags in (("Die", 1, TAG_DIE), ("Stripper", 3, TAG_STRIPPER),
                            ("Punch", 4, TAG_PUNCH)):
        print(f"[mesh] {name} をメッシュ中...")
        c, t = mesh_group(tags, tool_elem / MM, fuse=False, add_slug=False)
        print(f"[mesh]   {name} TET4={len(t):,}")
        groups.append((name, pid, c, t))

    # 各グループを通し番号へ詰め替える（部品ごとに別メッシュなので節点は独立）
    nodes: dict[int, tuple[float, float, float]] = {}
    part_elems: dict[int, list[tuple[int, tuple[int, int, int, int]]]] = {}
    part_nodes: dict[int, list[int]] = {}
    nid = 0
    eid = 0
    for name, pid, coord, tets in groups:
        remap = {}
        for old, xyz in coord.items():
            nid += 1
            remap[old] = nid
            nodes[nid] = (xyz[0] * MM, xyz[1] * MM, xyz[2] * MM)
        part_nodes[pid] = list(remap.values())
        el = []
        for t in tets:
            eid += 1
            el.append((eid, tuple(remap[int(v)] for v in t)))
        part_elems[pid] = el

    t_stop = stroke / speed

    L: list[str] = [
        "#RADIOSS STARTER", "/BEGIN", f"PANEL4MM_{tag}",
        f"{i10(2022)}{i10(0)}",
        f"{'kg':>20}{'m':>20}{'s':>20}",
        f"{'kg':>20}{'m':>20}{'s':>20}",
        "/TITLE", f"Panel 4mm ASSY 3D blanking ({tag}) - 4 punches, {stroke*1e3:g}mm stroke",
        "/ANALY", "#    N2D3D             IPARITH", f"{i10(0)}          {i10(1)}",
        "/NODE",
    ]
    for n, (x, y, z) in nodes.items():
        L.append(f"{i10(n)}{f20(x)}{f20(y)}{f20(z)}")

    for pid in (1, 2, 3, 4):
        L.append(f"/TETRA4/{pid}")
        for e, nn in part_elems[pid]:
            L.append(i10(e) + "".join(i10(v) for v in nn))

    L.append(ref["mat_tool"])
    L.append(ref["mat_blank"])
    L.append(ref["fail"])
    L.extend(tetra_prop(1, "Tool_Solid"))
    L.extend(tetra_prop(2, "Blank_Solid"))

    for pid, pname, prop, mat in ((1, "Die", 1, 1), (2, "Blank", 2, 2),
                                  (3, "Stripper", 1, 1), (4, "Punch", 1, 1)):
        L.append(f"/PART/{pid}")
        L.append(pname)
        L.append("#    Prop_ID     Mat_ID")
        L.append(f"{i10(prop)}{i10(mat)}")

    L.extend(fmt_grnod(100, "Punch_Nodes", part_nodes[4]))
    L.extend(fmt_grnod(200, "Blank_Nodes", part_nodes[2]))
    L.extend(fmt_grnod(300, "Die_Nodes", part_nodes[1]))
    L.extend(fmt_grnod(400, "Stripper_Nodes", part_nodes[3]))

    for sid, pid in ((1, 1), (2, 2), (3, 3), (4, 4)):
        L.append(f"/SURF/PART/EXT/{sid}00/0")
        L.append(f"Surf_Part_{pid}")
        L.append(f"{i10(pid)}")

    # パンチ: 0 -> -stroke の等速。工具底面が段違いなので接触は自然に時間差になる。
    L += ["/FUNCT/1", "Punch_Stroke",
          "#                  X                   Y",
          f"{f20(0.0)}{f20(0.0)}", f"{f20(t_stop)}{f20(-stroke)}",
          f"{f20(t_stop*10)}{f20(-stroke)}"]
    # ストリッパー: パンチが板に届く前に閉じ切って押さえる。
    strip_close = (1.2 - (1.1 + blank_dz)) * MM - TOOL_GAP
    L += ["/FUNCT/2", "Stripper_Close",
          "#                  X                   Y",
          f"{f20(0.0)}{f20(0.0)}", f"{f20(STRIPPER_CLOSE_T)}{f20(-strip_close)}",
          f"{f20(t_stop*10)}{f20(-strip_close)}"]
    L += ["/FUNCT/3", "Zero",
          "#                  X                   Y",
          f"{f20(0.0)}{f20(0.0)}", f"{f20(t_stop*10)}{f20(0.0)}"]

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
        f"/RUN/PANEL4MM_{tag}/1", f"{f20(t_stop)}", "/DT/NODA/0",
        f"{f20(0.9)}{f20(0.0)}", "/RFILE/50000", "/TFILE/4", f"{f20(1.0e-6)}",
        "/ANIM/DT", f"{f20(0.0)}{f20(t_stop/40)}",
        "/ANIM/ELEM/EPSP", "/ANIM/ELEM/VONM", "/ANIM/VECT/DISP", "/END", "",
    ]), encoding="utf-8")

    tot_e = sum(len(v) for v in part_elems.values())
    print(f"\n[deck] 節点 {len(nodes):,} / TET4 {tot_e:,}")
    for pid, pname in ((1, "Die"), (2, "Blank"), (3, "Stripper"), (4, "Punch")):
        print(f"[deck]   part {pid} {pname:9s}: {len(part_elems[pid]):>8,}")
    print(f"[deck] ストローク {stroke*1e3:g}mm / 速度 {speed:g}m/s / tstop {t_stop:g}s")
    print(f"[deck] ストリッパー閉じ {strip_close*1e3:.3f}mm @ t={STRIPPER_CLOSE_T:g}s")
    print(f"[deck] 接触 TYPE25 x3 / Gap_max {gap_max*1e6:.1f}um / Stfac {stfac:g} / Nstep {nstep}")
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
    ap.add_argument("--gap-max", type=float, default=DEFAULT_GAP_MAX)
    ap.add_argument("--stfac", type=float, default=DEFAULT_STFAC)
    ap.add_argument("--nstep", type=int, default=DEFAULT_NSTEP)
    a = ap.parse_args()
    build(a.tag, a.blank_elem, a.tool_elem, a.stroke, a.speed,
          a.gap_max, a.stfac, a.nstep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
