# Anijam QA Autonomous Protocol Pack

このZIPは、**Anijam を用いた QA / IATF / 社内教育向け動画生成**を、できるだけ自律的に回すための実装・運用プロトコル集です。

## 同梱内容
- `01_master_protocol.md` : 完全自律版の全体方針・手順
- `02_anijam_workflow.md` : Anijam実行フロー
- `03_n8n_automation_design.md` : 自動化設計
- `04_rag_integration_design.md` : RAG連携設計
- `05_governance_and_safety.md` : ガバナンス・安全策
- `06_commercial_use_risk_note.md` : 商用利用・権利注意点
- `templates/` : 監査、是正、不良解析、教育用のテンプレート
- `prompts/` : そのまま使えるプロンプト雛形
- `config/` : JSON/YAML設定例
- `workflows/` : n8n向けの擬似フロー仕様
- `checklists/` : 導入・運用チェックリスト

## 想定用途
- IATF内部監査教育動画
- 是正処置教育動画
- 不良事例の再発防止教材
- 作業標準・工程説明動画
- 顧客説明用の社内下書き動画

## 前提
- Anijam は外部SaaSとして利用
- 社内資料は RAG / Paperless / Qdrant 等から取得可能
- 最終公開前に人間レビューを必須化

