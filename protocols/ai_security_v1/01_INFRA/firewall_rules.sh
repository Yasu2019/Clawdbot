#!/usr/bin/env bash
set -euo pipefail

# Ubuntu / Debian 系の簡易例
ufw default deny incoming
ufw default deny outgoing

# ローカルホスト通信は許可
ufw allow in on lo
ufw allow out on lo

# 必要最小限のみ許可（例）
# ufw allow out to <approved_ip> port 443 proto tcp

ufw --force enable
ufw status verbose
