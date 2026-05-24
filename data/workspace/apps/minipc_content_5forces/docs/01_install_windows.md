# 01_install_windows - Windows導入手順

## 1. 前提

- Windows 10/11
- Python 3.11 以上推奨
- Docker Desktop 任意
- VS Code 任意

## 2. PowerShellで実行

このフォルダを開いて:

```powershell
.\scripts\run_windows_utf8.ps1
```

このスクリプトは以下を行います。

- UTF-8実行環境の指定
- 仮想環境 `.venv` の作成
- 依存パッケージのインストール
- サンプルCSVの採点
- FastAPIサーバーの起動案内

## 3. cmd.exeで実行

```bat
scripts\run_windows_utf8.bat
```

## 4. Dockerで起動

```powershell
docker compose up --build
```

## 5. 文字化けした場合

PowerShellで以下を実行してください。

```powershell
$env:PYTHONUTF8="1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

cmd.exeの場合:

```bat
chcp 65001
set PYTHONUTF8=1
```
