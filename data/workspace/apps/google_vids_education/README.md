# Google Vids × OpenClaw 教育自動生成システム（本番ZIP）

目的: Google Vidsを「動画生成の出力装置」、OpenClaw/Clawstackを「現場ナレッジの頭脳」として使い、IATF教育・品質不具合・設備操作・作業標準の動画教材を半自動〜自律的に生成するための本番導入テンプレートです。

想定環境:
- Windows 11 Pro + Docker Desktop + WSL2
- GMKtec NucBox K10 / Clawstack unified構成
- Portal: http://localhost:8088
- OpenClaw Gateway: http://127.0.0.1:18789
- n8n: http://127.0.0.1:5679
- Node-RED: http://127.0.0.1:1880
- Qdrant: http://127.0.0.1:6333
- LiteLLM: http://127.0.0.1:4000
- Langfuse: http://127.0.0.1:3001
- Paperless-ngx: http://127.0.0.1:8000

重要方針:
1. Google Vidsは最終出力。事実判断はOpenClaw/RAG側で行う。
2. 外部AI/動画生成APIの使用は最小化する。
3. 社外秘・顧客名・図面番号・個人名は公開用動画では自動マスクする。
4. 動画化前に「根拠」「承認」「公開範囲」を必ず確認する。
5. 既存Portalカード・既存Docker Composeと衝突しない後付け方式を優先する。

推奨導入順:
1. docs/01_architecture.md を読む
2. docs/02_installation.md に従い配置
3. templates/education_video_brief.yaml を使い1本目の教材を作る
4. prompts/vids_prompt_templates.md をGoogle Vidsへ貼り付ける
5. checklists/release_checklist.md で公開可否を確認する

