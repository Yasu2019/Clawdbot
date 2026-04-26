"""
strip_layout.py — 順送金型ストリップレイアウト生成 (SVG)
"""
import math
from typing import List, Tuple, Dict, Any

# ── 材料データベース ───────────────────────────────────────────────────────────
MATERIALS: Dict[str, Dict] = {
    'SPCC': {
        'name': 'SPCC（冷間圧延鋼板）',
        'density': 7.85e-6, 'E': 206000.0, 'nu': 0.30,
        'yield_stress': 200.0, 'uts': 320.0, 'elongation': 0.30,
        'n_hard': 0.22, 'k_factor': 0.33, 'clearance_ratio': 0.10,
        'shear_strength': 250.0, 'color': '#B8C4CC',
    },
    'SUS304': {
        'name': 'SUS304（ステンレス）',
        'density': 7.93e-6, 'E': 193000.0, 'nu': 0.30,
        'yield_stress': 215.0, 'uts': 520.0, 'elongation': 0.45,
        'n_hard': 0.30, 'k_factor': 0.35, 'clearance_ratio': 0.12,
        'shear_strength': 380.0, 'color': '#D4DDE4',
    },
    'A1050': {
        'name': 'A1050（純アルミニウム）',
        'density': 2.70e-6, 'E': 69000.0, 'nu': 0.33,
        'yield_stress': 35.0, 'uts': 95.0, 'elongation': 0.25,
        'n_hard': 0.20, 'k_factor': 0.30, 'clearance_ratio': 0.08,
        'shear_strength': 65.0, 'color': '#C8C8C0',
    },
    'A5052': {
        'name': 'A5052（アルミニウム合金）',
        'density': 2.68e-6, 'E': 70000.0, 'nu': 0.33,
        'yield_stress': 195.0, 'uts': 230.0, 'elongation': 0.12,
        'n_hard': 0.18, 'k_factor': 0.35, 'clearance_ratio': 0.10,
        'shear_strength': 160.0, 'color': '#C4C0BC',
    },
    'C2680': {
        'name': 'C2680（黄銅・真鍮）',
        'density': 8.50e-6, 'E': 110000.0, 'nu': 0.34,
        'yield_stress': 100.0, 'uts': 320.0, 'elongation': 0.35,
        'n_hard': 0.25, 'k_factor': 0.35, 'clearance_ratio': 0.10,
        'shear_strength': 220.0, 'color': '#D4A830',
    },
}


# ── 曲げ展開計算 ──────────────────────────────────────────────────────────────
def bend_allowance(angle_deg: float, r_inner: float,
                   thickness: float, k_factor: float) -> float:
    """曲げ代 (Bend Allowance) を計算"""
    return (math.pi / 180.0) * angle_deg * (r_inner + k_factor * thickness)


def bend_deduction(angle_deg: float, r_inner: float,
                   thickness: float, k_factor: float) -> float:
    """曲げ控除 (Bend Deduction) を計算"""
    ba = bend_allowance(angle_deg, r_inner, thickness, k_factor)
    os_ = math.tan(math.radians(angle_deg / 2.0)) * (r_inner + thickness)
    return 2.0 * os_ - ba


# ── ブランクサイズ計算 ─────────────────────────────────────────────────────────
def calculate_blank_size(
    part_width: float, part_height: float,
    bends: List[Dict],
    thickness: float, material_key: str
) -> Dict:
    mat = MATERIALS[material_key]
    k = mat['k_factor']

    total_ba = sum(
        bend_allowance(b.get('angle_deg', 90.0),
                       b.get('r_inner', thickness),
                       thickness, k)
        for b in bends
    )

    flat_width  = part_width  + total_ba * 0.5
    flat_height = part_height + total_ba * 0.5

    return {
        'flat_width':  round(flat_width, 2),
        'flat_height': round(flat_height, 2),
        'total_ba':    round(total_ba, 3),
        'bend_count':  len(bends),
    }


