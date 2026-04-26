"""
radioss_generator.py — OpenRadioss 入力デッキ生成
  - 打ち抜き（ブランキング）解析
  - V 曲げ解析（スプリングバック）
"""
import math
import textwrap
from typing import Dict, List


def _mesh_rectangle(x0, y0, w, h, ex, ey):
    """矩形シェルメッシュ生成 → nodes, elements"""
    nx, ny = ex + 1, ey + 1
    nodes, elems = [], []
    nid = 1
    node_map = {}
    for j in range(ny):
        for i in range(nx):
            x = x0 + w * i / ex
            y = y0 + h * j / ey
            nodes.append((nid, x, y, 0.0))
            node_map[(i, j)] = nid
            nid += 1
    eid = 1
    for j in range(ey):
        for i in range(ex):
            n1 = node_map[(i,   j  )]
            n2 = node_map[(i+1, j  )]
            n3 = node_map[(i+1, j+1)]
            n4 = node_map[(i,   j+1)]
            elems.append((eid, n1, n2, n3, n4))
            eid += 1
    return nodes, elems, node_map, nx, ny


def generate_blanking(
    blank_w: float, blank_h: float,
    thickness: float,
    punch_dia: float,
    material: Dict,
    clearance: float,
    job_dir: str,
) -> Dict[str, str]:
    """
    打ち抜き（ブランキング）解析デッキ
    モデル: ブランク板 + 円形パンチ（剛体リジッドボディ）+ ダイ（剛体）
    """
    mat = material
    rho = mat['density']       # kg/mm³
    E   = mat['E']             # MPa
    nu  = mat['nu']
    sy  = mat['yield_stress']  # MPa
    n   = mat['n_hard']

    # 打ち抜き周長・力
    perimeter = math.pi * punch_dia
    punch_force_kN = perimeter * thickness * mat['shear_strength'] / 1000.0

    # 板のメッシュ（1mm 要素）
    ex = max(8, int(blank_w))
    ey = max(8, int(blank_h))
    nodes, elems, node_map, nx, ny = _mesh_rectangle(
        0.0, 0.0, blank_w, blank_h, ex, ey)

    punch_disp = thickness * 1.2  # パンチ変位 = 板厚×1.2

    # ── スターターファイル ──────────────────────────────────────────────────
    starter = textwrap.dedent(f"""\
    /UNIT/kg mm ms
    /BEGIN
    /RUN/blanking_analysis/0
        0.000    {punch_disp / 1000.0 / 2.0:.6E}
    /ANIM/DT
      0.000    {punch_disp / 1000.0 / 40:.6E}
    /ANIM/ELEM
    VONM
    EPSP
    /ANIM/SHELL
    DAMA
    """)

    # ノード
    starter += '/NODE\n'
    for nid, x, y, z in nodes:
        starter += f'{nid:>8d} {x:>15.6f} {y:>15.6f} {z:>15.6f}\n'

    # シェル要素
    starter += '/SHELL/{:d}\nBlanking_Shell\n'.format(1)
    for eid, n1, n2, n3, n4 in elems:
        starter += f'{eid:>8d}{1:>8d}{n1:>8d}{n2:>8d}{n3:>8d}{n4:>8d}\n'

    # シェルプロパティ
    starter += textwrap.dedent(f"""\
    /PROP/SHELL/{1}
    Shell_Prop
              {thickness:.4f}       5       0       0       0       0       0       0       0
                 0.001       0       0       0       1       0
                0.8333       0
    """)

    # 材料（ジョンソンクック近似 → 冪乗硬化則）
    starter += textwrap.dedent(f"""\
    /MAT/PLAS_JOHNS/{1}
    {mat['name']}
              {rho:.4E}
              {E:.2f}    {nu:.3f}
              {sy:.2f}   {mat['uts']:.2f}       1
              {n:.4f}      0.002      0.93      0.014
    """)

    # 境界条件（ブランクの四辺を Z 方向固定）
    bc_nodes = (
        [node_map[(i, 0)] for i in range(nx)] +
        [node_map[(i, ny-1)] for i in range(nx)] +
        [node_map[(0, j)] for j in range(ny)] +
        [node_map[(nx-1, j)] for j in range(ny)]
    )
    starter += '/BCS\n'
    for nid in set(bc_nodes):
        starter += f'{nid:>8d}       0       0       1       1       1       1\n'

    # パンチ剛体（円柱近似 → 点ノード + RBODY）
    punch_nid = max(n[0] for n in nodes) + 1
    die_nid   = punch_nid + 1
    punch_z_top = thickness * 0.5   # パンチ初期位置（板上面）
    die_z_bot   = -thickness * 0.5  # ダイ（板下面）
    cx = blank_w / 2.0
    cy = blank_h / 2.0

    starter += f'/NODE\n{punch_nid:>8d} {cx:>15.6f} {cy:>15.6f} {punch_z_top:>15.6f}\n'
    starter += f'{die_nid:>8d} {cx:>15.6f} {cy:>15.6f} {die_z_bot:>15.6f}\n'

    starter += textwrap.dedent(f"""\
    /RBODY/{2}
    Punch
    {punch_nid:>8d}       0
    /RBODY/{3}
    Die
    {die_nid:>8d}       0
    """)

    # パンチ変位入力（Z マイナス方向）
    starter += textwrap.dedent(f"""\
    /IMPVEL/1/PUNCH_DOWN
                 1{punch_nid:>8d}       3
                 0.000     {-punch_disp / (punch_disp / 1000.0 / 2.0) * 1e-3:.6E}
                 1.000     {-punch_disp / (punch_disp / 1000.0 / 2.0) * 1e-3:.6E}
    """)

    starter += '/END\n'

    # ── エンジンファイル ────────────────────────────────────────────────────
    engine = textwrap.dedent(f"""\
    /RUN/blanking_analysis/1
        0.000    {punch_disp / 1000.0 / 2.0:.6E}
    /ANIM/DT
      0.000    {punch_disp / 1000.0 / 40:.6E}
    /PRINT/-1000
    /STOP
    """)

    return {
        'starter': starter,
        'engine':  engine,
        'info': {
            'analysis_type': 'blanking',
            'punch_dia_mm':  punch_dia,
            'clearance_mm':  clearance,
            'punch_disp_mm': punch_disp,
            'punch_force_kN': round(punch_force_kN, 1),
            'element_count': len(elems),
            'node_count':    len(nodes),
        },
    }


