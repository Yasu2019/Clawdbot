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
HOLE_R = 0.28                        # φ0.56 (公称値。パンチ寸法の参照用)
# 2026-09-03発覚: STEPの実際の穴境界はHOLE_R(280um)よりr≈300umまで外側に
# ある(実測、31万要素規模で確認)。add_slugのシリンダー半径をHOLE_Rのまま
# にすると280-300umの薄い環状隙間が生じ、四面体が一切生成されず(丸穴に
# 材料が存在しないままP1r/P1r2/P1r3を実行していた根本原因)。シリンダーは
# 実測境界に対し確実に重なる310umを使う(300um境界とのちょうど一致は
# OCCが非多様体境界として拒否するため、若干の重なりが必須)。
SLUG_FILL_R = 0.31                   # add_slug専用。HOLE_Rとは別(実測値+余裕)

MM = 1.0e-3                          # STEP は mm、デックは m

DEFAULT_BLANK_ELEM = 100.0e-6        # 板厚 0.5mm に対し 5 層
DEFAULT_TOOL_ELEM = 250.0e-6         # 工具は弾性体。荷重が伝わればよい

# 丸穴局所細分化（2026-08-28 追加）: P1本体(100umメッシュ)へ/DT/BRICK/DELを
# 適用しても丸穴は貫通しなかった(強制削除は0件=数値不安定性は無し)。
# 孤立診断モデル(RH4/RH5)は20umメッシュでのみ完全分離を達成しており、
# 真因は100umメッシュでは丸穴(φ0.56mm)の直径に対し要素数が5-6個しか無く
# 局所ひずみ集中を解像できていないこと。丸穴周辺だけ20umまで細分化する。
DEFAULT_ROUND_ELEM = 20.0e-6         # RH4/RH5で完全分離を確認した解像度
# GENE1校正値(2026-08-18〜25に確立): 100umメッシュではEps_s=0.5単独が必要。
# 参照デッキの素の値(Eps_s=0.1, Eps_eff=0.12)を両方有効のまま使うと二重発火する。
DEFAULT_EPS_S = 0.5
DEFAULT_EPS_EFF = 100.0              # 実質無効化(Eps_s単独で判定)
ROUND_REFINE_R = 0.6e-3              # 細分化する半径(HOLE_R=0.28mmに余裕を持たせる)[m]
ROUND_REFINE_RAMP = 1.0e-3           # 細→粗へ遷移させる距離[m]（急変によるメッシュ破綻回避）
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


