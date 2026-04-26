#!/usr/bin/env bash
set -euo pipefail
mkdir -p evidence
OUT="evidence/wsl_isolation_check_$(date +%Y%m%d_%H%M%S).txt"
{
  echo "# WSL Isolation Check"
  date -Is
  echo
  echo "## /etc/wsl.conf"
  cat /etc/wsl.conf || true
  echo
  echo "## mount check"
  mount | grep -E '/mnt/[a-z]' || echo 'OK: no Windows drive automount detected'
  echo
  echo "## interop check"
  if command -v powershell.exe >/dev/null 2>&1; then
    echo 'NG: powershell.exe is visible from WSL'
  else
    echo 'OK: powershell.exe is not visible from WSL'
  fi
  echo
  echo "## Windows C drive check"
  if [ -d /mnt/c ]; then
    echo 'NG: /mnt/c exists'
    ls -ld /mnt/c || true
  else
    echo 'OK: /mnt/c does not exist'
  fi
  echo
  echo "## current user"
  id
} | tee "$OUT"
echo "saved: $OUT"
