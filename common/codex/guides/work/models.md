# Models & Executor Routing

Load when: `/grok` · `/gpt` · `/claude` opt-in delegation, executor/model choice, host fallback, recursion ban.

The session's native model executes by default. Explicit executor requests authorize one bounded external unit; automatic selection remains grade-gated. The current session model stays the orchestrator.

## Opt-in delegation gate

- Automatic or main-selected delegation uses the grade gate: architecture, design, security, verification, and ambiguous-spec work stays native; bulk, repetitive, high-token, mechanical execution delegates.
- An explicit `/grok`, `/gpt`, or `/claude` request overrides only that selection gate for one bounded unit. A self-target executes locally.
- `/grok` → Grok Build CLI; model/effort from `~/.agents/models.toml` role `grok_exec`. Repo execution: `clx-grok-delegate <repo> -p "<prompt>" --always-approve --output-format plain`. One-shot second opinion: `clx-grok-call`.
- `/gpt` → Codex CLI through `clx-ai-delegate codex <repo> -p "<prompt>"`; role `gpt_exec`, Git-only, ephemeral, `workspace-write`.
- `/claude` → Claude Code CLI through `clx-ai-delegate claude <repo> -p "<prompt>"`; role `claude_exec`, nonpersistent, sandboxed on macOS/Linux, edit-only on Windows.
- **A model the user names wins for that call.** "gpt-5.6-sol로 돌려" pins sol for this invocation only —
  say so in the report and do NOT edit the registry. With no model named, the role's pin is used verbatim;
  never substitute a higher-ranked model on your own (`gpt_exec` is deliberately the fast/affordable tier).
- Reasoning effort: taken from the registry role, or from the tier the user named alongside the model.
  Registry policy: the highest tier the backend serves, excluding self-delegating tiers (Codex `ultra`).
- One bounded unit per invocation. On failure/timeout, inspect partial state before deciding; never blind-retry or chain calls.
- An external executor never invokes another executor. `CLX_EXTERNAL_EXECUTOR` makes the wrappers fail closed on nested entry.
- Never bypass the wrappers with unwrapped write-capable external CLIs.
- Only main invokes `/grok`/`/gpt`/`/claude`; subagents never spawn external CLIs.
- Host fallback: if the target CLI/backend is unavailable or times out, execute natively and say so — never substitute a raw CLI or another transport.
- Mixed requests: classify by primary labor type; verification always returns to main.
- A bare executor preference does not bypass the automatic gate; an explicit assignment does. Keep transient role bindings in the current session context.

Detection, not memory: `python3 ~/.claude/hooks/model-registry-check.py` asks the installed backends what
they serve; the setup-ui page shows the same data and can switch a role in one click.

`~/.agents/models.toml` is the model-id source of truth; `grok models` must list the `grok_exec` model as Grok's default (`~/.grok/config.toml` follows the registry). Vision/computer-use stays on a supporting host.
