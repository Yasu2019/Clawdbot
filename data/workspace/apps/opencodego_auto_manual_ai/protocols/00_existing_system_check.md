# 00 既存システム全面確認プロトコル

Codex/Claude/Antigravity/OpenCodeGO実行前に必ず実施すること。

## 1. 禁止事項
- 既存Docker volumeを削除しない
- 既存DBへ書き込みしない
- docker compose down -v を実行しない
- rm -rf を使わない
- 既存.envを上書きしない
- 既存Portal設定を直接編集しない。必ずバックアップを作る

## 2. 調査対象
- D:\\Clawdbot_Docker_20260125
- clawstack_v2
- docker-compose*.yml
- .env / .env.example
- Portal dashboard card定義
- Ollamaモデル一覧
- OpenCodeGO設定
- 既存の動画/画像/OCR/帳票生成機能
- 既存のMOST/サーブリッグ/スパゲッティ図解析コード

## 3. 調査コマンド例 Windows PowerShell
```powershell
cd D:\Clawdbot_Docker_20260125
Get-ChildItem -Recurse -Filter "docker-compose*.yml" | Select-Object FullName
Get-ChildItem -Recurse -Include "*.env","*.json","*.yml","*.yaml" | Select-Object FullName
```

## 4. Docker確認
```powershell
docker ps -a
docker compose ls
docker volume ls
```

## 5. 採否判断
| 判定 | 条件 | 実施内容 |
|---|---|---|
| 完全採用 | 既存と競合せず、Portal追加だけで運用可能 | 新規サービスとして追加 |
| 部分採用 | OCRや動画処理など一部が重複 | 既存機能を優先し、不足部分だけ追加 |
| 保留 | DB/volume/port競合、機密リスクが高い | docsだけ保存し実装しない |

## 6. 推奨ポート
- Auto Manual UI: 8094
- Worker API: 8095
- 出力静的ビューア: 8096

既存ポートと競合したら必ず変更する。
