# macOS harness

macOS-only pieces that are intentionally kept OUT of `common/` because they depend
on macOS facilities (jetsam/APFS, launchd) or on the owner's own git remote. The
cross-platform installer (`install.sh`) does **not** touch any of these by default.

## Files

| File | What it is | Wired up by |
|------|------------|-------------|
| `disk-guard.sh` | SessionStart guard that warns when free disk `< 30G` (heavy data work risks a macOS **jetsam** kill). Uses `df` (portable) but the remediation hint mentions APFS snapshots (`tmutil`), so it lives here. | Not registered by default. To use it, copy into `~/.claude/hooks/` and add a SessionStart hook in `settings.json`. |
| `com.OWNER.agents-backup.plist` | launchd job (daily 09:30) that refreshes the **local** safe mirror. `OWNER` and `__CLX_HOME__` are placeholders. Renamed from the owner's `com.<user>.agents-backup.plist`. As shipped it runs `backup-config.sh` (local mirror only — **no push**). | Only `install.sh --with-launchd` (opt-in). |
| `personal-examples/` | The owner's git backup/push flow, sanitized. **Never run by the installer.** See its own README. | Manual, after you personalize `OWNER`. |

## Re-enabling `disk-guard.sh` (optional)

```bash
cp macos-harness/disk-guard.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/disk-guard.sh
```

Then add to the `hooks.SessionStart` array in `~/.claude/settings.json`:

```json
{ "type": "command", "command": "__CLX_HOME__/.claude/hooks/disk-guard.sh", "timeout": 10 }
```

(Replace `__CLX_HOME__` with your real `$HOME`.)

## Installing the launchd job

`install.sh --apply --with-launchd` substitutes `OWNER` (your macOS short username)
and `__CLX_HOME__`, writes the plist to `~/Library/LaunchAgents/`, and prints the
`launchctl load` command. It does **not** auto-load the job — you run `launchctl` yourself.

## Intentionally excluded (mac + owner-specific)

These lived in the owner's `~/.claude` / `~/.codex` but are neither portable nor safe
to share, so they are **not** in this repo at all:

- `config-doctor.py` / `hooks-selftest.sh` — validators hardwired to the owner's exact
  repo/plugin/Hermes layout; they would emit noise on any other machine.
- Codex Hermes/xAI proxy `launchagents/`, `local-bin/` bridges, and `grok-*.config.toml`
  catalogs — personal localhost-proxy infrastructure tied to the owner's accounts.
- `sync-grok-model-config.py` ships with the owner's Codex desktop-proxy wiring stripped
  (it no longer injects a `chatgpt_base_url` into your `config.toml`). If you actually run
  the grok-hermes proxies, re-add one line to `~/.codex/config.toml`:
  `chatgpt_base_url = "http://127.0.0.1:8647"`.
