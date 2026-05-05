# 01 既存環境確認 SOP

既存のClawstack/OpenClaw環境を壊さないため、導入前に必ず確認する。

## Windows PowerShell確認
```powershell
cd D:\Clawdbot_Docker_20260125\clawstack_v2
pwd
docker ps -a
docker compose ps
docker network ls
docker volume ls
```

## ポート衝突確認
```powershell
netstat -ano | findstr ":8081"
netstat -ano | findstr ":8083"
netstat -ano | findstr ":6333"
netstat -ano | findstr ":9000"
netstat -ano | findstr ":11434"
```

## Blender確認
```powershell
where blender
blender --version
```

## Python確認
```powershell
python --version
pip --version
```

## 導入禁止条件
以下の場合、統合を止めてCodexに判断させる。

- Blenderの既存アドオンが動作不安定
- 既存Portalのカード定義形式が不明
- Docker volume名が衝突する
- 既存MCP設定ファイルの場所が不明
- 既存OpenClawが本番業務DBへ書き込み権限を持っている

## 安全原則
- 最初は `sandbox_motion_test` フォルダでのみ実行
- 既存Blenderファイルはコピーしてから処理
- 実行スクリプトは dry-run から開始
- 自動削除、自動上書き、自動volume削除は禁止
