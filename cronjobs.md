# cronjobs.md

Pasteable specs for both scheduled jobs. Each has a **Hermes `cronjob`**
definition (how they actually run here) and a plain **raw crontab** fallback.
Cron pushes use branch `main` and the `gh auth git-credential` helper (no token
in the repo). The cron delivery target is set in the Hermes scheduler — it is
**not** written here on purpose.

---

## arch-daily-update — daily Arch upgrade (AUR-free)
Schedule: `17 3 * * *`

**Hermes:**
```
cronjob create
  name:        arch-daily-update
  schedule:    17 3 * * *
  script:      arch_update.sh
  no_agent:    true
  deliver:     <your-telegram-chat-id>     # FIXME: set locally
```
Script: [`files/arch_update.sh`](files/arch_update.sh) → `~/.hermes/scripts/arch_update.sh` (`chmod +x`). Silent on success; alerts on failure.

**Raw fallback:**
```cron
17 3 * * *  /root/.hermes/scripts/arch_update.sh >>/root/.hermes/logs/arch_update.cron.log 2>&1
```

---

## server-setup-daily-log — auto-append server changes to this repo
Schedule: `17 4 * * *`

**Hermes** (self-contained prompt):
```
cronjob create
  name:        server-setup-daily-log
  schedule:    17 4 * * *
  deliver:     <your-telegram-chat-id>     # FIXME: set locally
  prompt: |
    Maintain /root/server-setup (branch: main). Read Hermes session history
    since the last SETUP-LOG.md entry (session_search, newest first). Append
    any SHAREABLE server change as a compact, dated-free entry ABOVE the
    "<!-- New entries go ABOVE this line ... -->" marker, same format as
    existing entries (### Title / Why / Do / Verify / Note):
      - newly installed/removed pacman packages
      - edits to ~/.hermes/config.yaml, ~/.config/starship.toml, ~/.bashrc, /etc configs
      - new or changed Hermes plugins/scripts/cron jobs
      - external services or accounts newly wired up
    NEVER log secrets/keys/tokens/private data/chat IDs — use "FIXME: set locally".
    If nothing notable, append a single short "no notable changes" line.
    Then commit + push:
      cd /root/server-setup && git add -A && \
      git commit -m "daily log: <summary or 'no changes'>" && git push origin main
    End with a one-paragraph summary.
```

**Raw fallback:**
```cron
17 4 * * *  /usr/local/lib/hermes-agent/venv/bin/hermes chat -q "Run server-setup-daily-log: append notable shareable changes to /root/server-setup/SETUP-LOG.md and push." >>/root/.hermes/logs/daily-log.cron.log 2>&1
```

---

## Manage
```bash
cronjob list                       # show jobs
cronjob run  <job_id>             # fire now (test)
cronjob pause <job_id>            # stop
cronjob remove <job_id>           # delete
```
