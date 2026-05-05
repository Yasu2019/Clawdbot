# 01 アーキテクチャ

## 全体像

画面録画MP4
  -> ffmpeg分割
  -> scene detect / keyframe抽出
  -> OCR候補抽出
  -> 画像差分・画面遷移検出
  -> OpenCodeGOモデルで手順化
  -> チャンク統合
  -> 品質/IATF観点の注意点付与
  -> HTML/Markdown/PDF/Word用出力

## 役割分担

### ローカル処理
- 動画分割
- 重要フレーム抽出
- OCR
- 画像比較
- HTML/PDF生成

### OpenCodeGO AIモデル
- 操作内容の文章化
- 手順の統合
- 重複削除
- 注意点・確認項目の生成
- 品質/IATF教育向け補足

### Codex/Claude/Gemini
- 既存環境調査
- 統合可否判断
- コードレビュー
- 危険操作の停止判断

## 推奨モデル方針
| 用途 | 第一候補 | 第二候補 |
|---|---|---|
| コード生成 | DeepSeek Coder系 | Qwen Coder系 |
| 日本語手順書 | DeepSeek Pro/Chat系 | Qwen Instruct系 |
| 長文統合 | DeepSeek Pro | Qwen Long Context系 |
| ローカル補助 | qwen3:8b | qwen2.5-coder:7b |

## 1時間動画対応
動画を5分または10分単位に分割する。各チャンクごとに以下を作る。
- chunk_001_frames/
- chunk_001_ocr.json
- chunk_001_steps.md
- chunk_001_risks.md

最後に全体統合する。
