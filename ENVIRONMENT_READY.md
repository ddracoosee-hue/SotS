# SotS environment handoff

Verified 2026-09-29. Ready for Muse to begin P00 implementation.

## Start here

Read MUSE_START_HERE.md, then follow its blueprint reading order and tasks/P00_skeleton.md.
The dependency environment is prepared; the application and phase acceptance checks are
not implemented. No task checkboxes have been marked complete.

From PowerShell in C:\Users\ddrac\SotS:

```powershell
uv sync --locked
uv run python --version
uv run pytest
uv run ruff check .
# Once Muse creates src/:
uv run pyright
```

Use `uv run` for project commands, or select this interpreter in your agent/editor:
`C:\Users\ddrac\SotS\.venv\Scripts\python.exe`.
Activation is optional. The system `py` launcher defaults to Python 3.14; avoid bare `py`
for this project. `.python-version` pins the installed 3.12.10 interpreter and
`requires-python` restricts the project to Python 3.12.

## Installed and verified

- Python 3.12.10, 64-bit, with pip 25.0.1 in the base installation.
- uv 0.12.20, available directly on PATH.
- Project-local .venv with all 17 direct packages from blueprint/02_ARCHITECTURE.md
  section 6, including the five development tools; 55 installed packages total.
- uv.lock records exact dependency versions; `uv sync --locked` succeeds.
- `uv pip check` reports all installed packages compatible.
- Every approved package imports successfully.
- SQLite 3.49.1 with working FTS5, DOCX and PDF in-memory round trips, and HTTPS to PyPI.
- pytest 9.1.1, Ruff 0.16.9, Pyright 1.1.414 start successfully.
- pytest collection runs; exit code 5 is expected because there are no tests yet.
- Ruff runs successfully; there is no application Python source to lint/type-check yet.
- Git 2.55.0.windows.2; local repository initialized on main, with no commit or remote.
- Ignore rules verified for profile/, data/, supplements/, .env and .venv/.
- Node 24.18.1 and npm 12.0.2 already installed; no JavaScript dependencies required.
- Ollama 0.32.13 responds at http://127.0.0.1:11434 with 18 installed models,
  including qwen3:14b. No model selection or inference-quality claim is made.
- Hardware: approximately 63.1 GiB RAM, NVIDIA RTX 4070 Ti SUPER, and approximately
  198 GiB free on C: before this dependency installation.

## Prepared files and remaining P00 work

- pyproject.toml: approved runtime packages, development dependency group, lint/type/test
  settings. Live tests are excluded by default.
- .python-version, uv.lock and .venv: reproducible Python environment.
- .gitignore: private author material, secrets, environment and build artifacts excluded.
- .env.example: empty placeholders for the seven required names; no credentials added.

The manifest temporarily uses `[tool.uv] package = false` because there is no application
package yet. During P00, Muse must add the src/sots package, configure its build backend,
enable package installation, and add `sots = "sots.cli:app"` under project.scripts.
Then resync and verify the CLI. Do not assume T00.001/T00.002 or P00 are complete.
No application, sots CLI, configuration tree or tests have been built by this setup.
Blueprint, profile and task files were left unchanged.

## Later live-service setup (does not block coding or offline tests)

- Docker CLI 29.7.2 is installed, but Docker Desktop's Linux engine is not running.
- No service responded on localhost ports 8080 (search convention) or 8081
  (blueprint LanguageTool default); SearXNG/LanguageTool were not installed or configured
  by this setup. A service on another port was not ruled out.
- Choose and configure the local model/context under OI-05; existing models are available.
- Muse endpoint/auth/model details remain OI-03; use the blueprint's stub during development.
- SearXNG is the default search option (OI-07); configure its service for live research.
- LanguageTool setup remains OI-21; the approved default is degraded LLM-only mode.
- API credentials (OI-08) must be supplied privately in .env when needed. Key-gated
  fetchers stay disabled until configured. No live paid API calls were made.
- Tests should use FakeProvider and mocked HTTP according to the blueprint.

## Tooling issue observed

The Codex sandbox command runner repeatedly failed before launching a process with
`timed out after 15000ms connecting runner pipe-in`. Authorized commands outside that
runner worked, and all verification above ran through that path. This is a separate
Codex execution issue, not a Python installation failure. If Muse uses the same failing
runner, it needs a working execution session before it can run build commands.

uv installation/dependency reference: https://docs.astral.sh/uv/getting-started/installation/
and https://docs.astral.sh/uv/concepts/projects/dependencies/.
