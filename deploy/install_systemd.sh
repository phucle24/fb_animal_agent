#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install_systemd.sh"
  exit 1
fi

install -m 0644 deploy/systemd/*.service /etc/systemd/system/
install -m 0644 deploy/systemd/*.timer /etc/systemd/system/

systemctl daemon-reload
systemctl enable --now fb-animal-agent-web.service
systemctl enable --now fb-animal-agent-ensure.timer
systemctl enable --now fb-animal-agent-poll-batch.timer
systemctl enable --now fb-animal-agent-publish-morning.timer
systemctl enable --now fb-animal-agent-publish-afternoon.timer

systemctl list-timers 'fb-animal-agent-*'

