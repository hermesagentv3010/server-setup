# SETUP-LOG

Compact, ordered runbook for the `hermes` server (Arch Linux, root, pacman-only).
Apply **top-to-bottom**. Dates are intentionally omitted — this is a recipe,
not a diary, so the file stays small. Secrets are never recorded;
non-shareable items are marked `FIXME: set locally`.

## Install Hermes Agent
- **Why:** autonomous operator on the box.
- **Do:**
  ```bash
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
  hermes config set model.default tencent/hy3:free
  hermes config set model.provider kilocode
  hermes config set model.base_url https://api.kilo.ai/api/gateway
  ```
- **Verify:** `hermes --version` → v0.20.4; `which hermes` → `/usr/local/lib/hermes-agent/venv/bin/hermes`.
- **Note:** installer venv has no pip/pytest — verify plugins by import, not `run_tests.sh`. Host `python` is 3.14; keep it separate from Hermes' 3.11 venv.

## Jina web-extract backend (custom plugin)
- **Why:** key-free URL→markdown extract via `r.jina.ai`.
- **Do:** copy [`files/jina-web-backend/`](files/jina-web-backend/) → `/usr/local/lib/hermes-agent/plugins/web/jina/`. Hermes auto-discovers `plugins/web/*`. Set in `~/.hermes/config.yaml`:
  ```yaml
  web:
    backend: jina
    extract_backend: jina
  ```
  Optional, local only in `~/.hermes/.env`: `JINA_API_KEY`, `JINA_TIMEOUT=30`, `JINA_BASE_URL`.
- **Verify:** `hermes chat -q "extract https://example.com"` logs `Plugin 'web-jina' registered web provider: jina`.
- **Note:** extract-only (`supports_search()=False`); search still routes to `ddgs`. No key = free-tier limit. Relaunch Hermes after copying files.

## Starship + JetBrains Mono Nerd Font
- **Why:** readable git-aware prompt with nerd glyphs.
- **Do:**
  ```bash
  pacman -S --noconfirm starship ttf-jetbrains-mono-nerd
  cp files/starship.toml ~/.config/starship.toml
  ```
  Add to `~/.bashrc` (see [`files/bashrc.snippet`](files/bashrc.snippet)): `eval "$(starship init bash)"`.
- **Verify:** `starship --version` → 1.26.0; `fc-list | grep -i "jetbrains mono nerd"` lists the font; new bash shell shows the prompt.
- **Note:** must be the **Nerd** font build or glyphs render as boxes.

## gh CLI + login as hermesagentv3010
- **Why:** headless GitHub access (this repo pushes via gh).
- **Do:**
  ```bash
  pacman -S --noconfirm github-cli
  gh auth login            # headless: gh auth login --with-token < token.txt
  git config --global credential.https://github.com.helper '!/usr/bin/gh auth git-credential'
  git config --global credential.https://gist.github.com.helper '!/usr/bin/gh auth git-credential'
  git config --global user.name  "hermesagentv3010"
  git config --global user.email "hermesagentv3010@users.noreply.github.com"
  ```
- **Verify:** `gh auth status` → logged in as hermesagentv3010; `git push origin main` works with no token prompt.
- **Note:** token lives only in `~/.config/gh/hosts.yml` — never commit it. If push prompts for a password, the credential helper line is missing.

## Daily Arch update cron (AUR-free)
- **Why:** keep system patched; never touch AUR.
- **Do:** copy [`files/arch_update.sh`](files/arch_update.sh) → `~/.hermes/scripts/arch_update.sh`, `chmod +x`. Register Hermes cron `arch-daily-update` (see [`cronjobs.md`](cronjobs.md)). Script: refresh `archlinux-keyring`, `pacman -Syu --noconfirm`, silent on success / alerts on failure, `flock` lock, AUR (`pacman -Qm`) never updated.
- **Verify:** `ARCH_UPDATE_DRYRUN=1 ~/.hermes/scripts/arch_update.sh`; `tail -n5 /root/.hermes/logs/arch_update.log`.
- **Note:** AUR packages drift by policy. Script must be executable at that path.

## This repo + daily-log cron
- **Why:** reproducible runbook that stays current automatically.
- **Do:** repo `hermesagentv3010/server-setup` (public, branch `main`). Add Hermes cron `server-setup-daily-log` (see [`cronjobs.md`](cronjobs.md)): reads recent sessions, appends shareable changes to this file, commits + pushes via gh. Skips all secrets.
- **Verify:** job appears in `cronjob list` and posts a daily summary; `gh repo view hermesagentv3010/server-setup --json url -q .url` → the repo link.
- **Note:** log agent records only shareable changes; secrets handled out-of-band. If `gh auth` expires, both crons break — re-run `gh auth login`. Cron delivery target is configured in the Hermes scheduler, never in this repo.

## sops + age installed (pacman, post-quantum secret tooling)
- **Why:** user wants agent-managed encrypted secrets without the agent ever seeing plaintext.
- **Do:** `pacman -S --noconfirm sops age` (sops 3.13.3-1, age 1.3.1-1, both from `extra`; no AUR).
- **Verify:** `sops --version` and `age --version`.
- **Note:** age ≥1.3 is required for the `-pq` (ML-KEM-768 + X25519) post-quantum key mode.

## sops-age-pq-management Hermes skill
- **Why:** codify the no-editor, pipe-generated-secret sops workflow plus the Komodo/Podman consumption pattern.
- **Do:** created `/root/.hermes/skills/sops-age-pq-management/SKILL.md` (non-interactive `sops -e -i` + `sops --set`, `(?i)` `encrypted_regex`, tmpfs decrypt unit).
- **Verify:** skill loads via Hermes skill list / `skill_view sops-age-pq-management`.
- **Note:** key lessons baked in — never hand-type the ~2000-char recipient (read from file), `encrypted_regex` is case-sensitive by default, never print decrypted values.

## PQ age keypair (secret — user custody)
- **Why:** encrypts/decrypts the sops stores; the private key must stay with the user and never enter the repo.
- **Do:** `age-keygen -pq -o /root/.config/sops/age/keys.txt`; public recipient saved to `/root/.config/sops/age/recipient.txt`.
- **Verify:** private key line begins `AGE-SECRET-KEY-PQ-1…`, recipient begins `age1pq1…`.
- **Note:** secret — private key value is FIXME: set locally; back it up off-box. Recipient is non-secret but host-specific.

<!-- daily log: no notable changes -->

<!-- New entries go ABOVE this line, newest first, same format. -->
