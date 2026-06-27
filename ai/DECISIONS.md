# pal-mcp-server Decisions

## Session 2 — Resolve push auth for `pal-mcp-server`

### 1. Use the personal fork instead of pushing directly to the org repo
- **Decision:** Add `pmartin1915/pal-mcp-server` as a remote named `fork` and push local `main` to a branch called `session-1-hygiene`.
- **Rationale:** The GitHub account has no write access to `BeehiveInnovations/pal-mcp-server`, but it owns a fork with push permissions. Pushing directly to the org repo is impossible without a permissions change.

### 2. Preserve the fork's existing commits rather than force-push
- **Decision:** Push local `main` to a new branch on the fork instead of overwriting `fork/main`.
- **Rationale:** `fork/main` had diverged from `origin/main` with later work. Force-pushing would have lost those commits.

### 3. Track the fork branch for local `main`
- **Decision:** Set `main` upstream to `fork/session-1-hygiene` so future `git push` commands succeed by default.
- **Rationale:** Provides the same ergonomics as a normal push while keeping the org repo as the upstream fetch source.
