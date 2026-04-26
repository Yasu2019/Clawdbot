# Windows側 LTspice 導入手順

## 目的

LTspiceの回路図編集・波形確認はWindowsホスト側で安定運用し、Docker側は自動解析サービスとしてngspiceを中心に使います。

## 手順

### 1. 公式ページを開く

PowerShellで以下を実行します。

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\01_open_official_download_page.ps1
```

Analog Devices公式ページから Windows 10/11 64bit版をダウンロードして通常インストールしてください。

### 2. LTspice実行ファイルを検出

```powershell
.\02_check_ltspice_cli.ps1
```

検出結果は以下に保存されます。

```text
%USERPROFILE%\.openclaw_spice_lab\ltspice_path.txt
```

### 3. バッチ実行テスト

```powershell
.\03_run_ltspice_batch_example.ps1
```

`examples\rc_lowpass_ltspice.cir` をLTspiceでバッチ実行し、`.raw` / `.log` の生成を確認します。

## 方針

- GUI編集: Windows LTspice
- 自動実行: Windows LTspiceバッチ、またはDocker ngspice
- OpenClaw統合: まずngspice APIを優先
- ADI専用モデルを使う必要がある場合だけ、LTspiceバッチ連携を追加

## 注意

LTspiceのインストール場所はバージョンやインストール方法で変わる場合があります。このパックの検出スクリプトは複数の一般的なパスを探索します。
