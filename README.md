# server-setup

Reproducible setup & runbook for the **`hermes`** server — an Arch Linux box
(root, passwordless sudo, `pacman` only) that runs **Hermes Agent** as the
primary operator. This repo documents everything *that can be shared* so a
fresh agent can roughly reproduce the environment.

> **Zero-secrets rule:** nothing here contains API keys, tokens, chat/user
> IDs, private data, or anything non-shareable. Any non-shareable item is
> named with a `FIXME: set locally` note instead of its value. Commits never
> embed a user ID in the author email — the username-only noreply address is
> used (see *Commits* below).

## How to use this as an agent

1. Read [`SETUP-LOG.md`](SETUP-LOG.md) top-to-bottom. Entries are ordered and
   meant to be applied **in order** — each one is a discrete, reproducible step.
   Dates are omitted on purpose to keep the file compact over time.
2. For each entry, copy the referenced file from [`files/`](files/) into the
   exact path described, or run the exact commands quoted.
3. Recreate the cron jobs from [`cronjobs.md`](cronjobs.md).

## What is on this server (verified)

| Component | State | Notes |
|---|---|---|
| OS | Arch Linux (x86_64, kernel 7.1.8-arch1-3) | root user, `pacman` only — **no AUR** |
| Hermes Agent | v0.20.4 (2026.8.18) | installed at `/usr/local/lib/hermes-agent`, venv py3.11 |
| Web extract backend | **jina** (custom plugin `web-jina`) | free tier via `r.jina.ai`, no key required |
| Web search backend | `ddgs` (default) | DuckDuckGo, no key |
| Starship | 1.26.0-1 | prompt in `~/.bashrc` |
| Font | `ttf-jetbrains-mono-nerd` 3.5.0-1 | "JetBrains Mono Nerd Font" |
| `gh` CLI | github-cli 2.97.0-1 | authed as `hermesagentv3010` |
| Update cron | `arch-daily-update` | `arch_update.sh` @ 03:17 daily |
| Git auth | `gh auth git-credential` helper | configured for github.com + gist |

## Repo layout

```
server-setup/
├── README.md                 # this file
├── SETUP-LOG.md              # ordered runbook (dates omitted, compact)
├── cronjobs.md               # pasteable cron definitions (Hermes + raw crontab)
└── files/
    ├── jina-web-backend/     # the custom Hermes web plugin (3 files)
    │   ├── plugin.yaml
    │   ├── __init__.py
    │   └── provider.py
    ├── starship.toml         # starship config (copy to ~/.config/)
    ├── arch_update.sh        # daily Arch update script (AUR-free)
    └── bashrc.snippet        # starship + local-bin lines for ~/.bashrc
```

## Accounts / prerequisites (NOT in this repo)

- A GitHub account authed via `gh`. This server uses the `hermesagentv3010`
  account — recreate with `gh auth login` (use `gh auth login --with-token
  < token.txt` on a headless box). The token lives only in
  `~/.config/gh/hosts.yml`; **never** commit it.
- `JINA_API_KEY` is **optional** — only lifts the free-tier rate limit. If
  wanted, set it locally in `~/.hermes/.env`; it is **not** shared here.
- Cron delivery targets a Telegram chat configured in the Hermes scheduler —
  that destination ID is **never** written to this repo.

## Commits

To keep the user ID out of git metadata, use the username-only noreply address:
```bash
git config --global user.name  "hermesagentv3010"
git config --global user.email "hermesagentv3010@users.noreply.github.com"
```
Pushes use the `gh auth git-credential` helper, so no token is stored in the
repo or in git config.
