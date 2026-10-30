# Claude Code configuration

@AGENTS.md

`AGENTS.md` is the canonical instruction file for this repository. Everything in it applies to Claude Code. This file adds only Claude-specific notes.

## Claude Code role

- Claude Code is the quality and security reviewer for this repo, and picks up Codex's unfinished work if Codex runs out of tokens. Role details are in `../../AGENT_ROLES.md`, in the github folder above the repo.
- Review changes against the verification commands in `AGENTS.md` before reporting them complete.
- Do not duplicate or override `AGENTS.md` rules here. If a rule belongs for both Codex and Claude, put it in `AGENTS.md`.
- Claude Code help: run `/help` in Claude Code, or report bugs at https://github.com/anthropics/claude-code/issues.
