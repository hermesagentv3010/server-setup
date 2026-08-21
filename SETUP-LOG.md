# SETUP-LOG

Compact, ordered runbook for the `hermes` server (Arch Linux, root, pacman-only).
Apply top-to-bottom. This is a recipe for rebuilding the box from scratch —
notably after a hardware change — so keep it free of snapshots, stale
versions, and anything that rots. Secrets are never recorded; non-shareable
items are marked `FIXME: set locally`.

## Install Hermes Agent
- Why: autonomous operator on the box.
- Do:
  ```bash
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
  hermes config set model.default <provider/model>   # FIXME: set locally
  # also set model.provider / model.base_url as needed (see note)
  ```
- Verify: `hermes --version` prints a version; `which hermes` resolves.
- Note: Hermes ships its OWN Python venv — keep it separate from the system
  python, and verify plugins by import, not run_tests.sh.

## Jina web-extract backend (custom plugin)
- Why: key-free URL→markdown extract via r.jina.ai.
- Do: copy `files/jina-web-backend/` → `/usr/local/lib/hermes-agent/plugins/web/jina/`.
  Hermes auto-discovers `plugins/web/*`. Set in `~/.hermes/config.yaml`:
  ```yaml
  web:
    backend: jina
    extract_backend: jina
  ```
  Optional, local only in `~/.hermes/.env`: `JINA_API_KEY`, `JINA_TIMEOUT=30`, `JINA_BASE_URL`.
- Verify: `hermes chat -q "extract https://example.com"` logs `Plugin 'web-jina' registered`.
- Note: extract-only (`supports_search()=False`); search still routes to ddgs.
  Relaunch Hermes after copying files.

## Starship + JetBrains Mono Nerd Font
- Why: readable git-aware prompt with nerd glyphs.
- Do:
  ```bash
  pacman -S --noconfirm starship ttf-jetbrains-mono-nerd
  cp files/starship.toml ~/.config/starship.toml
  ```
  Add to `~/.bashrc` (see `files/bashrc.snippet`): `eval "$(starship init bash)"`.
- Verify: a new bash shell shows the starship prompt; `fc-list` lists the Nerd font.
- Note: must be the Nerd font build or glyphs render as boxes.

## gh CLI + login
- Why: headless GitHub access (this repo pushes via gh).
- Do:
  ```bash
  pacman -S --noconfirm github-cli
  gh auth login            # headless: gh auth login --with-token < token.txt
  git config --global credential.https://github.com.helper '!/usr/bin/gh auth git-credential'
  git config --global credential.https://gist.github.com.helper  '!/usr/bin/gh auth git-credential'
  git config --global user.name  "hermesagentv3010"
  git config --global user.email "hermesagentv3010@users.noreply.github.com"
  ```
- Verify: `gh auth status` → logged in as hermesagentv3010; `git push origin main` works token-less.
- Note: token lives only in `~/.config/gh/hosts.yml` — never commit it. Use the
  hermesagentv3010 account.

## Daily Arch update cron (AUR-free)
- Why: keep system patched; never touch AUR.
- Do: copy `files/arch_update.sh` → `~/.hermes/scripts/arch_update.sh` (`chmod +x`).
  Register Hermes cron `arch-daily-update` (see `cronjobs.md`). Script: refresh
  `archlinux-keyring`, `pacman -Syu --noconfirm`, silent on success / alerts on
  failure, `flock` lock, AUR (`pacman -Qm`) never updated.
- Verify: `ARCH_UPDATE_DRYRUN=1 ~/.hermes/scripts/arch_update.sh`; `tail -n5 /root/.hermes/logs/arch_update.log`.
- Note: AUR packages drift by policy. Script must be executable at that path.

## This repo + daily-log cron
- Why: reproducible runbook that stays current automatically.
- Do: clone `hermesagentv3010/server-setup` (branch main). Add Hermes cron
  `server-setup-daily-log` (see `cronjobs.md`): reads recent sessions, appends
  shareable changes to this file, commits + pushes via gh. Skips all secrets.
- Verify: job appears in `cronjob list`; `gh repo view hermesagentv3010/server-setup --json url -q .url` returns the repo link.
- Note: log agent records only shareable changes; secrets handled out-of-band.
  If `gh auth` expires, both crons break — re-run `gh auth login`. Cron delivery
  target is set in the Hermes scheduler, never in this repo.

## sops + age (post-quantum secret tooling)
- Why: user wants agent-managed encrypted secrets without the agent ever seeing plaintext.
- Do: `pacman -S --noconfirm sops age` (both from `extra`; no AUR).
- Verify: `sops --version` and `age --version` run.
- Note: **age ≥1.3.0 required** for the `-pq` (ML-KEM-768 + X25519) post-quantum
  key mode. The `sops-age-pq-management` skill documents the workflow.

## PQ age keypair (secret — user custody)
- Why: encrypts/decrypts the sops stores; the private key must stay with the user and never enter the repo.
- Do: `age-keygen -pq -o /root/.config/sops/age/keys.txt`; public recipient saved to `/root/.config/sops/age/recipient.txt`.
- Verify: private key line begins `AGE-SECRET-KEY-PQ-1…`, recipient begins `age1pq1…`.
- Note: secret — private key value is `FIXME: set locally`; back it up off-box.
  Recipient is non-secret but host-specific.

## /dev/sda btrfs data disk mounted at /srv
- Why: dedicated 477G SSD for container images + named volumes (offloads OCI
  storage from the root nvme); first step of the homelab storage plan.
- Do:
  ```bash
  parted -s /dev/sda mklabel gpt
  parted -s /dev/sda mkpart primary 0% 100%
  mkfs.btrfs -L srv /dev/sda1      # UUID is device-specific — note it for fstab
  ```
  Add to /etc/fstab (substitute the real UUID from `blkid /dev/sda1`):
  ```
  UUID=<sda1-uuid>  /srv  btrfs  rw,noatime,compress=zstd,ssd,discard=async,space_cache=v2  0 0
  ```
  Also flip the root btrfs subvolumes (`/`, `/home`, `/var/cache/pacman/pkg`,
  `/var/log`) from `relatime` to `noatime` — they already had
  `compress=zstd:3,ssd,discard=async,space_cache=v2`.
- Verify: `findmnt /srv` shows `rw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2`;
  `findmnt --verify` reports no errors/warnings; `/srv` is writable and survives reboot.
- Note: this is where the Podman `graphroot` (container storage) will later point —
  not wired up yet. `mkfs` is hard-blocked in the agent shell, so the format was run
  via a wrapper script; a human rebuild runs `mkfs.btrfs` directly.

<!-- New entries go ABOVE this line, newest first, same format. -->
