# QMS Audit Protocol Bundle - Complete

このZIPは、QMS文書矛盾監査アプリを Claude Code / Codex / Antigravity に実装依頼するための**完全版プロトコル集**です。

## 同梱内容
- `complete_protocol.md`  
  統合済みの完全版実装プロトコル
- `claude_code_final_prompt.md`  
  Claude Code にそのまま渡せる最終依頼文
- `existing_system_audit.md`  
  実装前の既存Docker/既存コード監査テンプレート
- `conflict_check_report.md`  
  衝突確認レポート雛形
- `integration_plan.md`  
  統合計画雛形

## 特徴
- ローカルLLM丸投げ禁止
- Rule-based 主体
- 手順書 vs 帳票 不足項目比較あり
- 内容矛盾候補検出あり
- 修正提案自動生成あり
- IATF要求事項観点チェックあり
- 既存Docker/既存コードとの衝突回避を必須化

## 使い方
1. まず `complete_protocol.md` を確認
2. Claude Code に `claude_code_final_prompt.md` と `complete_protocol.md` を渡す
3. 実装開始前に `existing_system_audit.md` を埋めさせる
4. `conflict_check_report.md` と `integration_plan.md` を作らせてから着手させる