def override_gene1(block: str, nstep: int, eps_s: float, eps_eff: float) -> str:
    """Nstep / Eps_s / Eps_eff を差し替える。

    2026-09-02発覚: この関数は元々Nstepしか上書きしておらず、P1r/P1r2は
    参照デッキの未校正値(Eps_s=0.1, Eps_eff=0.12が両方同時有効)のまま
    走っていた。これは数週間前に特定・修正した「二重発火」バグと同一で、
    P1_calibrated(バイナリパッチ版)でのみ修正が反映されていた。
    """
    out = []
    for i, ln in enumerate(block.splitlines()):
        prev = block.splitlines()[i - 1] if i else ""
        if "Nstep" in prev and "Ismooth" in prev:
            ln = f"{i10(0)}{i10(0)}{f20(0.0)}{i10(nstep)}{i10(0)}{i10(0)}{f20(0.0)}"
        elif "Eps_max" in prev and "Eps_eff" in prev:
            ln = f"{i10(0)}{f20(0.0)}{f20(0.0)}{f20(eps_eff)}{f20(0.0)}"
        elif "Eps_min" in prev and "Eps_s" in prev:
            ln = f"{f20(0.0)}{f20(eps_s)}{i10(0)}{i10(0)}{i10(0)}"
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
               dz_mm: float = 0.0, refine: tuple | None = None):
    """指定 tag だけを別モデルで切り出してメッシュし、節点座標と四面体を返す。

    全体を一度にメッシュすると材料の丸穴まわりが PLC エラーで落ちる。
    接触で繋ぐので各部品が非共形でも問題ない。

    refine: (cx_mm, cy_mm, cz_mm, r_fine_mm, elem_fine_mm, ramp_mm) を渡すと、
    その中心から r_fine_mm 以内を elem_fine_mm、ramp_mm かけて elem_mm へ
    滑らかに戻す gmsh Ball フィールドを使う(全体を細かくすると要素数が
    爆発するため丸穴周辺のみ)。座標は STEP の元系(dz_mm 適用前)。
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
        # SLUG_FILL_R(実測境界+余裕)を使う。HOLE_Rでは薄い隙間が残り
        # 四面体が生成されない(2026-09-03発覚)。
        gmsh.model.occ.addCylinder(HOLE_CENTER[0], HOLE_CENTER[1], 0.6,
                                   0, 0, 0.5, SLUG_FILL_R)
        gmsh.model.occ.synchronize()
    if fuse:
        o = [(3, t) for d, t in gmsh.model.getEntities(3)]
        gmsh.model.occ.fuse(o[:1], o[1:])
        gmsh.model.occ.removeAllDuplicates()
        gmsh.model.occ.synchronize()
        # 2026-09-03発覚の重大バグ: 上のコメントは誤りだった。fuse は向きの
        # 反転した重複ソリッドを残し、removeAllDuplicates 後も実際には
        # 2エンティティ(体積+X, -X)のまま残る(1領域には統合されない)。
        # 「メッシュ体積で検証済み」という主張は、丸穴シリンダー追加前の
        # 5片単独fuseでのみ確認されており、add_slug込みでは未検証だった。
        # 結果、丸穴シリンダーの体積が交差キャンセルで消え、P1r/P1r2/P1r3
        # は丸穴に材料が一度も存在しないまま実行されていた。正しい体積
        # (質量>0)のエンティティだけを残し、反転複製(質量<0)は明示的に
        # 削除する。recursive=True でのこの削除はクラッシュしないことを
        # 個別テストで確認済み(旧コメントの「クラッシュする」は誤り)。
        for d, t in list(gmsh.model.getEntities(3)):
            if gmsh.model.occ.getMass(d, t) < 0:
                gmsh.model.occ.remove([(d, t)], recursive=True)
        gmsh.model.occ.synchronize()

    if refine is not None:
        cx, cy, cz, r_fine, elem_fine, ramp = refine
        fid = gmsh.model.mesh.field.add("Ball")
        gmsh.model.mesh.field.setNumber(fid, "XCenter", cx)
        gmsh.model.mesh.field.setNumber(fid, "YCenter", cy)
        gmsh.model.mesh.field.setNumber(fid, "ZCenter", cz)
        gmsh.model.mesh.field.setNumber(fid, "Radius", r_fine)
        gmsh.model.mesh.field.setNumber(fid, "VIn", elem_fine)
        gmsh.model.mesh.field.setNumber(fid, "VOut", elem_mm)
        gmsh.model.mesh.field.setNumber(fid, "Thickness", ramp)
        gmsh.model.mesh.field.setAsBackgroundMesh(fid)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    else:
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

    # remove(recursive=False) は削除したソリッドの面・辺をモデルに残すので、
    # generate(3) がそれらを 2D メッシュし、四面体に属さない孤立節点が出る。
    # 放置すると全節点の 58% が孤立し、GRNOD(=境界条件の対象)まで汚染され、
    # かつ質量ゼロの自由節点が毎サイクル時間積分されて計算時間を空費する。
    # 四面体が実際に参照する節点だけを残す。
    used = {int(v) for v in tets.reshape(-1)}
    coord = {k: v for k, v in coord.items() if k in used}
    return coord, tets


def build(tag: str, blank_elem: float, tool_elem: float, stroke: float,
          speed: float, gap_max: float, stfac: float, nstep: int,
          round_elem: float = DEFAULT_ROUND_ELEM,
          eps_s: float = DEFAULT_EPS_S, eps_eff: float = DEFAULT_EPS_EFF):
    ref_txt = REF_STARTER.read_text(encoding="utf-8", errors="replace")
    ref = {
        "mat_blank": extract_block(ref_txt, r"^/MAT/LAW2/2\b"),
        "mat_tool": extract_block(ref_txt, r"^/MAT/LAW1/1\b"),
        "fail": override_gene1(extract_block(ref_txt, r"^/FAIL/GENE1/2\b"),
                               nstep, eps_s, eps_eff),
        "inter1": extract_block(ref_txt, r"^/INTER/TYPE25/1\b"),
        "inter2": extract_block(ref_txt, r"^/INTER/TYPE25/2\b"),
        "inter3": extract_block(ref_txt, r"^/INTER/TYPE25/3\b"),
    }

    # 材料はダイ上面(0.5mm)へ TOOL_GAP だけ浮かせて置く。元位置 0.6mm から下げる。
    blank_dz = -(0.6 - 0.5 - TOOL_GAP / MM)

    print("[mesh] 材料を融合してメッシュ中(丸穴周辺 %.0fum に局所細分化)..." % (round_elem * 1e6))
    refine = (HOLE_CENTER[0], HOLE_CENTER[1], 0.85,
              ROUND_REFINE_R / MM, round_elem / MM, ROUND_REFINE_RAMP / MM)
    c_blank, t_blank = mesh_group(TAG_BLANK, blank_elem / MM, fuse=True,
                                  add_slug=True, dz_mm=blank_dz, refine=refine)
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
        f"{f20(0.9)}{f20(0.0)}",
        # 丸穴周辺を局所細分化すると孤立診断(RH1-RH3S)と同様のdt崩壊リスクが
        # 出る。GENE1の破断基準とは独立した数値安定化の安全弁として常設する。
        "/DT/BRICK/DEL", f"{f20(0.9)}{f20(1.0e-11)}",
        # "/RFILE/50000" は誤り: 番号はサイクル間隔ではなく書き出しファイル数の
        # 上限で、間隔は次の行に別途必要(2026-08-30発覚。この行が無かったため
        # P1r/P1r2でリスタートファイルが一度も書かれず、クラッシュ時に全進行を
        # 喪失した)。番号無し/RFILEの2行形式(ヘッダ+サイクル間隔)を使う。
        "/RFILE", f"{i10(20000)}", "/TFILE/4", f"{f20(1.0e-6)}",
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
    ap.add_argument("--round-elem", type=float, default=DEFAULT_ROUND_ELEM,
                    help="丸穴周辺の局所細分化サイズ[m]（既定20um、RH4/RH5実績値）")
    ap.add_argument("--eps-s", type=float, default=DEFAULT_EPS_S,
                    help="GENE1 Eps_s（既定0.5、100umメッシュ校正値）")
    ap.add_argument("--eps-eff", type=float, default=DEFAULT_EPS_EFF,
                    help="GENE1 Eps_eff（既定100=実質無効化。参照デッキ素の0.12のまま"
                         "使うとEps_sと二重発火する）")
    a = ap.parse_args()
    build(a.tag, a.blank_elem, a.tool_elem, a.stroke, a.speed,
          a.gap_max, a.stfac, a.nstep, a.round_elem, a.eps_s, a.eps_eff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
