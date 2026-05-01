# 🎬 Motion Lab - Unified Cinematic MoCap Studio

既存の Motion Lab と Cinematic MoCap ワークフローを統合した、Clawstack 映画級動画制作ハブです。

## 🌟 主な機能
- **AI 動作構成**: 台本から秒単位の「動作表 (Motion Table)」を自動生成
- **プロフェッショナル MoCap**: FreeMoCap / Rokoko 等のデータのリターゲティング
- **映画級仕上げ**: Blender によるライティング調整 & DaVinci Resolve によるグレーディング
- **品質保証 (Visual QA)**: インシデント INC-066 に基づく厳格な品質チェックリスト

## 📜 入力プロトコル (Honkiban Schema)
本アプリは `03_JSON_SCHEMA_TEMPLATE.json` に準拠した入力を受け付けます。
AI 監督が生成したショット指示に基づき、以下の要素を決定します：
- **Subject**: キャラクターのアイデンティティ固定 (Identity Lock)
- **Camera**: シネマティックなカメラワーク (Tracking Shot 等)
- **Exclusions**: 手足の崩れ、浮き、無効なフレームの排除

## ✅ 品質チェック (Visual QA)
インシデント **INC-066 (無効なフレームの垂れ流し)** を防止するため、レンダリング後に必ず以下のチェックを実施してください。詳細は `05_quality_check/animation_qc_checklist.md` を参照。

1. **足の滑り (Foot Sliding)**: 地面にしっかり着いているか
2. **重心の安定**: 物理的に不自然な姿勢になっていないか
3. **フレームの有効性**: すべてのフレームが黒画面や不自然なクローズアップになっていないか
4. **一貫性**: ショット間でキャラクターの容姿が維持されているか

## 🛠 ツールセット
- **Blender (Rigify)**: キャラクター制御
- **FreeMoCap / Mixamo**: モーションソース
- **DaVinci Resolve**: 最終編集・カラーグレーディング
- **DeepSeek Pro**: 台本解析・ショット構成

---
*Created: 2026-05-01 (Clawstack Cinematic Fusion Update)*
