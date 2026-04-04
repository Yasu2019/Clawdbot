# Docker Headless Migration Notes

Updated: 2026-04-03 JST

## What was confirmed

- `Ubuntu` inside WSL has `systemd` and a running `docker.service`.
- `docker compose` works inside `Ubuntu`.
- Repo-side host harnesses can now call Docker through `wsl -d Ubuntu -- docker ...` using:
  - `data/workspace/docker_runtime.py`
  - `data/workspace/docker_runtime_config.json`
- The following watchdog / maintenance scripts were switched to the shared runtime helper:
  - `data/workspace/paperless_rag_watchdog.py`
  - `data/workspace/audit_paperless_ingest_alignment.py`
  - `data/workspace/continuous_email_ingest_daemon.py`
  - `data/workspace/run_priority_gmail_backfill.py`
  - `data/workspace/repair_learning_engine.py`
  - `data/workspace/run_portal_app_launch_check.py`

## What failed

- Stopping Windows-side `Docker Desktop` / `com.docker.backend` also stopped Docker access inside `Ubuntu`.
- During that test, `docker ps` inside WSL failed with:
  - `Cannot connect to the Docker daemon at unix:///var/run/docker.sock`

## Why it failed

Journal evidence showed that the WSL daemon path is still coupled to Docker Desktop mounts:

- `mnt-wsl-docker-desktop-bind-mounts-Ubuntu-docker.sock.mount`
- `mnt-wsl-docker-desktop-cli-tools.mount`
- `mnt-wsl-docker-desktop-shared-sockets-guest-services.mount`

When Windows-side Docker Desktop was stopped, these mounts were torn down and the Ubuntu-side Docker socket became unavailable.

## Current safe state

- Continue using `Docker Desktop` backend for now.
- Keep `Docker Desktop` UI in quiet/headless suppression mode.
- Prefer repo-side Docker calls through WSL wrapper/runtime helper where already migrated.

## Best next step

Create a truly independent Ubuntu-side Docker engine that does **not** use `/var/run/docker.sock` from Docker Desktop.

Most realistic options:

1. `docker-native.service` on a different socket and data-root
   - example socket: `/var/run/docker-native.sock`
   - example data-root: `/var/lib/docker-native`
2. Separate WSL distro dedicated to headless Docker
3. Rootless Docker with its own user socket

## Current blocker

This machine currently requires elevated privileges inside Ubuntu for the systemd/service route, and rootless helper tools are not installed.

Observed:

- `sudo -n true` requires a password
- `dockerd-rootless-setuptool.sh` not found
- `dockerd-rootless.sh` not found
- `rootlesskit` not found
- `slirp4netns` not found

## Convenience scripts added

- `scripts/wsl_docker.ps1`
- `scripts/wsl_docker_compose.ps1`
- `scripts/activate_wsl_docker_headless.ps1`
- `scripts/enable_docker_desktop_headless_mode.ps1`
- `scripts/disable_docker_desktop_headless_mode.ps1`
