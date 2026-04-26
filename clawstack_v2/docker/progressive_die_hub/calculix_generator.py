"""
calculix_generator.py — CalculiX パンチ・ダイ強度解析 (.inp)
"""
import math
import textwrap
from typing import Dict


def generate_punch_strength(
    punch_dia: float,
    punch_length: float,
    thickness: float,
    punch_force_kN: float,
    die_material: str = 'SKD11',
) -> str:
    """
    パンチ強度解析 CalculiX 入力デッキ
    モデル: 円柱パンチ (C3D8R) — 軸対称 1/4 モデル
    """
    die_materials = {
        'SKD11': {'E': 210000.0, 'nu': 0.28, 'sy': 1800.0, 'name': 'SKD11 (冷間工具鋼)'},
        'SKH51': {'E': 220000.0, 'nu': 0.28, 'sy': 2200.0, 'name': 'SKH51 (高速度鋼)'},
        'SKS3':  {'E': 207000.0, 'nu': 0.29, 'sy': 1500.0, 'name': 'SKS3 (切削工具鋼)'},
    }
    mat  = die_materials.get(die_material, die_materials['SKD11'])
    E    = mat['E']
    nu   = mat['nu']
    sy   = mat['sy']

    r    = punch_dia / 2.0
    # 1/4 モデル: x=[0,r], z=[0,punch_length]
    nr, nz = 4, 8   # 要素分割数
    nnr, nnz = nr + 1, nz + 1

    nodes = []
    nid = 1
    node_map = {}
    for k in range(nnz):
        for i in range(nnr):
            x = r * i / nr
            z = punch_length * k / nz
            nodes.append((nid, x, 0.0, z))
            node_map[(i, k)] = nid
            nid += 1

    elems = []
    eid = 1
    for k in range(nz):
        for i in range(nr):
            # C3D8 (8節点 六面体) → 縮退して C3D8R
            n1 = node_map[(i,   k  )]
            n2 = node_map[(i+1, k  )]
            n3 = node_map[(i+1, k+1)]
            n4 = node_map[(i,   k+1)]
            # y=0 面の対称コピー
            elems.append((eid, n1, n2, n3, n4))
            eid += 1

    # 座屈荷重チェック（Euler 列 — ガイド付きパンチ: 有効長 Le = L/2）
    I       = math.pi * r**4 / 64.0   # 断面2次モーメント
    A       = math.pi * r**2
    Le      = punch_length / 2.0       # ストリッパーガイドで両端支持 → K=0.5
    Pcr_kN  = math.pi**2 * E * I / Le**2 / 1000.0
    safety  = Pcr_kN / punch_force_kN if punch_force_kN > 0 else 999.0

    # 圧縮応力
    sigma_c = punch_force_kN * 1000.0 / A  # MPa
    sf_comp = sy / sigma_c if sigma_c > 0 else 999.0

    inp = textwrap.dedent(f"""\
    ** =====================================================
    ** CalculiX Punch Strength Analysis
    ** Material : {mat['name']}
    ** Punch    : φ{punch_dia:.2f} × {punch_length:.2f} mm
    ** Load     : {punch_force_kN:.1f} kN
    ** =====================================================
    *HEADING
    Progressive Die - Punch Strength ({die_material})
    **
    *NODE, NSET=ALLNODES
    """)
    for nid, x, y, z in nodes:
        inp += f'{nid:>6d}, {x:>12.6f}, {y:>12.6f}, {z:>12.6f}\n'

    inp += '*ELEMENT, TYPE=C3D8R, ELSET=PUNCH\n'
    # 簡易メッシュ（2D 投影 → 3D extrude）
    for eid, n1, n2, n3, n4 in elems:
        # y=0 面と y=r 面 (全幅モデル近似)
        # nid オフセット：+len(nodes) → y 方向ミラー
        off = len(nodes)
        inp += (f'{eid:>6d}, {n1}, {n2}, {n3}, {n4}, '
                f'{n1+off}, {n2+off}, {n3+off}, {n4+off}\n')

    # ミラーノード (y = r)
    inp += '*NODE\n'
    for nid, x, y, z in nodes:
        inp += f'{nid + len(nodes):>6d}, {x:>12.6f}, {r:>12.6f}, {z:>12.6f}\n'

    inp += textwrap.dedent(f"""\
    **
    *MATERIAL, NAME={die_material}
    *ELASTIC
    {E:.0f}, {nu:.2f}
    *PLASTIC
    {sy:.0f}, 0.0
    {sy * 1.1:.0f}, 0.05
    **
    *SOLID SECTION, ELSET=PUNCH, MATERIAL={die_material}
    **
    ** Boundary Conditions
    *NSET, NSET=BOTTOM
    """)
    # ボトムノード (k=0)
    bottom_ids = [node_map[(i, 0)] for i in range(nnr)]
    bottom_ids += [n + len(nodes) for n in bottom_ids]
    inp += ', '.join(str(n) for n in bottom_ids) + '\n'

    inp += textwrap.dedent(f"""\
    *NSET, NSET=TOP
    """)
    top_ids = [node_map[(i, nz)] for i in range(nnr)]
    top_ids += [n + len(nodes) for n in top_ids]
    inp += ', '.join(str(n) for n in top_ids) + '\n'

    total_nodes = len(nodes) * 2
    inp += textwrap.dedent(f"""\
    **
    *STEP, NLGEOM
    *STATIC
    0.1, 1.0, 1e-5, 0.2
    **
    ** Fixed Bottom
    *BOUNDARY
    BOTTOM, 1, 6
    **
    ** Applied Load: {punch_force_kN:.1f} kN (compression)
    *CLOAD
    """)
    force_per_node = -punch_force_kN * 1000.0 / len(top_ids)
    for nid in top_ids:
        inp += f'{nid}, 3, {force_per_node:.4f}\n'

    inp += textwrap.dedent(f"""\
    **
    *NODE FILE
    U
    *EL FILE
    S, PEEQ
    *END STEP
    **
    ** =====================================================
    ** 事前計算結果サマリー
    **   圧縮応力    : {sigma_c:.1f} MPa  (許容 {sy:.0f} MPa, SF={sf_comp:.2f})
    **   座屈荷重    : {Pcr_kN:.1f} kN (SF={safety:.2f})
    **   推奨パンチ長: {min(punch_length, r * 10.0):.1f} mm 以下
    ** =====================================================
    """)

    return inp, {
        'die_material':    die_material,
        'sigma_comp_MPa':  round(sigma_c, 1),
        'yield_MPa':       sy,
        'sf_compression':  round(sf_comp, 2),
        'buckling_kN':     round(Pcr_kN, 1),
        'sf_buckling':     round(safety, 2),
        'status': 'OK' if sf_comp > 1.5 and safety > 2.0 else 'REVIEW',
    }


