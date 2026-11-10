# Claude Code configuration

@AGENTS.md

`AGENTS.md` is the canonical instruction file for this repository. Everything in it applies to Claude Code. This file adds only Claude-specific notes.

## Claude Code role

- Claude Code is the quality and security reviewer for this repo, and picks up unfinished work if Cursor/Grok or Codex runs out of tokens. Role details are in `../../AGENT_ROLES.md`, in the github folder above the repo.
- Review changes against the verification commands in `AGENTS.md` before reporting them complete.
- Do not duplicate or override `AGENTS.md` rules here. If a rule belongs for both Codex and Claude, put it in `AGENTS.md`.
- Claude Code help: run `/help` in Claude Code, or report bugs at https://github.com/anthropics/claude-code/issues.

## Agent skills

### Issue tracker

GitHub Issues in this repo (via `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
