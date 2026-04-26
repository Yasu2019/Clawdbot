#!/usr/bin/env bash
set -euo pipefail
if id claw >/dev/null 2>&1; then
  echo "user claw already exists"
else
  sudo adduser --disabled-password --gecos "AI Agent User" claw
fi
sudo mkdir -p /home/claw/workspace /home/claw/evidence
sudo chown -R claw:claw /home/claw
id claw
