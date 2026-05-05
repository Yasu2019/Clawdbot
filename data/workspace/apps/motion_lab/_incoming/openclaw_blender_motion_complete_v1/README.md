# OpenClaw × Blender × Mixamo/BVH Motion Pipeline 完全版 V1

目的：Blender MCP を中核に、Mixamo / BVHライブラリ / VRM / Rokoko系モーションを必ず取り込み、台本から自然な3Dキャラクター動作を生成・検証・修正できる現場投入向けパイプラインを構築する。

このZIPは「いきなり既存Clawstackに上書き統合しない」前提です。まず現状確認、ポート/フォルダ/コンテナ衝突確認、Codex/Claude/OpenCodeGOによる採否判断を行ってから段階導入してください。

## 重要方針
- Blender本体や既存Clawstackを直接改変しない。
- Mixamo/BVH/VRM/Rokokoのモーション資産を必ず候補として探索・変換・適用する。
- 映画級を一発生成とは考えず、AI粗生成 → モーション選定 → リターゲット → 足滑り/手めり込み/重心検査 → 人間確認 の反復で品質を上げる。
- OpenCodeGO/DeepSeek/Qwen/Codexは「判断・修正提案・スクリプト生成」に使い、Blender実行前にdry-runとバックアップを必須にする。

## 推奨フォルダ配置例
D:\Clawdbot_Docker_20260125\clawstack_v2\extensions\blender_motion_pipeline

## 最初に読む順番
1. docs/00_overview.md
2. docs/01_environment_audit.md
3. docs/02_motion_sources_mixamo_bvh_rokoko_vrm.md
4. docs/03_pipeline_sop.md
5. codex/CODEX_REVIEW_REQUEST.md
6. prompts/opencodego_master_prompt.md
