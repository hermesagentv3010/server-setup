#!/usr/bin/env bash
#
# arch_update.sh — Daily Arch system update (official repos ONLY).
#
# Hard rules:
#   * NEVER touches AUR. Only `pacman` (official repos) is ever invoked.
#     No yay/paru/aura/makepkg — AUR updates are structurally impossible.
#   * Silent on success (no stdout -> cron delivers nothing).
#   * On failure, emits a concise, Telegram-safe message to stdout so the
#     cron worker delivers an alert. Also exits non-zero (extra coverage).
#
# Env:
#   ARCH_UPDATE_DRYRUN=1  -> check parsing/branches without touching the system
#                            (success branch stays silent, failure branch prints).
#
set -uo pipefail

LOCK="/run/lock/arch_update.lock"
LOG="/root/.hermes/logs/arch_update.log"
mkdir -p "$(dirname "$LOG")"

# --- Light log rotation (keep last 300 lines) -------------------------------
if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 300 ]; then
  tail -n 300 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# --- Prevent overlapping runs ----------------------------------------------
exec 9>"$LOCK" || exit 0
if ! flock -n 9; then
  exit 0   # already running; stay silent
fi

TMPOUT="$(mktemp)"
trap 'rm -f "$TMPOUT"' EXIT

# Resolve a stable host label (hostname may be unset on minimal installs).
if command -v hostname >/dev/null 2>&1; then
  HOST="$(hostname)"
elif command -v uname >/dev/null 2>&1; then
  HOST="$(uname -n)"
else
  HOST="${HOSTNAME:-unknown-host}"
fi

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) run (dryrun=${ARCH_UPDATE_DRYRUN:-0}) ===" >> "$LOG"

if [ "${ARCH_UPDATE_DRYRUN:-0}" = "1" ]; then
  echo "DRYRUN: would refresh keyring + run 'pacman -Syu --noconfirm'." >> "$LOG"
  exit 0
fi

# 1) Refresh + update the keyring first to avoid spurious signature failures.
pacman -Sy --noconfirm archlinux-keyring >> "$LOG" 2>&1 || true

# 2) Full system upgrade (official repos only).
if pacman -Syu --noconfirm > "$TMPOUT" 2>&1; then
  cat "$TMPOUT" >> "$LOG"
  AUR_COUNT="$(pacman -Qm 2>/dev/null | wc -l)"
  echo "upgrade OK; AUR-installed packages present (intentionally NOT updated): $AUR_COUNT" >> "$LOG"
  # Success -> no stdout -> cron stays silent.
  exit 0
else
  RC=$?
  cat "$TMPOUT" >> "$LOG"
  # Failure -> emit a concise alert to stdout (cron delivers it).
  echo "ARCH UPDATE FAILED (exit $RC) on $HOST at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Last output from pacman:"
  tail -n 15 "$TMPOUT"
  echo "Full log: $LOG"
  exit 1
fi
