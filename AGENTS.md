# AI Agent Configuration

This document defines standard operating procedures, environmental constraints, and coding standards for AI coding agents working in `tin+topo's` repositories.

These instructions apply to Cursor (Grok), Codex, Claude Code, Cline, and Gemini.

## Cursor and Grok

- Cursor with Grok is the working agent in Cursor. The thread name is this repository's folder name. Role details: `../../AGENT_ROLES.md`.
- Cursor loads this file and `.cursor/rules/`. Grok CLI also loads `~/.grok/AGENTS.md`.
- Shared rules belong here. Claude-only notes belong in `CLAUDE.md`.

## Primary Objective

Make the smallest safe change that satisfies the user's request while preserving the existing repository structure, coding style, and documentation format.

## VS Code Repository Access

- Treat the currently opened VS Code workspace folder as the active repository.
- Use repository-relative paths in all explanations and edits.
- Prefer direct workspace file tools for reading, searching, creating, and editing files.
- Use open editor tabs, selected text, and visible file context when available.
- If a needed file is not visible or accessible through workspace file tools, ask the user to confirm that the correct folder is open in VS Code or to paste the relevant file contents.
- Do not invent file paths, repository structure, schemas, function names, or configuration values that have not been observed in the workspace or provided by the user.

## Working Guidelines

- Make the smallest, most efficient change that satisfies the request.
- Preserve existing code architecture, Markdown structure, and wording unless the task explicitly asks for broader refactoring or cleanup.
- Prefer plain Markdown and GitHub-supported syntax over custom HTML for documentation.
- Treat documentation and shared templates as team-wide defaults; avoid unnecessary formatting churn.
- Before editing, inspect only the files needed for the task.
- After editing, summarize the changed files and the purpose of each change.

## Documentation Updates

- **Update README Date:** If you make any significant changes to the repository's code, scripts, or dependencies, update the `Last Updated: [Date]` field in `README.md` to the current date (e.g., `YYYY-MM-DD`).

## Environment & Tooling Constraints

- **Execution Surface Matters:** Codex Desktop on managed Windows workstations may block local shell and PowerShell execution. Codex CLI running inside Ubuntu/WSL can use scoped Linux terminal commands when the user launches it from the target repo.
- **Prefer WSL for Commands:** For command-dependent inspection, tests, formatters, package tooling, or Linux-first workflows, use the WSL terminal/Codex CLI from the repository root.
- **Direct File IO Fallback:** If terminal execution is blocked in the current surface, use direct file-read, file-search, and file-write/edit tools for repository work.
- **Command-Based Verification:** When command execution is available, run narrowly scoped read-only checks or project validation commands such as `git diff`, `pytest`, `ruff`, `npm test`, or relevant script help/version checks. If commands are blocked, perform manual review and report what was not run.
- **Dependency Installation:** Do not install packages, extensions, CLIs, or system tools unless the user explicitly asks for setup or approves the install.
- **Ask When Blocked:** If the required context cannot be accessed through available tools, ask the user for the exact path, file contents, schema, or error text.


## File Editing Workflow

1. Identify the relevant file or folder from the user's request.
2. Use workspace file-search/read tools or scoped WSL commands to inspect the smallest necessary context.
3. Make targeted edits with direct file-write/edit tools or a focused patch.
4. Run relevant validation when command execution is available and safe for the repo.
5. If terminal execution is blocked, perform manual review instead of command-based validation.
6. In the final response, report:
   - files changed;
   - what changed;
   - commands run, or validation not performed because terminal execution was blocked;
   - any follow-up action the user needs to run manually.


## Validation

- For Markdown-only edits, review heading levels, links, tables, fenced code blocks, and list indentation.
- For JSON, YAML, TOML, GitHub Actions, and configuration files, validate syntax with available tooling when possible; otherwise inspect syntax carefully.
- For code edits, inspect surrounding code for imports, naming conventions, indentation, and expected side effects.
- Do not introduce generated artifacts, build outputs, lockfiles, logs, cache directories, or editor metadata such as `.vscode/` files unless explicitly requested.
- When command execution is available, run the narrowest meaningful test, formatter, linter, or syntax check. If commands are blocked, tell the user the exact command to run manually.


## GIS & Data Handling

- **No Binary Reads:** Never attempt to read binary spatial files such as `.shp`, `.dbf`, `.gdb`, `.tif`, `.img`, `.gpkg`, `.sqlite`, `.pbf`, or geodatabase contents directly into context.
- **Large Files:** Do not read large data files such as `.csv`, `.json`, or `.geojson` over 1 MB directly into context.
- **Schema Discovery:** If dataset structure is needed, ask the user to provide the schema, field list, metadata, or a small sample.
- **Helper Scripts:** You may write a short Python script that prints `head()`, `info()`, fields, geometry type, CRS, or row counts, but do not run it yourself. Ask the user to run it and paste the output.
- **Projections:** Assume spatial data uses EPSG:4326, Tennessee State Plane, or another project-standard CRS only when the repository or user states that explicitly.
- **Spatial Logic:** Add brief comments for non-obvious spatial joins, overlays, CRS transformations, dissolves, buffers, or geometry repairs.

## Script Networking Constraints

