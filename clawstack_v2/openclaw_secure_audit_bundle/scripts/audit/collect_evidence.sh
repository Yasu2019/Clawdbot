#!/usr/bin/env bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
DIR="evidence/audit_$TS"
mkdir -p "$DIR"
cp /etc/wsl.conf "$DIR/wsl.conf" 2>/dev/null || true
uname -a > "$DIR/uname.txt"
id > "$DIR/id.txt"
mount > "$DIR/mount.txt"
(command -v docker >/dev/null && docker version > "$DIR/docker_version.txt" 2>&1) || true
(command -v docker >/dev/null && docker compose ps > "$DIR/docker_compose_ps.txt" 2>&1) || true
(command -v iptables >/dev/null && sudo iptables -S > "$DIR/iptables.txt" 2>&1) || true
find . -maxdepth 3 -type f | sort > "$DIR/bundle_file_list.txt"
tar -czf "evidence/audit_$TS.tar.gz" -C evidence "audit_$TS"
echo "created evidence/audit_$TS.tar.gz"