# ── ストリップ工程設計 ─────────────────────────────────────────────────────────
def design_stations(
    blank: Dict, part_w: float, part_h: float,
    holes: List[Dict], bends: List[Dict],
    thickness: float, material_key: float
) -> List[Dict]:
    """工程一覧を返す"""
    mat = MATERIALS[material_key]
    clearance = mat['clearance_ratio'] * thickness  # 片側クリアランス

    stations = []

    # St.1 パイロット穴打ち抜き
    stations.append({
        'no': 1,
        'name': 'パイロット穴（位置決め）',
        'operation': 'pilot_hole',
        'description': f'φ{thickness*2:.1f} パイロット穴 × 2',
        'punch_force': _calc_punch_force(
            math.pi * thickness * 2, thickness, mat['shear_strength']),
    })

    # St.2 外形ノッチング（両側）
    stations.append({
        'no': 2,
        'name': '外形ノッチング',
        'operation': 'notch',
        'description': '両側キャリア切断、外形部分抜き',
        'punch_force': _calc_punch_force(
            (part_h + thickness * 4) * 2, thickness, mat['shear_strength']),
    })

    # St.3 内穴打ち抜き
    if holes:
        hole_perimeter = sum(2 * math.pi * h['r'] for h in holes[:4])
        stations.append({
            'no': 3,
            'name': f'内穴打ち抜き × {len(holes)}',
            'operation': 'hole_punch',
            'description': ', '.join(f'φ{h["r"]*2:.1f}' for h in holes[:4]),
            'punch_force': _calc_punch_force(
                hole_perimeter, thickness, mat['shear_strength']),
        })
        next_st = 4
    else:
        next_st = 3

    # 曲げ工程（1曲げ = 1工程）
    for i, bend in enumerate(bends):
        stations.append({
            'no': next_st + i,
            'name': f'曲げ {i+1} ({bend.get("angle_deg",90):.0f}°)',
            'operation': 'bend',
            'description': f'R{bend.get("r_inner", thickness):.1f} 曲げ、スプリングバック角度 +{_springback(bend.get("angle_deg",90), mat):.1f}°',
            'punch_force': _calc_bend_force(
                blank['flat_width'], thickness, mat['uts']),
        })
    next_st = next_st + len(bends)

    # 最終 切り落とし
    stations.append({
        'no': next_st,
        'name': '切り落とし（最終抜き）',
        'operation': 'cutoff',
        'description': f'部品切り離し、ピッチ {blank["flat_width"]+thickness*3:.1f} mm',
        'punch_force': _calc_punch_force(
            part_h * 2, thickness, mat['shear_strength']),
    })

    return stations


def _calc_punch_force(perimeter_mm: float,
                       thickness: float, shear_mpa: float) -> float:
    """打ち抜き力 (kN)"""
    return round(perimeter_mm * thickness * shear_mpa / 1000.0, 1)


def _calc_bend_force(width: float, thickness: float, uts: float) -> float:
    """V曲げ力 (kN) 簡易計算"""
    return round(width * thickness ** 2 * uts / (8 * (thickness + 5)) / 1000.0, 1)


def _springback(angle_deg: float, mat: Dict) -> float:
    """
    スプリングバック角度推定（経験式ベース）
    Δθ ≈ θ × (σy/E) × Cf
    Cf は材料の加工硬化係数に基づく経験値
    SPCC 90°: ~2-4°, SUS304: ~6-10°, Al合金: ~5-10°
    """
    # 目標値: SPCC≈3°, SUS304≈8°, A1050≈5°, A5052≈7°, C2680≈4° (90°, R/t=1)
    # cf = Δθ_target / (90 × σy/E) で逆算した経験係数
    cf_map = {
        'SPCC': 35, 'SUS304': 80, 'A1050': 110,
        'A5052': 28, 'C2680': 49,
    }
    sy = mat['yield_stress']
    cf = 35
    for key, m in MATERIALS.items():
        if abs(m['yield_stress'] - sy) < 1.0:
            cf = cf_map.get(key, 35)
            break
    return round(angle_deg * (sy / mat['E']) * cf, 1)


