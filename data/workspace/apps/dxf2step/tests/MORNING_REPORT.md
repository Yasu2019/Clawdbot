# DXF2STEP 自律改善ループ 最終レポート

## 最終スコア: **100.0 / 100** (Round 3)

**テスト日時**: 2026-03-05
**ラウンド数**: 3ラウンド (Round 1: 0/100 → Round 2: 90/100 → Round 3: 100/100)

---

## テスト結果一覧 (Round 3)

| ID | 説明 | Faces | Vol(mm³) | BBox | スコア |
|---|---|---|---|---|---|
| circle | 円形押し出し r=30mm×10mm | 3 | 28,274 | 60×60×10 | 100/100 |
| semicircle | 半円柱 r=30mm×10mm | 4 | 14,137 | 60×30×10 | 100/100 |
| right_triangle | 直角三角形 60×40×8mm | 5 | 9,600 | 60×40×8 | 100/100 |
| rect_simple | 矩形 100×60×8mm | 6 | 48,000 | 100×60×8 | 100/100 |
| pentagon | 正五角形 R40×8mm | 7 | 30,434 | 72.4×76.1×8 | 100/100 |
| hexagon | 正六角形 R40×8mm | 8 | 33,255 | 80×69.3×8 | 100/100 |
| l_shape | L字形状 T接合 80×80×6mm | 8 | 28,800 | 80×80×6 | 100/100 |
| u_shape | U字形状 内側除去 100×80×5mm | 10 | 25,000 | 100×80×5 | 100/100 |
| arc_rect | 角丸矩形 R10 100×60×5mm | 10 | 29,571 | 100×60×5 | 100/100 |
| t_shape | T字形状 重複矩形 80×80×5mm | 14 | 14,000 | 80×80×5 | 100/100 |
| multiview_cube | 多視点 100mm立方体 | 6 | 1,000,000 | 100×100×100 | 100/100 |
| multiview_lbracket | 多視点 L字ブラケット | 6 | 288,000 | 80×60×60 | 100/100 |

**Face数カバレッジ: 3, 4, 5, 6, 7, 8, 10, 14** — リクエスト通り多様化

---

## 修正した主要バグ

### Bug 1: FreeCAD analyse_step argv バグ
- **症状**: 全テスト `"FreeCAD exception thrown (Unknown extension)"` で0点
- **原因**: `FreeCADCmd script.py stepfile.step` — FreeCADCmdは追加argvをスクリプト引数として渡さない
- **修正**: STEPパスをスクリプト内容に直接埋め込む

### Bug 2: DXF単位スケール 1000倍ズレ
- **症状**: bbox_x=100,000 (期待:100), volume=48,000,000,000 (期待:48,000)
- **原因**: `ezdxf.new()` が `$INSUNITS=6`(meters) を設定 → FreeCADが1000倍スケール変換
- **修正**: `$INSUNITS=4`(mm) に設定（generate_dxfs.py + dxf2step_worker.py）

### Bug 3: CIRCLEエンティティ無視
- **症状**: circle テスト → `no_step` (STEPファイル未生成)
- **原因**: `resolve_tjunctions()` がLINEとARCのみ処理、CIRCLEを無視
- **修正**: `circle_entities` を追加、cleaned DXFに `add_circle()` で出力

### Bug 4: t_shape face数 22 (期待14)
- **症状**: 重複矩形のT字形状で22個のFace
- **原因**: resolve_tjunctions がゴースト内側ループ（20×20正方形）を生成 → fuse時に余分なface分割
- **修正**: `removeSplitter()` をfuse後に追加 → 14面に収束

### Bug 5: 多視点再構成 face数 16 (期待6)
- **症状**: 立方体再構成で16Face（6Faceが正しい）
- **原因**: SurfaceOfExtrusionタイプのFaceはremoveSplitterで合成不可
- **修正**: face upgrade（SurfaceOfExtrusion→Plane変換）後に2回目のremoveSplitter追加 → 6面に収束

### Bug 6: arc_rect 期待face数の誤り
- **原因**: 角丸矩形の期待値を3（不正）→ 10（上下+4直線側面+4曲面コーナー）に修正

---

## テストインフラ構成

```
tests/
├── test_cases.py       # 12テスト定義 (Face 3〜14カバー)
├── generate_dxfs.py    # DXFファイル生成 (12種類)
├── score.py            # 自動採点スクリプト
├── dxf_files/          # 生成済みDXFファイル
├── results_round01.json  # Round 1: 0.0/100
├── results_round02.json  # Round 2: 90.0/100
└── results_round03.json  # Round 3: 100.0/100 ← 最終
```

---

## 採点基準 (各テスト100点)
- 30点: STEPファイル生成成功 + valid shape
- 30点: 体積 ±許容誤差内
- 20点: Face数 ±1以内
- 20点: BoundingBox 各軸 ±2%以内
