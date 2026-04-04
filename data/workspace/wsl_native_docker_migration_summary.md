# WSL Native Docker Migration Prep

- Timestamp: `2026-04-03T06:37:46+09:00`
- Distro: `Ubuntu`
- Current runtime: `docker-desktop`
- Current docker root: `/var/lib/docker`
- Passwordless sudo ready: `True`
- Native socket exists: `True`
- Current desktop socket exists: `True`

## Coupling hints

- `mnt-wsl-docker\x2ddesktop-cli\x2dtools.mount                                                                                                                                 loaded    active     mounted      /mnt/wsl/docker-desktop/cli-tools`
- `  mnt-wsl-docker\x2ddesktop-docker\x2ddesktop\x2duser\x2ddistro.mount                                                                                                          loaded    active     mounted      /mnt/wsl/docker-desktop/docker-desktop-user-distro`
- `  mnt-wsl-docker\x2ddesktop-shared\x2dsockets-guest\x2dservices.mount                                                                                                          loaded    active     mounted      /mnt/wsl/docker-desktop/shared-sockets/guest-services`
- `  mnt-wsl-docker\x2ddesktop-shared\x2dsockets-host\x2dservices.mount                                                                                                           loaded    active     mounted      /mnt/wsl/docker-desktop/shared-sockets/host-services`
- `  mnt-wsl-docker\x2ddesktop\x2dbind\x2dmounts-Ubuntu-docker.sock.mount                                                                                                         loaded    active     mounted      /mnt/wsl/docker-desktop-bind-mounts/Ubuntu/docker.sock`
- `  docker-native.service                                                                                                                                                        loaded    active     running      Independent Docker Engine for headless WSL operation`
- `  docker.service                                                                                                                                                               loaded    active     running      Docker Application Container Engine`
- `  docker.socket                                                                                                                                                                loaded    active     running      Docker Socket for the API`

## Ready artifacts

- Installer script: `wsl_native_docker_install.sh`
- Native daemon config: `docker-native-daemon.json`
- systemd unit: `docker-native.service`
- Runtime switch to native: `switch_docker_runtime_to_wsl_native.ps1`
- Runtime rollback to desktop socket: `switch_docker_runtime_to_wsl_desktop.ps1`

## Recommended next step

- `activate_native_runtime`
