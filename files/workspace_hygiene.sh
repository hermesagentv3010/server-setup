#!/usr/bin/env bash
# Weekly workspace hygiene (Mondays 05:00, no-agent cron):
#   1) Sweep stray items from the workspace ROOT into tmp/quarantine/<ISO-week>/
#      (move, not delete — reversible grace period)
#   2) Delete anything under tmp/ (incl. quarantine) older than 7 days
# Silent (exit 0, no output) when there is nothing to do — watchdog style.
# NEVER touches projects/ (real work products live there) or .hermes.md.
WS=/srv/hermes-workspace
WEEK_TAG=$(date -u +%G-W%V)

# --- 1) root strays -> quarantine -------------------------------------------
shopt -s nullglob dotglob
stries=()
strays=()
for entry in "$WS"/*; do
  base="${entry##*/}"
  case "$base" in projects|tmp|.hermes.md) continue ;; esac
  strays+=("$entry")
done
if [ ${#strays[@]} -gt 0 ]; then
  DEST="$WS/tmp/quarantine/$WEEK_TAG"
  mkdir -p "$DEST"
  mv "${strays[@]}" "$DEST"/
  echo "workspace-hygiene: quarantined ${#strays[@]} stray item(s) from $WS root into $DEST:"
  printf '  - %s\n' "${strays[@]##*/}"
fi

# --- 2) stale tmp wipe (>7 days) ---------------------------------------------
STALE=$(find "$WS/tmp" -mindepth 1 -mtime +7 2>/dev/null)
if [ -n "$STALE" ]; then
  COUNT=$(printf '%s\n' "$STALE" | wc -l)
  find "$WS/tmp" -mindepth 1 -mtime +7 -delete
  echo "workspace-hygiene: removed $COUNT stale item(s) from $WS/tmp (>7 days):"
  printf '%s\n' "$STALE"
fi

# --- 3) prune dirs emptied by the wipe (always runs) --------------------------
find "$WS/tmp" -depth -mindepth 1 -type d -empty -delete 2>/dev/null
exit 0
