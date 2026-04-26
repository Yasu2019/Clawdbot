【OpenClaw TACO++ 完全自律版】

目的:
  Terminal / Docker / CAE / Python / Node / n8n の長大ログを安全に圧縮し、
  AIエージェントのトークン爆発、Lost in the Middle、無限ループを抑制します。

同梱内容:
  1. Layer1 Guard       : ERROR/WARNING/CAE危険語を絶対保持
  2. Layer2 Evolve      : 圧縮ルールを自動生成・評価・昇格
  3. Layer3 Memory      : Qdrantへ圧縮ルールを長期保存
  4. Brake Controller   : 「情報不足」「同じコマンド反復」を検知して圧縮を緩和
  5. LiteLLM Adapter    : LLM投入前の観測ログを圧縮
  6. Langfuse Events    : 圧縮率、保護行数、ロールバック回数を記録
  7. Workflow Healer    : ループ検知時にn8n/Healerへ通知
  8. Portal Dashboard   : 127.0.0.1:8088配下へ置ける可視化カード

推奨配置:
  D:\Clawdbot_Docker_20260125\clawstack_v2\OpenClaw_TACOplusplus_AutoOps_UTF8

導入手順:
  1. このフォルダを clawstack_v2 直下に配置
  2. docker-compose.taco.yml を既存 compose と併用
     docker compose -f docker-compose.yml -f OpenClaw_TACOplusplus_AutoOps_UTF8/docker-compose.taco.yml up -d
  3. 動作確認
     python scripts/run_local_demo.py
  4. Portalカードを使う場合
     portal/taco_dashboard.html を既存 Portal の apps/taco_dashboard/index.html 等へコピー

安全方針:
  - CAEエラー、スタックトレース、コンパイルエラー、権限エラー、接続エラーは削除しません。
  - 圧縮ルールは confidence >= 0.80 かつ failures == 0 の場合のみ採用候補になります。
  - エージェントが full output / information missing を要求した場合、自動的に保守モードへ戻します。

注意:
  このZIPは既存OpenClawへ“上書き”せず、横置き統合する設計です。
  本番導入前に tests/sample_logs で圧縮結果を確認してください。