def generate_die_insert_strength(
    punch_dia: float,
    die_thickness: float,
    punch_force_kN: float,
    die_material: str = 'SKD11',
) -> str:
    """ダイインサート強度解析（簡易リング要素）"""
    die_materials = {
        'SKD11': {'E': 210000.0, 'nu': 0.28, 'sy': 1800.0},
        'SKH51': {'E': 220000.0, 'nu': 0.28, 'sy': 2200.0},
    }
    mat   = die_materials.get(die_material, die_materials['SKD11'])
    E, nu = mat['E'], mat['nu']
    sy    = mat['sy']

    r_i   = punch_dia / 2.0
    r_o   = r_i + die_thickness

    # Lamé の式 (内圧 → 打ち抜き力による等価圧力)
    A     = math.pi * r_i ** 2
    p     = punch_force_kN * 1000.0 / A  # 等価内圧 MPa
    sigma_r_max = p * r_i**2 / (r_o**2 - r_i**2) * (1 + r_o**2 / r_i**2)
    sf    = sy / sigma_r_max

    inp = textwrap.dedent(f"""\
    ** =====================================================
    ** CalculiX Die Insert Strength (Lame approximation)
    ** Die: φ{punch_dia:.1f} bore, wall {die_thickness:.1f} mm, {die_material}
    ** =====================================================
    *HEADING
    Die Insert Strength
    **
    ** Pre-computed hoop stress (Lame):
    **   Hoop stress (max) : {sigma_r_max:.1f} MPa
    **   Yield stress      : {sy:.0f} MPa
    **   Safety Factor     : {sf:.2f}
    **   Status            : {'OK' if sf > 2.0 else 'INCREASE WALL THICKNESS'}
    **
    ** (Full FEM mesh omitted - use pre-computed result above)
    """)

    return inp, {
        'hoop_stress_MPa': round(sigma_r_max, 1),
        'yield_MPa':       sy,
        'sf':              round(sf, 2),
        'status': 'OK' if sf > 2.0 else 'INCREASE WALL THICKNESS',
    }
