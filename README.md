# LinkedIn AI Auto Job Applier 🤖

An intelligent automation bot that logs in to LinkedIn, searches for jobs matching your criteria, detects Easy Apply vs. External Apply buttons, answers application questions, and persists all job data to MongoDB with a real-time history dashboard.

---

## ✨ Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#️-installation)
- [Configuration](#-configuration)
  - [secrets.py](#1-secretspy)
  - [personals.py](#2-personalspy)
  - [questions.py](#3-questionspy)
  - [search.py](#4-searchpy)
  - [settings.py](#5-settingspy)
- [MongoDB Setup](#-mongodb-setup)
- [Running Locally](#️-running-locally)
  - [Run the Bot — runAiBot.py](#run-the-bot--runaiботpy)
  - [Run the Dashboard — app.py](#run-the-dashboard--apppy)
- [Applied Jobs History UI](#️-applied-jobs-history-ui)
- [Data Capture Mode](#️-data-capture-mode)
- [Reposted Jobs Handling](#-reposted-jobs-handling)
- [Continuous Mode](#-continuous-mode-run_non_stop)
- [Contributor Guidelines](#-contributor-guidelines)
- [Major Updates History](#️-major-updates-history)
- [Disclaimer](#-disclaimer)
- [Terms and Conditions](#️-terms-and-conditions)
- [License](#️-license)
- [Socials](#-socials)

---

## 🚀 Features

- 🔍 Searches LinkedIn jobs using your configured search terms and filters
- 🤖 Automatically detects Easy Apply vs. External Apply buttons (strict SVG+aria XPath)
- 📋 Answers all Easy Apply application questions automatically
- 📄 Customizes resumes using AI (OpenAI / DeepSeek / Gemini / local LLM via Ollama)
- 🗄️ Persists all job data to **MongoDB** (`is_easy_apply`, `status`, `reposted`, etc.)
- 🏃 Runs continuously across all pages with `run_non_stop = True`
- 📊 **Data Capture Mode** — browse and save job details without submitting applications
- ♻️ **Reposted Jobs Detection** — detects and skips reposted jobs
- 🖥️ **Applied Jobs History Dashboard** — view all jobs at `http://localhost:5000` with pagination, filters, and search
- 🛡️ Skips already-applied jobs (captures status, does not re-click)
- 📝 Detailed logs with reasons for skips, failures, and termination
- 🖥️ Runs in background or visible window mode

[back to top](#linkedin-ai-auto-job-applier-)

---

## 📋 Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **Python** | 3.10+ | [Download](https://www.python.org/downloads/) — must be added to PATH |
| **Google Chrome** | Latest | [Download](https://www.google.com/chrome) — install in default location |
| **MongoDB** | 6.0+ | [Download Community](https://www.mongodb.com/try/download/community) — or use MongoDB Atlas |
| **ChromeDriver** | Matches Chrome | Not needed if `stealth_mode = True` |

[back to top](#linkedin-ai-auto-job-applier-)

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/3cor/LinkedIn-Bot.git
cd LinkedIn-Bot
```

### 2. Create a virtual environment (recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install required packages

```bash
pip install undetected-chromedriver pyautogui setuptools openai flask flask-cors pymongo
```

> If a `requirements.txt` is present: `pip install -r requirements.txt`

### 4. Install ChromeDriver *(skip if `stealth_mode = True`)*

**Option A — Auto install (Windows):**
```
Run: setup\windows-setup.bat
```

**Option B — Manual:**
- Go to https://googlechromelabs.github.io/chrome-for-testing/
- Download the version matching your installed Chrome
- Place `chromedriver.exe` where Chrome is installed  
  e.g. `C:\Program Files\Google\Chrome\Application\`

### 5. Start MongoDB

```bash
# Windows — if installed as a service
net start MongoDB

# Or start manually
mongod --dbpath "C:\data\db"
```

> For **MongoDB Atlas**, update `mongodb_uri` in `config/settings.py` with your Atlas connection string.

[back to top](#linkedin-ai-auto-job-applier-)

---

## 🔧 Configuration

All configuration files are in the `/config` folder. Edit each file before running the bot.

### 1. `secrets.py`

LinkedIn credentials and AI provider settings.

```python
# LinkedIn login
username = "your_email@example.com"
password = "your_password"

# AI (set use_AI = False to disable)
use_AI      = False
ai_provider = "openai"                        # "openai", "deepseek", "gemini"
llm_api_url = "https://api.openai.com/v1/"
llm_api_key = "sk-..."                        # Your API key
llm_model   = "gpt-4o-mini"
```

> If credentials are left blank, the bot tries a saved browser profile or prompts for manual login.

### 2. `personals.py`

Personal details used to auto-fill application forms.

```python
first_name   = "John"
last_name    = "Doe"
phone_number = "1234567890"
current_city = "New York"
state        = "NY"
zipcode      = "10001"
country      = "United States"
ethnicity    = "Decline"
gender       = "Decline"
disability_status = "No"
veteran_status    = "No"
```

### 3. `questions.py`

Answers to common application questions.

```python
default_resume_path       = "all resumes/default/resume.pdf"
years_of_experience       = "5"
require_visa              = "No"
desired_salary            = 120000
us_citizenship            = "U.S. Citizen/Permanent Resident"
notice_period             = 30       # days
pause_before_submit       = True     # Pause for manual review before submitting
pause_at_failed_question  = True     # Pause on unknown questions
overwrite_previous_answers = False
```

### 4. `search.py`

Job search preferences and filters.

| Setting | Description | Example |
|---|---|---|
| `search_terms` | Job titles to search | `["Java Developer", "Lead Software Engineer"]` |
| `search_location` | Location filter | `"United States"` |
| `sort_by` | Sort order | `"Most recent"` / `"Most relevant"` |
| `date_posted` | Date filter | `"Past 24 hours"`, `"Past week"`, `"Any time"` |
| `experience_level` | Filter by level | `["Mid-Senior level", "Director"]` |
| `job_type` | Job type | `["Full-time", "Contract"]` |
| `on_site` | Work mode | `["Remote", "Hybrid"]` |
| `about_company_bad_words` | Skip companies with these words | `["Staffing", "Recruiting"]` |
| `bad_words` | Skip jobs with these words in description | `["No Sponsorship", "C2C"]` |
| `minimum_company_size` | Min LinkedIn employee count | `250` (set `0` to disable) |
| `current_experience` | Your years of experience | `5` (set `-1` to apply to all) |
| `security_clearance` | Skip jobs requiring clearance | `False` |

### 5. `settings.py`

Bot behavior and MongoDB connection.

| Setting | Description | Default |
|---|---|---|
| `use_mongodb` | Store jobs in MongoDB (required for dashboard) | `True` |
| `mongodb_uri` | MongoDB connection URI | `"mongodb://localhost:27017"` |
| `mongodb_database` | Database name | `"linkedin"` |
| `run_non_stop` | Run through all pages continuously | `True` |
| `close_tabs` | Close external application tabs | `False` |
| `follow_companies` | Auto-follow after Easy Apply | `False` |
| `run_in_background` | Hide Chrome window | `False` |
| `click_gap` | Max seconds between clicks | `4` |
| `safe_mode` | Open Chrome in guest profile | `True` |
| `smooth_scroll` | Smooth vs instant scrolling | `True` |
| `keep_screen_awake` | Prevent PC sleep during run | `True` |
| `stealth_mode` | Undetected Chrome mode (experimental) | `False` |
| `showAiErrorAlerts` | Show AI API error alerts | `False` |
| `alternate_sortby` | Alternate sort between runs | `False` |
| `cycle_date_posted` | Cycle through date filters | `False` |
| `file_name` | Applied jobs CSV path | `"all excels/all_applied_applications_history.csv"` |
| `failed_file_name` | Failed jobs CSV path | `"all excels/all_failed_applications_history.csv"` |
| `logs_folder_path` | Logs and screenshots folder | `"logs/"` |

[back to top](#linkedin-ai-auto-job-applier-)

---

## 🗄️ MongoDB Setup

MongoDB is used to persist all job data and power the history dashboard.

### Local MongoDB

1. Install [MongoDB Community Edition](https://www.mongodb.com/try/download/community)
2. Start the service:
   ```bash
   # Windows
   net start MongoDB

   # macOS / Linux
   sudo systemctl start mongod
   ```
3. In `config/settings.py`:
   ```python
   use_mongodb      = True
   mongodb_uri      = "mongodb://localhost:27017"
   mongodb_database = "linkedin"
   ```

### MongoDB Atlas (Cloud)

1. Create a free cluster at [cloud.mongodb.com](https://cloud.mongodb.com)
2. Get your connection string
3. In `config/settings.py`:
   ```python
   use_mongodb      = True
   mongodb_uri      = "mongodb+srv://user:password@cluster.mongodb.net/?retryWrites=true&w=majority"
   mongodb_database = "linkedin"
   ```

> The database and collection (`linkedin_jobs`) are created **automatically** on first run.

### Key Fields in `linkedin_jobs` Collection

| Field | Type | Description |
|---|---|---|
| `job_id` | string | LinkedIn job ID (unique key) |
| `title` | string | Job title |
| `company` | string | Company name |
| `is_easy_apply` | bool | `True` = Easy Apply button detected, `False` = External |
| `status` | string | `Applied`, `New`, `Skipped`, `Failed` |
| `reposted` | bool | Whether the job is a repost |
| `date_applied` | datetime/string | When applied (or `"Not Applied - ..."`) |
| `job_link` | string | Full LinkedIn job URL |
| `visits_count` | int | Number of times the bot has seen this job |
| `last_seen` | datetime | Last time the bot visited this job |

[back to top](#linkedin-ai-auto-job-applier-)

---

## ▶️ Running Locally

### Run the Bot — `runAiBot.py`

The main automation script: logs in, searches, detects apply type, and saves data.

#### Steps

**1. Activate your virtual environment**
```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**2. Start MongoDB** (if `use_mongodb = True`)
```bash
# Windows service
net start MongoDB

# Or manually
mongod --dbpath "C:\data\db"
```

**3. Configure** all files in `/config` (see [Configuration](#-configuration) above)

**4. Run the bot**
```bash
python runAiBot.py
```

**5. What happens**
- Chrome opens and navigates to LinkedIn
- Bot logs in using `config/secrets.py` credentials
- Searches jobs from `config/search.py`
- For each job:
  - Detects Easy Apply (`is_easy_apply = True`) or External Apply (`is_easy_apply = False`)
  - Detects already-applied badge → sets `status = Applied`
  - Saves all data to MongoDB
  - If Easy Apply: fills and submits the application form (when not in data capture mode)
- If `pause_before_submit = True`, bot pauses for manual review before each submit
- All events logged to `logs/` folder

#### Common run options

| Goal | Config |
|---|---|
| Show Chrome window | `run_in_background = False` in `settings.py` |
| Run headless (hidden) | `run_in_background = True` in `settings.py` |
| Stop after one pass | `run_non_stop = False` in `settings.py` |
| Run all pages | `run_non_stop = True` in `settings.py` |
| Pause before submit | `pause_before_submit = True` in `questions.py` |
| Skip unknown questions | `pause_at_failed_question = True` in `questions.py` |

---

### Run the Dashboard — `app.py`

A Flask web app showing job history from MongoDB with pagination, filters, and search.

#### Steps

**1. Activate your virtual environment**
```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**2. Ensure MongoDB is running** and `use_mongodb = True` in `config/settings.py`

**3. Start the Flask server**
```bash
python app.py
```

**4. Open in browser**
```
http://localhost:5000
```

The dashboard can run **simultaneously** with the bot — refresh to see new jobs as they are added.

#### Run on a custom port

```bash
# Windows
set FLASK_APP=app.py
flask run --port 8080

# macOS / Linux
FLASK_APP=app.py flask run --port 8080
```

#### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /` | GET | Job history dashboard |
| `GET /applied-jobs` | GET | Paginated Applied/New jobs |
| `GET /skipped-jobs` | GET | Paginated Skipped jobs |
| `GET /failed-jobs` | GET | Paginated Failed jobs |
| `PUT /applied-jobs/<job_id>` | PUT | Mark job as applied (sets `date_applied = now`) |

#### Query Parameters

| Parameter | Values | Default | Description |
|---|---|---|---|
| `page` | integer | `1` | Page number |
| `page_size` | `10`, `20`, `50`, `100` | `20` | Rows per page |
| `is_easy_apply` | `true` / `false` | — | Filter by apply type |
| `status` | `Applied` / `New` | — | Filter by status |
| `hide_reposted` | `true` | — | Exclude reposted jobs |
| `search` | string | — | Search title or company |

[back to top](#linkedin-ai-auto-job-applier-)

---

## 🖥️ Applied Jobs History UI

Open `http://localhost:5000` after running `python app.py`.

### Tabs

| Tab | Description |
|---|---|
| ✅ Applied | Jobs with status `Applied` or `New` |
| ⏭️ Skipped | Jobs skipped (bad words, blacklist, experience mismatch, etc.) |
| ❌ Failed | Jobs where the bot encountered an error |

### Features

- **Server-side Pagination** — page sizes: 10 / 20 / 50 / 100 — data fetched directly from MongoDB
- **Filters** — Hide Reposted, Easy Apply Only, External Only, Applied Only, New Only
- **Search** — real-time search by title, company, skip/error reason
- **Badges** — Easy Apply 🔵, Reposted 🟠, Applied 🟢, New 🟡, Skipped 🔴, Failed 🟤
- **Mark as Applied** — click an external apply link to record your manual application date
- **Stats bar** — live counts of applied, new, easy apply, and reposted jobs

[back to top](#linkedin-ai-auto-job-applier-)

---

## ⚠️ Data Capture Mode

The bot can browse LinkedIn jobs and save details to MongoDB **without submitting any applications**.

### What it does

- ✅ Logs in and searches jobs
- ✅ Detects Easy Apply vs. External Apply (`is_easy_apply` saved to MongoDB)
- ✅ Extracts: title, company, website, category, HR info, repost status, applicant count
- ✅ Captures already-applied status without re-clicking
- ❌ Does **NOT** submit any applications

### Enabling real applications

Search for `"COMMENTED OUT:"` in the `apply_to_jobs()` function in `runAiBot.py` and follow inline instructions to uncomment the application logic.

[back to top](#linkedin-ai-auto-job-applier-)

---

## ♻️ Reposted Jobs Handling

The bot detects reposted jobs and handles them based on configuration.

```python
# config/settings.py
skip_reposted_jobs = True    # True or False
```

| Value | Behavior |
|---|---|
| `True` | Reposted jobs are **skipped** and stored with `reposted = True` in MongoDB |
| `False` | Reposted jobs are treated like any other job |

[back to top](#linkedin-ai-auto-job-applier-)

---

## 🔄 Continuous Mode (`run_non_stop`)

```python
# config/settings.py
run_non_stop = True    # True or False
```

- Navigates to the next page when the current page is exhausted
- Continues until there are no more jobs to process
- Logs a termination reason if stopped mid-run
- **Note:** Automatically `False` when `run_in_background = True`

[back to top](#linkedin-ai-auto-job-applier-)

---

## 🧑‍💻 Contributor Guidelines

All contributions are appreciated — no matter how small or big.

> **NOTE:** Only Pull Requests to the `community-version` branch will be accepted. PRs to `main` will be declined.

### Code Guidelines

#### Functions
1. **lowercase snake_case** naming
2. Must include a docstring:
   ```python
   def function() -> None:
       '''
       Brief description of what this function does.
       '''
   ```
3. Parameter and return types must be annotated:
   ```python
   def function(param1: str, param2: list[str]) -> str:
   ```

#### Variables
- **Local variables** → camelCase: `jobListingsElement`, `localBufferTime`
- **Global variables** → snake_case: `total_runs`, `easy_applied_count`

#### Configuration Variables
1. Must include an explanation comment with valid value examples:
   ```python
   # Do you want to randomize the search order?
   randomize_search_order = False     # True or False
   ```
2. Must be validated in `/modules/validator.py`

### Attestation

Wrap your contributions:
```python
##> ------ <Your full name> : <github id> OR <email> - <Type of change> ------
    print("My contribution")
##<
```

[back to top](#linkedin-ai-auto-job-applier-)

---

## 🗓️ Major Updates History

### May 31, 2026
- Removed all `GodsScion` sponsor links across all modules
- `is_easy_apply` detection: strict XPath `//button[@id='jobs-apply-button-id' and contains(@aria-label,'Easy Apply')]` — no fallback, no broad aria-label match
- `is_easy_apply` flag correctly saved to MongoDB for all statuses: applied, skipped, failed
- Server-side pagination on Jobs History UI — page sizes 10 / 20 / 50 / 100, fetched from MongoDB on demand

### Apr 11, 2026
- **External Apply URL** displayed in Jobs History UI with `[Open]` and `[Copy]` buttons
- **Data Capture Mode** — browse and save job details without submitting applications
- **Reposted Jobs Handling** — `skip_reposted_jobs` flag; stored in MongoDB with `reposted = True`
- **Continuous Mode** — `run_non_stop = True` navigates all pages until last job
- `sort_by = "Most recent"` applied by default
- Fixed: filter selection too fast causing radio buttons to be missed
- Fixed: `Setting the preferences failed!` — errors logged and continue
- Fixed: premature termination — bot now continues to next page/search
- Already-applied jobs: capture status only, do not re-click
- Termination now always logs a reason before exiting

### Jan 20, 2026
- You can now use Chrome simultaneously while the bot applies in a new window

[back to top](#linkedin-ai-auto-job-applier-)

---

## 📜 Disclaimer

**This program is for educational purposes only. By downloading, using, copying, replicating, or interacting with this program or its code, you acknowledge and agree to abide by all the Terms, Conditions, Policies, and Licenses mentioned, which are subject to modification without prior notice. The responsibility of staying informed of any changes or updates bears upon yourself. Additionally, kindly adhere to and comply with LinkedIn's terms of service and policies pertaining to web scraping. Usage is at your own risk. The creators and contributors of this program emphasize that they bear no responsibility or liability for any misuse, damages, or legal consequences resulting from its usage.**

[back to top](#linkedin-ai-auto-job-applier-)

---

## 🏛️ Terms and Conditions

- **LinkedIn Policies**: LinkedIn has specific policies regarding web scraping and data collection. Review and comply with these policies before using this program.
- **No Warranties or Guarantees**: This program is provided as-is, without any warranties or guarantees of any kind. Use it at your own risk.
- **Disclaimer of Liability**: The creators and contributors shall not be held responsible or liable for any damages or consequences arising from the use of this program.
- **Use at Your Own Risk**: Ensure your usage complies with applicable laws and regulations.
- **Chrome Driver**: This program uses Chrome Driver. Please review and comply with the [ChromeDriver terms](https://chromedriver.chromium.org/home).

[back to top](#linkedin-ai-auto-job-applier-)

---

## ⚖️ License

Copyright (C) 2026 3COR AI

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

See [AGPLv3 LICENSE](LICENSE) for more info.

[back to top](#linkedin-ai-auto-job-applier-)

---

## 🐧 Socials

- **LinkedIn** : https://www.linkedin.com/company/3cor/
- **Email**    : javadevelopersforum@gmail.com
- **GitHub**   : https://github.com/venkat-singi-reddy

---

#### ℹ️ Version: 26.05.31.1.00

---

[back to top](#linkedin-ai-auto-job-applier-)

