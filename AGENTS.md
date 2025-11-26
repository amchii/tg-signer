# Repository Guidelines

Follow these notes to keep contributions consistent and low-friction for the project maintainers.

## Project Structure & Module Organization
- `tg_signer/` main package: `__main__.py` entrypoint, `cli/` (Click commands for signer/monitor flows), `core.py` scheduling & action logic, `config.py` config models, `notification/` (server_chan hooks), `webui/` NiceGUI app, and shared helpers in `utils.py`.
- `tests/` houses Pytest suites for config conversion, matching, and core behaviors.
- `docker/` contains build/run instructions; `build/` and `dist/` hold artifacts; session files and logs stay local, not versioned.

## Build, Test, and Development Commands
- Create a venv: `python -m venv .venv && source .venv/bin/activate`.
- Install for local hacking: `pip install -e .` (add `pip install ruff pytest tox` for tooling).
- Lint: `ruff check tg_signer tests`.
- Tests: `pytest -vv tests/` for quick runs; `tox` exercises py310/py311/py312.
- Run CLI: `python -m tg_signer --help` or `tg-signer run` after install; launch the UI with `python -m tg_signer.webui`.

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indents, and type hints where practical.
- Follow the ruff config (line length 88; bugbear/comprehension rules enabled; long lines handled by `E501` ignore).
- Use `snake_case` for modules/functions/variables, `PascalCase` for classes, and keep CLI options `kebab-case` per Click defaults.
- Prefer explicit logging via `tg_signer.logger` and focused exception handling over bare `except`.

## Testing Guidelines
- Pytest with `pytest-asyncio`; mark async tests with `@pytest.mark.asyncio`.
- Name files `test_*.py` and tests `test_*` under `tests/` for discovery.
- Lean on fixtures for session/config setup; add regression cases when touching config migration (`test_sign_config_v2_to_v3.py`) or matching logic.
- Run `pytest -vv` before PRs; add targeted cases when adding CLI flags or web UI flows.

## Commit & Pull Request Guidelines
- Commit style mirrors history (`feat(webui): ...`, `fix(core): ...`, `chore:`); include scope when helpful and optional issue refs `(#123)`.
- Keep commits focused and narrative (what/why). Do not commit secrets or local session/log/db artifacts.
- PRs should outline behavior changes, tests run, and UX impact (CLI snippets or web UI screenshots when relevant).
- Link related issues/discussions and request review after tests pass.

## Security & Configuration Tips
- Treat `*.session`, `*.session_string`, `test.db`, and `tg-signer.log` as sensitive; keep them out of VCS and shared logs.
- Use `--workdir` (default `.signer`) for configs/records; set keys like `TG_PROXY`, `TG_SESSION_STRING`, `OPENAI_API_KEY`, and `OPENAI_BASE_URL` via env vars rather than checked-in files.
