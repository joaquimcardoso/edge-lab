#!/usr/bin/env bash
# Installs the edgelab-8k-poll systemd service + timer on the Pi.
# Idempotent: safe to re-run. Does NOT create or edit /etc/edgelab.env
# (secrets policy: docs/08-credentials.md -- created directly on the
# device by whoever has hands on it, never by an automated script).
#
# Story: stories/STORY-008-pi-collector-entrypoint.md
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/mnt/data/edgelab"
UNIT_DEST="/etc/systemd/system"
ENV_FILE="/etc/edgelab.env"

echo "==> Checking external data disk is mounted at /mnt/data"
if ! mountpoint -q /mnt/data; then
  echo "ERROR: /mnt/data is not mounted. Fix /etc/fstab first (see docs/04-infrastructure.md)." >&2
  exit 1
fi

echo "==> Creating data directories (idempotent)"
mkdir -p "${DATA_DIR}/raw" "${DATA_DIR}/reports"

echo "==> Checking for ${ENV_FILE}"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "WARNING: ${ENV_FILE} does not exist yet." >&2
  echo "         Create it on this device (see .env.example, docs/08-credentials.md)" >&2
  echo "         before this timer is enabled -- refusing to enable it against a" >&2
  echo "         config that is guaranteed to fail on its first tick." >&2
  ENV_READY=0
else
  ENV_READY=1
fi

echo "==> Installing systemd units to ${UNIT_DEST}"
UNITS=(
  edgelab-8k-poll.service edgelab-8k-poll.timer
  edgelab-daily-report.service edgelab-daily-report.timer
)
for unit in "${UNITS[@]}"; do
  sudo cp "${DEPLOY_DIR}/${unit}" "${UNIT_DEST}/${unit}"
done
sudo systemctl daemon-reload

if [[ "${ENV_READY}" -eq 1 ]]; then
  echo "==> Enabling and starting timers"
  sudo systemctl enable --now edgelab-8k-poll.timer
  sudo systemctl enable --now edgelab-daily-report.timer
  echo "==> Done. Check status with: systemctl status edgelab-8k-poll.timer edgelab-daily-report.timer"
else
  echo "==> Units installed but NOT enabled. Create ${ENV_FILE}, then run:" >&2
  echo "        sudo systemctl enable --now edgelab-8k-poll.timer edgelab-daily-report.timer" >&2
fi
