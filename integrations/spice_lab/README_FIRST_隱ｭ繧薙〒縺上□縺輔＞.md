# OpenClaw SPICE Lab / LTspice + ngspice 統合パック 2026-04-26_v1

このZIPは、鈴木様のMiniPC / Windows 11 / Docker Desktop / Clawstack 環境に、電子回路シミュレーション機能を安全に追加するための導入パックです。

## 結論

推奨構成は次の通りです。

```text
Windowsホスト側 : LTspice公式版を通常インストール
Docker側        : ngspice + Python + FastAPI の解析サービス
OpenClaw側      : Portalカード / API連携 / RAG化用レポート出力
必要時のみ      : Windows LTspiceをバッチ実行で呼び出す
```

LTspice本体のインストーラーは同梱していません。Analog Devices公式サイトから取得してください。再配布条件や最新版維持のため、このZIPでは公式ページを開くスクリプトと検出スクリプトのみを入れています。

## まず実行する順番

1. `00_windows_ltspice/README_windows_LTspice.md` を読む
2. Windows PowerShellで `00_windows_ltspice/01_open_official_download_page.ps1` を実行
3. LTspiceを通常インストール
4. `00_windows_ltspice/02_check_ltspice_cli.ps1` で実行ファイルの検出
5. Docker側で `01_docker_ngspice_service/docker-compose.ngspice.yml` を起動
6. `03_protocols/01_codex_antigravity_implementation_protocol.md` をCodex / Antigravity / Claudeへ渡し、既存Clawstackに統合

## 既存Clawstackへいきなり上書きしないでください

このパックは、既存の `D:\Clawdbot_Docker_20260125` へ直接上書きする前提ではありません。まず任意の作業フォルダで起動確認し、その後、Codex / Antigravityに差分統合させる構成です。

推奨配置例:

```text
D:\Clawdbot_Docker_20260125\integrations\spice_lab
```

## ポート

Docker側APIの既定ポートは `127.0.0.1:8765` です。競合する場合は `.env` または compose の `SPICE_LAB_PORT` を変更してください。

## できること

- ngspiceによる `.cir` / `.net` 実行
- RCフィルタ、分圧、保護回路、センサー入力フィルタの例
- FastAPI経由でOpenClawから解析実行
- 解析ログ、測定値、CSV、Markdownレポート保存
- 将来的なQdrant / Paperless / Docling / RAG登録を想定した出力
- Windows上のLTspiceバッチ実行との接続プロトコル

## できないこと / やらないこと

- LTspice公式インストーラーの同梱
- LTspice GUIをLinux Docker内で常用する構成
- 既存Clawstackファイルの無条件上書き
- 外部へポート公開する構成

## 文字化け対策

- `.ps1` / `.bat` は UTF-8 を想定
- `.bat` は `chcp 65001` を先頭に設定
- 日本語説明はMarkdown中心
- Windowsで文字化けする場合は VS Code で UTF-8 として開いてください
