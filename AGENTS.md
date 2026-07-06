# AGENTS.md

## Mission-critical map
- Main runtime is `runAiBot.py` (Selenium bot + job extraction + MongoDB writes).
- Web UI/API is `app.py` + `templates/index.html` (Flask server-side pagination over MongoDB).
- Shared automation primitives live in `modules/clickers_and_finders.py` and `modules/helpers.py`.
- Browser session is created at import-time in `modules/open_chrome.py`; importing this module launches Chrome immediately.
- Persistence contract is centralized in `modules/db.py` (single collection `linkedin-jobs`, unique `job_id`, `visits_count`, `last_seen`).
- `config/resume.py` exists but is currently an inert stub (no runtime imports); do not rely on it.
- MongoDB is **required** for all data writes; `use_mongodb = False` in `config/settings.py` means no job data is saved.

## Data flow (why structure matters)
- `main()` in `runAiBot.py` validates config (`validate_config()`), initializes MongoDB, logs in, then runs `apply_to_jobs()`.
- Job records are upserted through `submitted_jobs()`, `skipped_job()`, and `failed_job()` in `runAiBot.py`, each calling `modules.db.upsert_job`.
- Deduplication is live DB-based (`is_already_seen()` -> `check_and_touch_job()`), not preload CSV-based.
- UI endpoints in `app.py` read the same collection via `get_jobs_paginated()`:
  - `/active-jobs` — jobs with status `"Active"`, `"New"`, or `""` (replaces the old `/applied-jobs`).
  - `/active-jobs/summary` — per-company job counts via `get_company_job_counts()` aggregation.
  - `/active-jobs/<job_id>` PUT — updates `date_applied` via `update_job_date()`.
  - `/skipped-jobs` — status `"Skipped"`.
  - `/failed-jobs` — status `"Failed"`.
- `app.py` lazy-initializes MongoDB via `get_mongo_db()` (not at import time).
- Frontend filters in `templates/index.html` map directly to query params consumed in `app.py`.
- `_map_job_doc()` in `app.py` now exposes `Company_ID`, `Company_Website`, `Job_Category`, `Number_of_Applications`, `Is_Easy_Apply`, `Re_posted`, `Visits_Count`, `Last_Seen` — adding new fields here requires matching table columns in `templates/index.html`.

## Current behavioral mode
- This branch is explicitly **Data Capture Mode**: `runAiBot.py` records job metadata and statuses, but does not submit applications.
- `is_easy_apply` detection uses strict XPath: `//button[@id='jobs-apply-button-id' and contains(@aria-label,'Easy Apply')]`.
- If `run_in_background = True`, startup forces `pause_before_submit = False`, `pause_at_failed_question = False`, and `run_non_stop = False`.
- Job statuses written to MongoDB: `"New"` (first-seen, not yet applied), `"Applied"` (LinkedIn Applied badge detected), `"Skipped"` (filtered out), `"Failed"` (error during processing).
- `search_terms` in `config/search.py` supports two formats:
  - Plain string: `"Software Engineer"` → broad match, no quotes in URL.
  - Dict: `{"terms": ["Software Engineer", "Java"], "operator": "AND"}` → `"Software Engineer" AND "Java"` in URL. Converted by `build_keywords()` in `runAiBot.py`.
- `minimum_company_size` in `config/search.py` filters by LinkedIn employee count from the About Company section (not total company headcount). Set to `0` to disable.
- `job_description_good_words` + `job_description_good_words_operator` (`"OR"` / `"AND"`) in `config/search.py` skip jobs missing required keywords.

## Developer workflows
- Setup scripts are under `setup/` (`windows-setup.bat`, `windows-setup.ps1`, `setup.sh`) for ChromeDriver/bootstrap.
- Typical local runs:
  - `python runAiBot.py` (bot)
  - `python app.py` (history dashboard at `http://localhost:5000`)
- There is no `requirements.txt`/`pyproject.toml`; dependency install is documented in `README.md`.
- No automated test suite is present; use smoke checks: run bot, inspect `logs/log.txt`, then verify dashboard/API responses.

## Project-specific conventions
- Config is Python modules in `config/` (not env vars): `personals.py`, `questions.py`, `resume.py` (stub), `search.py`, `secrets.py`, `settings.py`.
- New config keys should be added to validation in `modules/validator.py`.
- Mixed naming style is intentional: many globals in snake_case, many locals in camelCase.
- Use `print_lg()` for logging so messages are mirrored to `logs/log.txt`.
- Preserve MongoDB/UI field compatibility with `_map_job_doc()` in `app.py` and table rendering in `templates/index.html`.
- `config/search.py` has two distinct blacklist mechanisms:
  - `blacklisted_company_names` — exact company name match at job-card stage (before clicking), case-insensitive.
  - `about_company_bad_words` — keyword match inside the About Company section text (checked after opening job).
- `config/questions.py` has an expanded set of form-answer fields including: `gender_identity`, `race_ethnicity`, `require_visa_sponsorship`, `work_authorization_us`, `open_to_relocation`, `preferred_hub_city`, `hiring_manager_message`, `reasonable_accommodation`, `protected_veteran_status`, `relatives_in_company`, `relatives_names`, `acknowledge_privacy_policy`, `notice_period_selection`, `legal_work_authorization`, `has_cs_degree`, `how_did_you_hear`, `other_languages_fluent`, `primary_motivation`, `current_company`, `current_title`. Add new answer fields here and validate them in `modules/validator.py`.
- `config/settings.py` contains MongoDB connection config (`use_mongodb`, `mongodb_uri`, `mongodb_database`).

## Integration points and risks
- LinkedIn DOM/XPath coupling is tight; selector changes can break login/filter/apply-type detection.
- **LinkedIn login (May 2026):** LinkedIn now uses dynamic element IDs. Login selectors must use stable attribute XPaths:
  - Email: `//input[@type="email" and contains(@autocomplete,"username")]`
  - Password: `//input[@type="password" and @autocomplete="current-password")]`
  - Submit: `//button[.//span[normalize-space(text())="Sign in"]]`
  - React-controlled inputs require `_js_set_input_value()` (native setter + bubbling `input`/`change` events); plain `element.send_keys()` may not register.
- External services: MongoDB (`config/settings.py`), optional OpenAI/DeepSeek/Gemini (`modules/ai/*`).
- AI provider routing is done in `runAiBot.py` via `config/secrets.py` (`ai_provider`).
- Browser automation relies on Selenium and optional `undetected_chromedriver` (`stealth_mode`).

## Repo hygiene for agents
- Treat `config/secrets.py` as sensitive; do not expose credentials/tokens in commits or logs.
- Preserve graceful shutdown behavior in `runAiBot.py` (`atexit` + signal handlers) when refactoring startup/exit paths.
- Do not bypass `modules/db.py` for writes unless you also preserve upsert/index semantics and `last_seen`/`visits_count` behavior.
