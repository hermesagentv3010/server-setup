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
Script: [`files/arch_update.sh`](files/arch_update.sh) → `~/.hermes/scripts/arch_update.sh` (`chmod +x`). Silent on success; alerts on failure. Also runs a best-effort `brew update`/`upgrade` as the dedicated non-root `linuxbrew` user (skipped cleanly if Homebrew is absent).

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
    Maintain /srv/hermes-workspace/projects/server-setup (branch: main). Read Hermes session history
 since the last SETUP-LOG.md entry (session_search, newest first). Append
 any SHAREABLE server change as a compact entry ABOVE the
 "<!-- New entries go ABOVE this line ... -->" marker, same format as
 existing entries (## Title / Why / Do / Verify / Note):
   - newly installed/removed pacman packages (install current extra packages; say
     e.g. "pacman -S sops age", NOT "sops 3.13.3-1")
   - edits to ~/.hermes/config.yaml, ~/.config/starship.toml, ~/.bashrc, /etc configs
   - new or changed Hermes plugins/skills/scripts/cron jobs
   - external services or accounts newly wired up
 RULES:
   - NEVER pin exact package versions (they rot) — record the install command, not a number.
   - NEVER log secrets/keys/tokens/private data/chat IDs — use "FIXME: set locally".
   - NEVER add diary/status prose — this is a rebuild recipe, not a log of the day.
   - Mark MINIMUM version requirements only where a feature needs it (e.g. "age >=1.3.0 for -pq").
 If nothing notable, append a single short "no notable changes" line.
    Then commit + push:
      cd /srv/hermes-workspace/projects/server-setup && git add -A && \
      git commit -m "daily log: <summary or 'no changes'>" && git push origin main
    End with a one-paragraph summary.
```

**Raw fallback:**
```cron
17 4 * * *  /usr/local/lib/hermes-agent/venv/bin/hermes chat -q "Run server-setup-daily-log: append notable shareable changes to /srv/hermes-workspace/projects/server-setup/SETUP-LOG.md and push." >>/root/.hermes/logs/daily-log.cron.log 2>&1
```

---

## workspace-hygiene — weekly workspace sweep (Mondays)
Schedule: `0 5 * * 1`

**Hermes:**
```
cronjob create
  name:        workspace-hygiene
  schedule:    0 5 * * 1
  script:      workspace_hygiene.sh
  no_agent:    true
  deliver:     <your-telegram-chat-id>     # FIXME: set locally
```
Script: [`files/workspace_hygiene.sh`](files/workspace_hygiene.sh) → `~/.hermes/scripts/workspace_hygiene.sh` (`chmod +x`). Moves stray items from the workspace root into `tmp/quarantine/<ISO-week>/`, deletes anything under `tmp/` older than 7 days; silent when there is nothing to do. Never touches `projects/` or `.hermes.md`. Pair with the `pre_tool_call` hook from SETUP-LOG ("Workspace hygiene") which blocks writes at the workspace root in the first place.

**Raw fallback:**
```cron
0 5 * * 1  /root/.hermes/scripts/workspace_hygiene.sh >>/root/.hermes/logs/workspace_hygiene.cron.log 2>&1
```

---

## Manage
```bash
cronjob list                       # show jobs
cronjob run  <job_id>             # fire now (test)
cronjob pause <job_id>            # stop
cronjob remove <job_id>           # delete
```
