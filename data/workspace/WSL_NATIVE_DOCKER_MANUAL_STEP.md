# WSL Native Docker Manual Step

独立 daemon の本番切替は、いまの時点では Ubuntu 側の `sudo` が必要です。  
ただし、それ以外の準備物はすでに生成済みです。

## 目的

- Docker Desktop の UI / backend に引きずられない Docker socket を作る
- 既存の Desktop socket `/var/run/docker.sock` とは別に
  `/var/run/docker-native.sock` を立てる
- data-root も `/var/lib/docker-native` に分離する

## 準備済みファイル

- [wsl_native_docker_install.sh](d:/Clawdbot_Docker_20260125/data/workspace/wsl_native_docker_install.sh)
- [docker-native-daemon.json](d:/Clawdbot_Docker_20260125/data/workspace/docker-native-daemon.json)
- [docker-native.env](d:/Clawdbot_Docker_20260125/data/workspace/docker-native.env)
- [docker-native.service](d:/Clawdbot_Docker_20260125/data/workspace/docker-native.service)
- [switch_docker_runtime_to_wsl_native.ps1](d:/Clawdbot_Docker_20260125/data/workspace/switch_docker_runtime_to_wsl_native.ps1)
- [switch_docker_runtime_to_wsl_desktop.ps1](d:/Clawdbot_Docker_20260125/data/workspace/switch_docker_runtime_to_wsl_desktop.ps1)
- [validate_wsl_native_docker_runtime.py](d:/Clawdbot_Docker_20260125/data/workspace/validate_wsl_native_docker_runtime.py)

## Ubuntu で 1 回だけ実行するコマンド

```bash
bash /mnt/d/Clawdbot_Docker_20260125/data/workspace/wsl_native_docker_install.sh
```

この途中で `sudo` のパスワード入力が求められます。

## 完了確認

Ubuntu 側:

```bash
DOCKER_HOST=unix:///var/run/docker-native.sock docker version
DOCKER_HOST=unix:///var/run/docker-native.sock docker ps
systemctl --no-pager --full status docker-native.service
```

Windows 側:

```powershell
powershell -ExecutionPolicy Bypass -File data\workspace\switch_docker_runtime_to_wsl_native.ps1
python data\workspace\validate_wsl_native_docker_runtime.py
```

## Rollback

```powershell
powershell -ExecutionPolicy Bypass -File data\workspace\switch_docker_runtime_to_wsl_desktop.ps1
```

必要なら Ubuntu 側で:

```bash
sudo systemctl stop docker-native.service
sudo systemctl disable docker-native.service
sudo rm -f /etc/systemd/system/docker-native.service /etc/docker/daemon-native.json /etc/default/docker-native
sudo systemctl daemon-reload
```
