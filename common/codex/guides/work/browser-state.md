# Browser State Isolation

Load when: any browser automation or Chrome/profile/cookie/session operation.

Standing user policy (2026-07-14): ordinary apps may be launched and used read-only without extra conversational approval. Real browser profiles remain separate because browser launch/navigation can persist history, cookies, locks, and session data.

## Agent boundary
- Never attach automation to, navigate, inspect, screenshot, quit, or kill the user's regular Chrome or another real browser profile.
- Never read or change profiles, cookies, history, sessions, extensions, cache, preferences, local state, sync, Keychain, tokens, or account state.
- Never attach CDP, Playwright, extensions, or other automation to a real browser data root.
- If work needs the user's real browser/account state, give the exact manual step; the user may provide a screenshot or exported artifact.

## Isolated automation
- Use a new unsigned isolated profile for read-only browser work without extra conversational approval; platform-mandated tool approval may still appear.
- Never import cookies, credentials, profiles, or account state into the isolated profile.
- Cleanup must close and remove only the agent-created isolated profile/resources after verifying their resolved paths are outside every real browser data root.

## Mandatory audit transaction

Every browser action, including in-app browser, Playwright, or an isolated Chrome/Chromium process, must have one active session-scoped transaction before the first browser tool call. The hook denies unplanned browser calls and always denies real-Chrome endpoints even when a transaction exists.

Runtime root: `~/.claude/browser-audit/` (local-only; never backed up).

```
YYYY-MM-DD/<session-id>/<action-id>/
├── plan.json       # purpose, method, sanitized target, expected changes, owned resources
├── events.jsonl    # append-only tool start/result hashes and sanitized targets
├── result.json     # actual changes, rollback state, verification
└── ROLLBACK.md     # human-readable ordered reversal steps
```

Before use, run `browser-audit.py begin` with the stable session id, exact purpose/method/target, expected persistent changes, every agent-owned resource, ordered rollback steps, and verification. If the hook supplies a session id in a denial, use that exact id; never key by cwd or share an active transaction across sessions. Add material observations with `note`; finish with actual change, rollback status, and verification. An open transaction cannot be overwritten.

The ledger records no cookies, credentials, query strings, URL fragments, request/response bodies, page text, or account state. Tool inputs/results are represented by hashes plus sanitized target metadata. Audit is evidence, not permission: it never authorizes real-profile access or an otherwise unauthorized external write.

Pruning runs at session start and transaction start. Only non-symlink date directories strictly older than 10 days under the audit root are removed; current/10-day records, paths outside the root, and unknown entries remain untouched.

## Static wrapper verification

Never execute `chrome-cdp` to test whether it is safe. Validate its regular-file type, executable/non-writable mode, pinned SHA-256, fail-closed `exit 125`, and forbidden capability strings by static reads only. Test risky upstream behavior only with temporary fake scripts that cannot touch Chrome.
