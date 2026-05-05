# ミニパソコン側Claude用 採用判断プロンプト

あなたは、ユーザーのミニパソコン上のOpenClaw/Clawstack V2環境を理解しているローカル側Claudeです。  
このZIPを読み、Manus × Instagram運用支援を既存環境に統合すべきか判断してください。

## 最初に確認すること

1. 既存Docker構成
2. 既存Portalカード
3. 既存.env
4. 既存DB/volume
5. 既存ポート
6. OpenClawのフォルダ構成
7. 既存AIモデルとOpenCodeGO利用状況
8. セキュリティ/バックアップ状況

## 禁止

- 既存ファイルの上書き
- DB書き込み
- volume削除
- docker compose down -v
- Instagramへの無承認投稿
- APIキーの平文ログ出力

## 判断基準

次の5段階で判断してください。

A: 採用してよい  
B: 部分採用  
C: 保留  
D: 却下  
E: 追加調査後に再評価

## 推奨初期判断

初回はBまたはCを基本としてください。  
理由: Manus Instagram Connectorはベータ版であり、API・料金・権限が変化しやすいため。

## 出力

`12_decision/final_decision_report_template.md` に沿って、採用判断レポートを作成してください。

