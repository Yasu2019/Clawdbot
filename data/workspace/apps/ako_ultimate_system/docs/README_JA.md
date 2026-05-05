# AKO Ultimate System 最終統合版

Corpus2Skill、LightRAG、GraphRAG、通常RAG、Query Router、Evidence Verifier、Cache、Failure Learning、Benchmark、Excel/PDF/画像/動画プロセッサ雛形を統合したOpenClaw向け拡張パッケージです。

## 目的
- IATF/規定/手順書/検査要領書/議事録/不適合報告書を根拠付きで探索
- 質問タイプごとに最適エンジンを自動選択
- 失敗ログから改善候補を残す

## 導入方針
既存Clawstackへ直接上書きせず、extensions配下に配置してください。Codex/Claude/OpenCodeGOに採用可否を判断させてください。

## 実行
```bash
pip install pyyaml pandas pymupdf
python main.py
```