# ── SVG 生成 ──────────────────────────────────────────────────────────────────
def generate_svg(
    blank: Dict, stations: List[Dict],
    part_w: float, part_h: float,
    holes: List[Dict], bends: List[Dict],
    thickness: float, material_key: str,
    strip_width_ratio: float = 1.6,
) -> str:
    mat = MATERIALS[material_key]

    n_stations = len(stations)
    pitch      = blank['flat_width'] + thickness * 3.0
    carrier_w  = max(3.0, thickness * 2.0)   # キャリア幅
    strip_w    = part_h * strip_width_ratio   # ストリップ幅

    # SVG サイズ
    MARGIN     = 30
    ST_W       = max(pitch * 8, 60)   # 1工程あたりの幅 (px)
    SCALE      = min(ST_W / (pitch + 2), 4.0)
    total_w    = int(n_stations * ST_W + MARGIN * 2 + 80)
    total_h    = int(strip_w * SCALE + MARGIN * 2 + 120)

    # 色
    mat_color  = mat['color']
    cut_color  = '#FF6B6B'
    bend_color = '#4ECDC4'
    hole_color = '#FFE66D'
    bg_color   = '#1a1a2e'
    strip_color= mat_color

    lines = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                 f'width="{total_w}" height="{total_h}" '
                 f'viewBox="0 0 {total_w} {total_h}" '
                 f'style="background:{bg_color}; font-family:sans-serif;">')

    # フィード方向矢印
    arrow_y = MARGIN + 10
    lines.append(f'<text x="{MARGIN}" y="{arrow_y}" fill="#aaa" '
                 f'font-size="11">→ 送り方向</text>')

    strip_top = MARGIN + 25
    strip_bot = strip_top + int(strip_w * SCALE)

    # キャリア帯
    carrier_px = int(carrier_w * SCALE)
    lines.append(f'<rect x="{MARGIN + 80}" y="{strip_top}" '
                 f'width="{total_w - MARGIN - 80 - MARGIN}" height="{strip_bot - strip_top}" '
                 f'fill="{strip_color}" stroke="#888" stroke-width="0.8" opacity="0.6"/>')
    # 上下キャリア強調
    lines.append(f'<rect x="{MARGIN + 80}" y="{strip_top}" '
                 f'width="{total_w - MARGIN - 80 - MARGIN}" height="{carrier_px}" '
                 f'fill="{mat_color}" stroke="#666" stroke-width="0.5" opacity="0.8"/>')
    lines.append(f'<rect x="{MARGIN + 80}" y="{strip_bot - carrier_px}" '
                 f'width="{total_w - MARGIN - 80 - MARGIN}" height="{carrier_px}" '
                 f'fill="{mat_color}" stroke="#666" stroke-width="0.5" opacity="0.8"/>')

    # 各工程
    for i, st in enumerate(stations):
        sx = MARGIN + 80 + i * ST_W + 5
        cx = sx + ST_W // 2
        cy = (strip_top + strip_bot) // 2

        # 工程区切り線
        lines.append(f'<line x1="{sx + ST_W - 5}" y1="{strip_top - 5}" '
                     f'x2="{sx + ST_W - 5}" y2="{strip_bot + 5}" '
                     f'stroke="#555" stroke-width="0.8" stroke-dasharray="4,3"/>')

        # 工程番号
        lines.append(f'<circle cx="{cx}" cy="{strip_top - 14}" r="9" '
                     f'fill="#333" stroke="#666" stroke-width="1"/>')
        lines.append(f'<text x="{cx}" y="{strip_top - 10}" fill="#eee" '
                     f'font-size="10" text-anchor="middle">{st["no"]}</text>')

        op = st['operation']
        part_px_w = int(blank['flat_width'] * SCALE * 0.85)
        part_px_h = int(part_h * SCALE * 0.75)
        px0 = cx - part_px_w // 2
        py0 = cy - part_px_h // 2

        # 部品アウトライン（当工程での状態）
        if op == 'pilot_hole':
            # 素材矩形 + パイロット穴
            lines.append(f'<rect x="{px0}" y="{py0}" '
                         f'width="{part_px_w}" height="{part_px_h}" '
                         f'fill="{strip_color}" stroke="#aaa" stroke-width="1"/>')
            pilot_r = max(3, int(thickness * SCALE))
            for px_off in [int(part_px_w * 0.1), int(part_px_w * 0.9)]:
                lines.append(f'<circle cx="{px0 + px_off}" cy="{cy}" r="{pilot_r}" '
                             f'fill="{hole_color}" stroke="{cut_color}" stroke-width="1.5"/>')

        elif op == 'notch':
            # ノッチカット後の外形
            nw = max(4, int(part_px_w * 0.15))
            lines.append(f'<rect x="{px0 + nw}" y="{py0}" '
                         f'width="{part_px_w - nw*2}" height="{part_px_h}" '
                         f'fill="{strip_color}" stroke="#aaa" stroke-width="1"/>')
            lines.append(f'<rect x="{px0}" y="{py0}" width="{nw}" height="{part_px_h}" '
                         f'fill="{cut_color}" opacity="0.5" '
                         f'stroke="{cut_color}" stroke-width="1"/>')
            lines.append(f'<rect x="{px0 + part_px_w - nw}" y="{py0}" '
                         f'width="{nw}" height="{part_px_h}" '
                         f'fill="{cut_color}" opacity="0.5" '
                         f'stroke="{cut_color}" stroke-width="1"/>')

        elif op == 'hole_punch':
            # 内穴打ち抜き
            lines.append(f'<rect x="{px0}" y="{py0}" '
                         f'width="{part_px_w}" height="{part_px_h}" '
                         f'fill="{strip_color}" stroke="#aaa" stroke-width="1"/>')
            for j, h in enumerate(holes[:4]):
                hr = max(3, int(h['r'] * SCALE * 0.8))
                hcx = cx + int((h['cx'] - (blank['flat_width'] / 2)) * SCALE * 0.6)
                hcy = cy + int((h['cy'] - (part_h / 2)) * SCALE * 0.6)
                lines.append(f'<circle cx="{hcx}" cy="{hcy}" r="{hr}" '
                             f'fill="{hole_color}" stroke="{cut_color}" stroke-width="1.5"/>')

        elif op == 'bend':
            # 曲げ工程（断面ビュー）
            lines.append(f'<rect x="{px0}" y="{py0}" '
                         f'width="{part_px_w}" height="{part_px_h}" '
                         f'fill="{strip_color}" stroke="#aaa" stroke-width="1"/>')
            # 曲げ線
            bl_x = px0 + part_px_w // 2
            lines.append(f'<line x1="{bl_x}" y1="{py0}" x2="{bl_x}" y2="{py0 + part_px_h}" '
                         f'stroke="{bend_color}" stroke-width="2.5" stroke-dasharray="6,3"/>')
            # 曲げ角度ラベル
            angle = st.get('angle_deg', 90)
            lines.append(f'<text x="{bl_x + 4}" y="{cy - 4}" fill="{bend_color}" '
                         f'font-size="9">{int(st["name"].split("(")[-1].split("°")[0]) if "(" in st["name"] else 90}°</text>')

        elif op == 'cutoff':
            # 切り落とし → 完成品
            lines.append(f'<rect x="{px0}" y="{py0}" '
                         f'width="{part_px_w}" height="{part_px_h}" '
                         f'fill="{strip_color}" stroke="#4CAF50" stroke-width="2"/>')
            cut_x = px0 + part_px_w
            lines.append(f'<line x1="{cut_x}" y1="{py0 - 8}" x2="{cut_x}" y2="{py0 + part_px_h + 8}" '
                         f'stroke="{cut_color}" stroke-width="3"/>')
            # ✓マーク
            lines.append(f'<text x="{cx}" y="{cy + 4}" fill="#4CAF50" '
                         f'font-size="14" text-anchor="middle" font-weight="bold">✓</text>')

        # 工程名（下部）
        label_y = strip_bot + 16
        lines.append(f'<text x="{cx}" y="{label_y}" fill="#ccc" '
                     f'font-size="9" text-anchor="middle">{st["name"]}</text>')
        # 打ち抜き力
        lines.append(f'<text x="{cx}" y="{label_y + 12}" fill="#888" '
                     f'font-size="8" text-anchor="middle">{st["punch_force"]} kN</text>')

    # 凡例
    legend_y = strip_bot + 45
    legends = [
        (cut_color,  '打ち抜き'),
        (bend_color, '曲げ線'),
        (hole_color, '内穴'),
        ('#4CAF50',  '完成品'),
    ]
    lx = MARGIN + 80
    for color, label in legends:
        lines.append(f'<rect x="{lx}" y="{legend_y}" width="12" height="8" fill="{color}"/>')
        lines.append(f'<text x="{lx + 16}" y="{legend_y + 7}" fill="#aaa" font-size="9">{label}</text>')
        lx += 60

    # スケール表示
    scale_mm = 10.0
    scale_px = int(scale_mm * SCALE)
    sx_s = total_w - MARGIN - scale_px - 10
    lines.append(f'<line x1="{sx_s}" y1="{legend_y + 4}" '
                 f'x2="{sx_s + scale_px}" y2="{legend_y + 4}" '
                 f'stroke="white" stroke-width="2"/>')
    lines.append(f'<text x="{sx_s + scale_px//2}" y="{legend_y + 14}" '
                 f'fill="#aaa" font-size="9" text-anchor="middle">{scale_mm:.0f} mm</text>')

    lines.append('</svg>')
    return '\n'.join(lines)


