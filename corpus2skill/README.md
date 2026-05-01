# Corpus2Skill × OpenClaw 超本気版 統合パッケージ

対象環境: GMKtec NucBox K10 / Windows 11 Pro / Docker Desktop + WSL2 / clawstack-unified

目的:
- 従来RAGの「似ている文章を拾う」方式から、AIが文書構造を理解して探索する Corpus2Skill 型へ拡張
- IATF 16949、社内品質文書、QC工程表、図面PDF、STEP/3Dモデル、過去不具合記録を横断して根拠付き回答を行う
- Qdrantベクトル検索は捨てず、構造探索 + ベクトル検索 + 原文ID追跡のハイブリッドにする

最重要方針:
1. 既存Clawstackを壊さない
2. 既存Qdrant/Paperless/OpenClaw/Langfuseを活用する
3. API消費を最小化し、ローカルLLM優先でツリー生成する
4. 引用元IDを最後まで保持する
5. IATF監査・品質保証・図面解釈で使える証跡を残す

構成:
- docs/: 設計書、運用手順、現場投入ガイド
- config/: 環境変数、分類ルール、プロンプト
- schemas/: ツリー、ノード、証跡、探索ログのJSONスキーマ
- services/: Tree Builder / Navigator / Evidence Tracker / API Gateway
- portal/: OpenClaw Portal追加カード
- n8n/: ワークフロー雛形
- examples/: IATF、図面、QC工程表向けサンプル
- tests/: 動作確認用テスト

導入順序:
1. docs/00_DEPLOYMENT_GUIDE.md を読む
2. .env.example を .env にコピーして既存Clawstackに合わせる
3. docker-compose.override.corpus2skill.yml を既存composeに追加
4. scripts/smoke_test.sh を実行
5. Portalカードを既存Portalに追加

