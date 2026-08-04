# personal-examples

Sanitized copies of the owner's git backup-and-push flow. **Nothing here is run by
`install.sh` or by any shipped hook.** The clean distribution ships with no git remote
and never auto-pushes — these are references you personalize if you want your own
private backup mirror.

| File | Purpose |
|------|---------|
| `backup-to-git.sh` | Refresh the local safe mirror, secret-scan it (fail closed), then commit + push to **your** private repo. |
| `auto-backup.sh` | Optional Stop hook that runs `backup-to-git.sh` when config changed. |

## To use

1. Open `backup-to-git.sh`, set `OWNER` to your GitHub account and `EXPECTED_REMOTE`
   to a **private** repo you created.
2. Read the secret-scan block. It fails closed on any match — keep it.
3. Copy the file(s) into `~/.claude/hooks/`, `chmod +x`, and (for auto-backup) register
   the Stop hook shown in the header comment.

Never point these at a public repo, and never remove the secret scan.
