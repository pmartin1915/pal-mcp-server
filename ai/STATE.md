# pal-mcp-server — STATE

Written 2026-10-27 from README.md, CLAUDE.md, AGENTS.md, CHANGELOG.md, conf/custom_models.json, clink/ and git log. Describes only; it decides nothing.

## What it is
Perry's fork of an upstream project (remote `origin` = pmartin1915/pal-mcp-server; remote `upstream` = BeehiveInnovations/pal-mcp-server). PAL MCP ("Provider Abstraction Layer", formerly Zen MCP) is an MCP server that lets a CLI such as Claude Code call other models and CLIs from one session. Its `clink` tool bridges external AI CLIs as subagents. Upstream version in `config.py` and CHANGELOG.md: 9.8.2 (2025-12-15). Layout (AGENTS.md): `server.py`, `tools/`, `providers/`, `utils/`, `systemprompts/`, `conf/`, `clink/`, `tests/`, `simulator_tests/`.

## Current state (main, even with origin at 344a8ad, 2026-10-27)
Fork's own commits on top of upstream:
- `ea906ab` adds a Zhipu/GLM provider (conf/zhipu_models.json).
- `8703ab2` points the Custom model registry at the local Ollama endpoint it serves.
- `2a1984c` adds qwen-code as a clink client; `dfc5a87` adds Kimi Code CLI as a clink client (laptop-only; the commit says kimi still crashes on perrypc); `483a6e7` fixes its parser so the final physical line must be the final message.
- `29ac796` registers served-context tags in the Custom registry, opt-in by name.
- `a5fc69d` makes the `local-coder` and `qwen3-coder` aliases resolve to `qwen3-coder:30b-48k` (one resident copy on the GPU); the plain tag stays reachable by exact name.
- `1cf70d4` makes clink's qwen client authenticate against Main's Ollama via env (tailnet `OPENAI_BASE_URL`, dummy key) in an isolated `QWEN_HOME` (`.qwen-clink`), leaving the default `~/.qwen` untouched.
- `344a8ad` ignores `.env.bak*` backups.

clink clients (conf/cli_clients/): claude, codex, gemini, kimi, qwen. Parsers in clink/parsers/: base, claude, codex, gemini, kimi, qwen. Agent subclasses in clink/agents/: claude, codex, gemini, qwen.

Custom registry (conf/custom_models.json): `qwen3-coder:30b` (no aliases, 32768 ctx); `qwen2.5-coder:14b` (aliases qwen2.5-coder, local-small; 32768); `qwen3-coder:30b-48k` (aliases local-coder-48k, local-coder, qwen3-coder; 49152); `qwen3.8:27b-80k` (aliases local-planner, local-planner-80k; 81920).
CLAUDE.md notes: `DEFAULT_MODEL=auto` ranks by `intelligence_score`, with local entries scored low on purpose so auto-selection does not send traffic to the GPU; local models are used only when named explicitly. Ollama serves a 32768 context regardless of the model card; the 7900 XTX holds one large model resident at a time.

Workflow (CLAUDE.md): run `./code_quality_checks.sh` before and after changes; unit tests `pytest tests/ -m "not integration"`; restart the Claude session after code changes. Commits follow Conventional Commits (AGENTS.md).

## Open decision (Perry's)
Whether and how to upstream the fork is undecided; this file does not decide it.

## Next step
Not recorded; Perry to set.
