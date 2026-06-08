# AGENTS.md

## Mission-critical map
- Main runtime is `runAiBot.py` (Selenium bot + job extraction + MongoDB writes).
- Web UI/API is `app.py` + `templates/index.html` (Flask server-side pagination over MongoDB).
- Shared automation primitives live in `modules/clickers_and_finders.py` and `modules/helpers.py`.
- Browser session is created at import-time in `modules/open_chrome.py`; importing this module launches Chrome immediately.
- Persistence contract is centralized in `modules/db.py` (single collection `linkedin-jobs`, unique `job_id`, `visits_count`, `last_seen`).

## Data flow (why structure matters)
- `main()` in `runAiBot.py` validates config (`validate_config()`), initializes MongoDB, logs in, then runs `apply_to_jobs()`.
- Job records are upserted through `submitted_jobs()`, `skipped_job()`, and `failed_job()` in `runAiBot.py`, each calling `modules.db.upsert_job`.
- Deduplication is live DB-based (`is_already_seen()` -> `check_and_touch_job()`), not preload CSV-based.
- UI endpoints in `app.py` (`/applied-jobs`, `/skipped-jobs`, `/failed-jobs`) read the same collection via `get_jobs_paginated()`.
- Frontend filters in `templates/index.html` map directly to query params consumed in `app.py`.

## Current behavioral mode
- This branch is explicitly **Data Capture Mode**: `runAiBot.py` records job metadata and statuses, but does not submit applications.
- `is_easy_apply` detection uses strict XPath: `//button[@id='jobs-apply-button-id' and contains(@aria-label,'Easy Apply')]`.
- If `run_in_background = True`, startup forces `pause_before_submit = False`, `pause_at_failed_question = False`, and `run_non_stop = False`.

## Developer workflows
- Setup scripts are under `setup/` (`windows-setup.bat`, `windows-setup.ps1`, `setup.sh`) for ChromeDriver/bootstrap.
- Typical local runs:
  - `python runAiBot.py` (bot)
  - `python app.py` (history dashboard at `http://localhost:5000`)
- There is no `requirements.txt`/`pyproject.toml`; dependency install is documented in `README.md`.
- No automated test suite is present; use smoke checks: run bot, inspect `logs/log.txt`, then verify dashboard/API responses.

## Project-specific conventions
- Config is Python modules in `config/` (not env vars): `personals.py`, `questions.py`, `search.py`, `secrets.py`, `settings.py`.
- New config keys should be added to validation in `modules/validator.py`.
- Mixed naming style is intentional: many globals in snake_case, many locals in camelCase.
- Use `print_lg()` for logging so messages are mirrored to `logs/log.txt`.
- Preserve MongoDB/UI field compatibility with `_map_job_doc()` in `app.py` and table rendering in `templates/index.html`.

## Integration points and risks
- LinkedIn DOM/XPath coupling is tight; selector changes can break login/filter/apply-type detection.
- External services: MongoDB (`config/settings.py`), optional OpenAI/DeepSeek/Gemini (`modules/ai/*`).
- AI provider routing is done in `runAiBot.py` via `config/secrets.py` (`ai_provider`).
- Browser automation relies on Selenium and optional `undetected_chromedriver` (`stealth_mode`).

## Repo hygiene for agents
- Treat `config/secrets.py` as sensitive; do not expose credentials/tokens in commits or logs.
- Preserve graceful shutdown behavior in `runAiBot.py` (`atexit` + signal handlers) when refactoring startup/exit paths.
- Do not bypass `modules/db.py` for writes unless you also preserve upsert/index semantics and `last_seen`/`visits_count` behavior.