def run(
    geom: Dict,
    material_key: str,
    thickness: float,
    bend_radius: float,
    bend_angle: float,
    strip_width_margin: float = 1.6,
) -> Dict:
    """ストリップレイアウト全計算の統合エントリポイント"""
    mat  = MATERIALS[material_key]
    dims = geom['dimensions']
    part_w = dims['width']
    part_h = dims['height']
    holes  = geom.get('holes', [])
    bends  = geom.get('bends', [])

    # 曲げ角度をユーザー指定で上書き
    for b in bends:
        b['angle_deg'] = bend_angle
        b['r_inner']   = bend_radius

    blank    = calculate_blank_size(part_w, part_h, bends, thickness, material_key)
    stations = design_stations(blank, part_w, part_h,
                                holes, bends, thickness, material_key)
    svg      = generate_svg(blank, stations, part_w, part_h,
                             holes, bends, thickness, material_key,
                             strip_width_margin)

    total_force = sum(s['punch_force'] for s in stations)
    press_tons  = round(total_force * 1.3 / 9.81, 1)   # 安全率 1.3

    return {
        'material':     MATERIALS[material_key],
        'blank':        blank,
        'stations':     stations,
        'svg':          svg,
        'summary': {
            'station_count':  len(stations),
            'pitch_mm':       round(blank['flat_width'] + thickness * 3.0, 2),
            'strip_width_mm': round(part_h * strip_width_margin, 2),
            'total_force_kN': round(total_force, 1),
            'press_capacity_ton': press_tons,
        },
    }
