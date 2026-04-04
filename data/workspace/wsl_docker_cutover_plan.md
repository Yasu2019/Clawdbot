# WSL Docker Cutover Plan

- Timestamp: `2026-04-03T07:12:23+09:00`
- Native daemon ready: `True`
- Cutover ready: `False`

## Phases

- `phase_1_native_daemon_ready`: completed - Independent WSL native docker daemon is running on /var/run/docker-native.sock
- `phase_2_inventory_baseline`: completed - Current Docker Desktop projects and services are inventoried
- `phase_3_migrate_compose_projects`: in_progress - Recreate compose projects on native daemon without touching desktop runtime yet
- `phase_4_validation`: pending - Portal, Paperless, Gmail, n8n, and quality apps pass smoke checks on native daemon
- `phase_5_runtime_switch`: pending - Switch repo-side runtime helper to wsl_native after services are verified

## Project migration progress

- `clawstack-unified`: pending (desktop running `50`, native running `0`)
- `iatf_system_dev`: completed (desktop running `0`, native running `4`)
- `iatf_system`: completed (desktop running `0`, native running `4`)

## Current blocker

- Native daemon is up, but `clawstack-unified` is not yet recreated on the native socket.
- Do not run the runtime switch yet; it would move host-side maintenance scripts to an empty daemon.