- **Corporate Proxy:** TDA team members operate behind a Zscaler corporate proxy.
- **External Requests:** When writing scripts that make external network requests, remind the user that they may need to configure the script to trust their local Zscaler certificate path.
- **TLS Verification:** Do not recommend disabling TLS verification except as a temporary internal troubleshooting step. If mentioned, clearly label `verify=False` or equivalent settings as temporary and not appropriate for production.

## Coding Standards & Preferences

- **Python:** Prefer `geopandas`, `pandas`, `arcpy`, and the ArcGIS API for Python for spatial and ArcGIS workflows.
- **Arcade:** Prefer clear, defensive Arcade expressions with explicit null handling and simple branching.
- **Notebooks:** When editing Jupyter notebooks (`.ipynb`), modify only the exact code cells requested. Avoid broad JSON rewrites.
- **Node.js:** Use ES6 syntax and prefer native `fetch` over third-party request libraries where practical.
- **Documentation:** Use concise comments for complex spatial logic, projections, assumptions, or data transformations.
- **Markdown:** Preserve existing heading style, list style, table alignment, and terminology unless the user asks for cleanup.

## Git and Pull Request Behavior

- Read-only git commands such as `git status`, `git diff`, `git log`, and `git show` may be used for context and validation when command execution is available.
- Do not stage, commit, push, reset, clean, rebase, or create branches unless the user explicitly asks for that git action.
- Never use destructive git commands to discard user work unless the user explicitly requests that exact operation.
- If a commit message or PR summary is requested, draft it from the edits made and clearly state whether git commands were run.


## When Access Fails

If repository files cannot be accessed or edited from Codex in VS Code, Codex Desktop, or Codex CLI:

- Ask the user to confirm that VS Code is opened at the repository root, not a parent folder, child folder, or disconnected workspace.
- Ask the user to open the target file in the editor or paste the relevant contents.
- Continue using the provided content rather than attempting terminal workarounds.
- Do not claim that files were changed unless a direct file-write/edit tool reported success.

## Definition of Done

A task is complete when the requested direct edits are made and the response includes a brief summary of changed files, important assumptions, and any manual validation the user should perform.

## Repository Layout

- `data/` (git-ignored): `raw/` holds original downloads (do not commit); `processed/` holds cleaned, derived spatial outputs.
- `notebooks/`: Jupyter exploration. `src/`: production code. `scripts/`: production-ready scripts.
- `.devcontainer/`: VS Code dev container config. `.env.example`: environment variable template. `.gitignore`: spatial binary and secret blocklist.

## Python Environment and Commands

- **Python Version:** 3.11 (as specified in `.devcontainer/devcontainer.json`).
- **Package Manager:** pip. Dev tools: ruff (linting) and pytest (when tests exist).
- **Install Dependencies:** Only when the user asks for setup or approves the install: `pip install -r requirements.txt` (production) and `pip install -r requirements-dev.txt` (development, includes JupyterLab).
- **Run Code:** Notebooks with `jupyter lab`; scripts with `python scripts/my_script.py` or through scheduled tasks; tests with `pytest`.
- **Lint:** `ruff check .` (ruff enforces PEP 8 conventions).
- **Test Changes:** Test changes in notebooks or scripts before committing.

## Spatial Data Storage and Practices

- **No Large Binaries in Git:** Never commit large binary spatial files (`.shp`, `.gdb`, `.tif`, `.gpkg`, etc.). See `.gitignore` for the full blocklist.
- **Storage:** Store raw data in `data/raw/` and processed outputs in `data/processed/`, both git-ignored. Document schema, CRS, and transformations in notebooks or `docs/`.
- **CRS:** State the CRS explicitly for every spatial operation. Never assume one; verify it against metadata, shapefiles, or GeoJSON properties.
- **Geometry Validation:** Check for null geometries, self-intersections, or invalid coordinates before processing.
- **Large Datasets:** For datasets over 100 MB, use `geopandas` chunking, spatial indexing, or filtering.

## ArcGIS Online and Enterprise Safety

Before modifying hosted layers, feature services, or scheduled jobs:
1. Confirm the target portal URL and account.
2. Identify item IDs and service names.
3. Prefer dry-run behavior for new scripts.
4. Never overwrite services or truncate data without explicit user confirmation.

## Environment Variables and Secrets

- Use `.env.example` as the template. Keep a local `.env` (git-ignored) for ArcGIS Online credentials, API keys, portal URLs or service names, and other sensitive configuration.
- Never commit actual credentials to Git.

## Cursor Cloud specific instructions

- The map gallery is a static site with no build step. The environment start script serves the repository root at `http://localhost:8000` with `python3 -m http.server 8000 --bind 0.0.0.0`. `http://localhost:8000/?year=2026` opens a specific year.
- Project Python is 3.11 in `.venv`. Run `.venv/bin/ruff check .` and `.venv/bin/python -m compileall -q src scripts`. Pytest runs when a `tests/` directory exists.
- Ubuntu 24.04 does not ship Python 3.11. Install adds the deadsnakes PPA, then `python3.11`, `python3.11-venv`, `python3.11-dev`, and `libkrb5-dev` (required to build the `arcgis` Kerberos dependency), then `pip install -r requirements-dev.txt` inside `.venv`.
