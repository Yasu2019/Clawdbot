# 03_scoring_design - 採点設計

## 基本思想

0〜100点で採点します。  
点数が高いほど「作る価値が高い」です。

## 初期重み

| 項目 | 重み | 内容 |
|---|---:|---|
| buyer_pain | 25 | 読者が本当に困っているか |
| user_moat | 20 | 鈴木様の実務経験で差別化できるか |
| competition_weakness | 15 | 競合が強すぎないか |
| substitute_resistance | 15 | 無料情報だけで解決されないか |
| low_supplier_dependency | 10 | 外部APIや素材依存が低いか |
| platform_fit | 10 | 媒体とテーマが合っているか |
| production_feasibility | 5 | ミニパソコンで無理なく作れるか |

## 判定

| 点数 | 判定 |
|---:|---|
| 80〜100 | 本気実装・有料化候補 |
| 65〜79 | 小さく検証してから本実装 |
| 50〜64 | 無料記事・集客用なら可 |
| 35〜49 | 保留 |
| 0〜34 | 捨てる |

## 鈴木様向けボーナス

以下の語が含まれる場合は、差別化スコアを上げます。

- 品質保証
- IATF
- APQP
- PPAP
- NEXIV
- 検査成績書
- Excel
- VBA
- 不良率
- 品質月報
- OpenClaw
- Portal
- FreeCAD
- Blender
- PrePoMax
- CAE
- 製造業
