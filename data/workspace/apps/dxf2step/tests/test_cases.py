"""
Test case definitions for DXF2STEP scoring.
Each test: generate DXF → convert → score geometry.

Scoring per test (100 pts each):
  30  STEP file generated without error
  30  Volume within 5% of expected
  20  Face count == expected (±1 tolerance)
  20  Bounding box within 2% of expected per axis

Overall score = average across all cases.
Face coverage: 3, 4, 5, 6, 7, 8, 8, 10, 10, 14, 6, 6
"""
import math

# ─── Helper constants ─────────────────────────────────────────────────────────
_R5 = 40   # pentagon circumradius
_R6 = 40   # hexagon circumradius

TESTS = [
    # ── 3 faces ───────────────────────────────────────────────────────────────
    {
        "id": "circle",
        "desc": "円形押し出し r=30mm 厚み10mm (3面)",
        "thickness": 10.0,
        "expected_volume": math.pi * 30**2 * 10,     # ≈ 28 274 mm³
        "expected_faces": 3,
        "expected_bbox": (60.0, 60.0, 10.0),
        "vol_tol": 0.03,
        "bbox_tol": 0.02,
    },
    # ── 4 faces ───────────────────────────────────────────────────────────────
    {
        "id": "semicircle",
        "desc": "半円柱 r=30mm 厚み10mm (4面: 上下+曲面+平面)",
        "thickness": 10.0,
        "expected_volume": math.pi * 30**2 / 2 * 10,  # ≈ 14 137 mm³
        "expected_faces": 4,
        # x: -30..30=60, y: 0..30=30, z: 0..10
        "expected_bbox": (60.0, 30.0, 10.0),
        "vol_tol": 0.03,
        "bbox_tol": 0.02,
    },
    # ── 5 faces ───────────────────────────────────────────────────────────────
    {
        "id": "right_triangle",
        "desc": "直角三角形押し出し 60×40mm 厚み8mm (5面)",
        "thickness": 8.0,
        "expected_volume": 0.5 * 60 * 40 * 8,         # 9 600 mm³
        "expected_faces": 5,
        "expected_bbox": (60.0, 40.0, 8.0),
        "vol_tol": 0.02,
        "bbox_tol": 0.02,
    },
    # ── 6 faces ───────────────────────────────────────────────────────────────
    {
        "id": "rect_simple",
        "desc": "単純矩形押し出し 100×60×8mm (6面)",
        "thickness": 8.0,
        "expected_volume": 100 * 60 * 8,              # 48 000 mm³
        "expected_faces": 6,
        "expected_bbox": (100.0, 60.0, 8.0),
        "vol_tol": 0.02,
        "bbox_tol": 0.02,
    },
    # ── 7 faces ───────────────────────────────────────────────────────────────
    {
        "id": "pentagon",
        "desc": "正五角形押し出し R=40mm 厚み8mm (7面)",
        "thickness": 8.0,
        # Regular pentagon: Area = (n/2)*R²*sin(2π/n), n=5, R=40
        "expected_volume": (5 / 2) * _R5**2 * math.sin(2 * math.pi / 5) * 8,
        "expected_faces": 7,
        # Vertices at 0°,72°,144°,216°,288° — R=40:
        #   x range: R*cos(144°) to R → 40*cos(144°)=-32.36 to 40 → width=72.36
        #   y range: -R*sin(72°) to +R*sin(72°) → height=2*40*sin(72°)=76.08
        "expected_bbox": (
            2 * _R5 * math.sin(2 * math.pi / 5),   # ≈ 76.08 (sorted desc = largest)
            _R5 * (1 + math.cos(math.pi / 5)),      # ≈ 72.36
            8.0,
        ),
        "vol_tol": 0.03,
        "bbox_tol": 0.03,
    },
    # ── 8 faces ───────────────────────────────────────────────────────────────
    {
        "id": "hexagon",
        "desc": "正六角形押し出し R=40mm 厚み8mm (8面)",
        "thickness": 8.0,
        # Regular hexagon: Area = (3√3/2)*R², R=side=circumradius=40
        "expected_volume": (3 * math.sqrt(3) / 2) * _R6**2 * 8,  # ≈ 33 255 mm³
        "expected_faces": 8,
        # x: -40..40=80, y: -40*sin(60°)..40*sin(60°)=69.28
        "expected_bbox": (80.0, 2 * _R6 * math.sin(math.pi / 3), 8.0),  # (80, 69.28, 8)
        "vol_tol": 0.02,
        "bbox_tol": 0.02,
    },
    {
        "id": "l_shape",
        "desc": "L字形状 (T接合除去テスト) 厚み6mm (8面)",
        "thickness": 6.0,
        # Outer 80×80 − 40×40 top-right corner: Area = 4800 mm²
        "expected_volume": 4800 * 6,               # 28 800 mm³
        "expected_faces": 8,
        "expected_bbox": (80.0, 80.0, 6.0),
        "vol_tol": 0.04,
        "bbox_tol": 0.02,
    },
    # ── 10 faces ──────────────────────────────────────────────────────────────
    {
        "id": "u_shape",
        "desc": "U字形状 (内側矩形除去) 厚み5mm (10面)",
        "thickness": 5.0,
        # Outer 100×80 − inner 60×50: Area = 5000 mm²
        "expected_volume": 5000 * 5,               # 25 000 mm³
        "expected_faces": 10,
        "expected_bbox": (100.0, 80.0, 5.0),
        "vol_tol": 0.05,
        "bbox_tol": 0.02,
    },
    {
        "id": "arc_rect",
        "desc": "角丸矩形 R10コーナー 厚み5mm (10面: 上下+4直+4曲)",
        "thickness": 5.0,
        # Area ≈ 100*60 − (4−π)*10² ≈ 5685 mm²
        "expected_volume": (100 * 60 - (4 - math.pi) * 10**2) * 5,
        "expected_faces": 10,   # top + bottom + 4 flat sides + 4 curved corners
        "expected_bbox": (100.0, 60.0, 5.0),
        "vol_tol": 0.05,
        "bbox_tol": 0.02,
    },
    # ── 14 faces ──────────────────────────────────────────────────────────────
    {
        "id": "t_shape",
        "desc": "T字形状 (重複矩形T接合) 厚み5mm (14面)",
        "thickness": 5.0,
        # Vertical 20×80 + horizontal 80×20 overlapping: Area=2800 mm²
        "expected_volume": 2800 * 5,               # 14 000 mm³
        "expected_faces": 14,   # top + bottom + 12 side faces (after removeSplitter)
        "expected_bbox": (80.0, 80.0, 5.0),
        "vol_tol": 0.05,
        "bbox_tol": 0.02,
    },
    # ── Multi-view reconstruction (6 faces each) ───────────────────────────────
    {
        "id": "multiview_cube",
        "desc": "多視点再構成: 正面+上面 → 100mm立方体 (6面)",
        "thickness": 100.0,
        "expected_volume": 100**3,                 # 1 000 000 mm³
        "expected_faces": 6,
        "expected_bbox": (100.0, 100.0, 100.0),
        "vol_tol": 0.05,
        "bbox_tol": 0.05,
        "multiview": True,
    },
    {
        "id": "multiview_lbracket",
        "desc": "多視点再構成: L字ブラケット 正面+上面 (6面)",
        "thickness": 60.0,
        # Front 80×60 ∩ Top 80×60 → 80×60×60 box
        "expected_volume": 80 * 60 * 60,           # 288 000 mm³
        "expected_faces": 6,
        "expected_bbox": (80.0, 60.0, 60.0),
        "vol_tol": 0.05,
        "bbox_tol": 0.05,
        "multiview": True,
    },
    # ── 13. Mold Plate with Hole (through hole) ──────────────────────────────
    {
        "id": "mold_plate_hole",
        "desc": "金型プレート: 100×100×20mm プレート中央に r=20mm の貫通穴",
        "thickness": 20.0,
        # Plate (100*100*20) - Cylinder (pi*20^2*20)
        "expected_volume": (100 * 100 - math.pi * 20**2) * 20,  # ≈ 174 867 mm³
        "expected_faces": 7,   # top, bottom, 4 outer sides, 1 inner cylinder
        "expected_bbox": (100.0, 100.0, 20.0),
        "vol_tol": 0.05,
        "bbox_tol": 0.02,
    },
    # ── 14. Counterbore (layered hole) ───────────────────────────────────────
    {
        "id": "counterbore_test",
        "desc": "座グリ穴: 100×100×20mm プレートに Φ40(深さ10)+Φ20(貫通)の座グリ",
        "thickness": 20.0,
        # Vol = Plate(100*100*20) - Cap(pi*20^2*10) - Hole(pi*10^2*10)
        "expected_volume": (100*100*20) - (math.pi*20**2*10) - (math.pi*10**2*10), 
        "expected_faces": 10,  # top(hole), bottom(hole), 4 sides, 2 cyl internal, 1 annular step
        "expected_bbox": (100.0, 100.0, 20.0),
        "vol_tol": 0.05,
        "bbox_tol": 0.02,
    },
    # ── 15. U-Bend Product (Reconstruction) ──────────────────────────────────
    {
        "id": "u_bend_product",
        "desc": "U字曲げ製品: 正面U字型(厚み5) × 奥行き50mm",
        "thickness": 50.0,
        # Area ≈ Outer(60x40)-Inner(50x35) = 2400-1750 = 650 mm^2
        "expected_volume": 650 * 50,               # 32 500 mm³
        "expected_faces": 10,
        "expected_bbox": (60.0, 40.0, 50.0),
        "vol_tol": 0.08,
        "bbox_tol": 0.05,
    },
]