def generate_bending(
    blank_w: float,
    thickness: float,
    bend_angle: float,
    bend_radius: float,
    material: Dict,
    job_dir: str,
) -> Dict[str, str]:
    """
    V 曲げ解析デッキ（スプリングバック付き）
    モデル: 平板ブランク + V 字パンチ（剛体） + V 字ダイ（剛体）
    """
    mat = material
    rho = mat['density']
    E   = mat['E']
    nu  = mat['nu']
    sy  = mat['yield_stress']
    n   = mat['n_hard']

    depth   = blank_w * 0.3   # ブランク幅（送り方向）
    ex, ey  = max(20, int(blank_w * 2)), max(6, int(depth))
    nodes, elems, node_map, nx, ny = _mesh_rectangle(
        0.0, 0.0, blank_w, depth, ex, ey)

    punch_depth = (bend_radius + thickness) * (1.0 - math.cos(math.radians(bend_angle / 2.0)))

    starter = textwrap.dedent(f"""\
    /UNIT/kg mm ms
    /BEGIN
    /RUN/bending_analysis/0
        0.000    {punch_depth / 2000:.6E}
    /ANIM/DT
      0.000    {punch_depth / 2000 / 40:.6E}
    /ANIM/ELEM
    VONM
    EPSP
    """)

    starter += '/NODE\n'
    for nid, x, y, z in nodes:
        starter += f'{nid:>8d} {x:>15.6f} {y:>15.6f} {z:>15.6f}\n'

    starter += f'/SHELL/{1}\nBending_Shell\n'
    for eid, n1, n2, n3, n4 in elems:
        starter += f'{eid:>8d}{1:>8d}{n1:>8d}{n2:>8d}{n3:>8d}{n4:>8d}\n'

    starter += textwrap.dedent(f"""\
    /PROP/SHELL/{1}
    Shell_Prop
              {thickness:.4f}       5       0       0       0       0       0       0       0
                 0.001       0       0       0       1       0
                0.8333       0
    /MAT/PLAS_JOHNS/{1}
    {mat['name']}
              {rho:.4E}
              {E:.2f}    {nu:.3f}
              {sy:.2f}   {mat['uts']:.2f}       1
              {n:.4f}      0.002      0.93      0.014
    """)

    # 支持点（ダイ開口部）
    half_die = blank_w * 0.35
    support_nodes = [node_map[(0, j)] for j in range(ny)] + \
                    [node_map[(nx-1, j)] for j in range(ny)]
    starter += '/BCS\n'
    for nid in set(support_nodes):
        starter += f'{nid:>8d}       0       1       1       1       1       1\n'

    # パンチ剛体ノード
    punch_nid = max(n[0] for n in nodes) + 1
    starter += f'/NODE\n{punch_nid:>8d} {blank_w/2:.4f} {depth/2:.4f} {thickness:.4f}\n'
    starter += textwrap.dedent(f"""\
    /RBODY/{2}
    VPunch
    {punch_nid:>8d}       0
    /IMPVEL/1/PUNCH_DOWN
                 1{punch_nid:>8d}       3
                 0.000     {-punch_depth / (punch_depth / 2000) * 1e-3:.6E}
                 1.000     {-punch_depth / (punch_depth / 2000) * 1e-3:.6E}
    /END
    """)

    engine = textwrap.dedent(f"""\
    /RUN/bending_analysis/1
        0.000    {punch_depth / 2000:.6E}
    /ANIM/DT
      0.000    {punch_depth / 2000 / 40:.6E}
    /PRINT/-1000
    /STOP
    """)

    # スプリングバック角度推定（経験式）
    # 各材料の目標値 SPCC≈3°, SUS304≈8°, A1050≈5°, A5052≈7° at 90°, R/t=1
    cf_map = {'SPCC':35, 'SUS304':80, 'A1050':110, 'A5052':28, 'C2680':49}
    mat_name = material.get('name', '')
    cf = next((cf_map[k] for k, m in __import__('strip_layout').MATERIALS.items()
               if m['name'] == mat_name), 35)
    sb_angle = round(bend_angle * (sy / E) * cf, 1)

    return {
        'starter': starter,
        'engine':  engine,
        'info': {
            'analysis_type':  'bending',
            'bend_angle_deg': bend_angle,
            'bend_radius_mm': bend_radius,
            'punch_depth_mm': round(punch_depth, 3),
            'springback_deg': sb_angle,
            'corrected_angle': round(bend_angle + sb_angle, 1),
            'element_count':  len(elems),
            'node_count':     len(nodes),
        },
    }
