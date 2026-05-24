# MiniPC Content 5-Forces Gate / Portal Integration Pack

鈴木様のミニパソコン上の Portal ダッシュボードに、  
**Kindlebook生成 / note生成 / YouTube生成 / TikTok生成 / ミニゲーム生成** の前段階として追加するための  
「売れるテーマ判定ゲート」サンプル実装です。

## 目的

生成AIで記事・本・動画・ミニゲームを大量生成する前に、以下を判定します。

- 競合が強すぎないか
- AIで誰でも量産できる内容ではないか
- 無料情報や既存ツールで代替されないか
- API・外部サービス・著作権素材などに依存しすぎていないか
- 読者・視聴者・購入者が本当に困っていて、お金や時間を払う価値があるか
- 鈴木様の実務経験、品質保証、Excel/VBA、NEXIV、IATF、OpenClaw、3D/CAEと結び付くか

## 推奨用途

特に以下のようなテーマ選定に向きます。

- 製造業向け Excel VBA 自動化
- NEXIV 測定データ変換
- 品質月報、不良率、損失金額、メンテナンス記録の自動分析
- IATF16949 内部監査、是正処置、APQP/PPAP
- OpenClaw を使った品質保証業務の自動化
- Blender / FreeCAD / UE5 / CAE を使った製造業向け資料作成
- 現場教育用ミニゲーム、監査トレーニング、異常検出ゲーム

## フォルダ構成

```text
minipc_content_5forces_full/
  backend/                 FastAPI サンプルAPI
  cli/                     コマンドライン実行サンプル
  configs/                 採点ルール、媒体ルール
  data/                    UTF-8サンプルデータ
  docs/                    導入・運用・文字化け防止資料
  portal-card/             PortalカードのHTML/manifestサンプル
  scripts/                 Windows実行用スクリプト
  tests/                   簡易テスト
  docker-compose.yml       Docker Compose起動例
```

## Windowsでの最短実行

PowerShellを開き、このフォルダで実行します。

```powershell
.\scripts\run_windows_utf8.ps1
```

または cmd.exe では:

```bat
scripts\run_windows_utf8.bat
```

## Dockerで起動

```powershell
docker compose up --build
```

起動後:

- API: http://localhost:8765
- ヘルスチェック: http://localhost:8765/health
- APIドキュメント: http://localhost:8765/docs

## 文字化け防止方針

- 全ファイルは UTF-8 で作成
- Python 実行時は `PYTHONUTF8=1`
- Windows cmd は `chcp 65001`
- CSV は `utf-8-sig` 出力にも対応
- ファイル名は原則 ASCII にして、本文を日本語化
- README、設定、サンプルCSVは UTF-8

## 重要

このパックは「テーマ採用判断」と「企画生成補助」のサンプルです。  
YouTube、TikTok、note、Amazon KDPなどの最新ルールは変わる可能性があるため、実運用前に必ず各サービスの最新ポリシーを確認してください。

会社情報、図面、顧客情報、個人情報、内部監査資料、Gmail内容などは、外部APIや外部サービスに送らない運用を前提にしてください。
