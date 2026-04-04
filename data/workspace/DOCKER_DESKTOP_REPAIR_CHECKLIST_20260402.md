# Docker Desktop Repair Checklist

## Current state

- Docker Desktop version: `4.62.0`
- Install path: `C:\Program Files\Docker\Docker`
- Uninstall command: `"C:\Program Files\Docker\Docker\Docker Desktop Installer.exe" "uninstall"`
- Current WSL data path: `E:\DockerData\DockerDesktopWSL`
- Legacy path kept as junction: `D:\DockerData\DockerDesktopWSL`

## Before repair install

1. Run `powershell -ExecutionPolicy Bypass -File scripts\prepare_docker_desktop_repair.ps1`
2. Confirm backup files exist under `backups\docker_desktop_repair\...`
3. Confirm `docker_desktop_repair_prepare_status.json` says `dockerInfoOk: true`
4. Confirm `settings-store.json` still contains `CustomWslDistroDir = E:\DockerData\DockerDesktopWSL`
5. Close Docker Desktop dashboard windows

## Safe repair install flow

1. Stop only the frontend first
   `Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force`
2. Start the installer
   `& "C:\Program Files\Docker\Docker\Docker Desktop Installer.exe"`
3. Choose repair/reinstall if the installer offers it
4. Do not remove WSL data when prompted
5. After install, wait for Docker Desktop to finish starting

## Post-repair checks

1. `docker version`
2. `docker info`
3. `docker ps`
4. Open Docker Desktop once and check no `docker.exe` popup appears
5. Confirm `settings-store.json` still points to `E:\DockerData\DockerDesktopWSL`
6. Confirm `D:\DockerData\DockerDesktopWSL` is still a junction to `E:\DockerData\DockerDesktopWSL`

## If the installer resets the WSL path

1. Close Docker Desktop
2. Restore `settings-store.json` from the repair backup
3. Run:
   `wsl --shutdown`
4. Start Docker Desktop again
5. Recheck `docker version` and `docker ps`

## If repair still fails

1. Use the same installer for uninstall
2. Keep `E:\DockerData\DockerDesktopWSL` intact
3. Reinstall Docker Desktop
4. Restore `settings-store.json` so `CustomWslDistroDir` points to `E:\DockerData\DockerDesktopWSL`
5. Start Docker Desktop and recheck
