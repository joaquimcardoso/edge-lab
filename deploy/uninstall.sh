#!/usr/bin/env bash
# Stops, disables and removes the edgelab-8k-poll service + timer.
# Never touches /mnt/data -- data deletion is never a side effect
# of an uninstall script.
#
# Story: stories/STORY-008-pi-collector-entrypoint.md
set -euo pipefail

UNIT_DEST="/etc/systemd/system"

echo "==> Stopping and disabling edgelab-8k-poll.timer (if present)"
sudo systemctl disable --now edgelab-8k-poll.timer 2>/dev/null || true

echo "==> Removing unit files"
sudo rm -f "${UNIT_DEST}/edgelab-8k-poll.service" "${UNIT_DEST}/edgelab-8k-poll.timer"
sudo systemctl daemon-reload

echo "==> Done. /mnt/data was not touched."
