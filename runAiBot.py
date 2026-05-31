'''
Author:     Venkat S
LinkedIn:   https://www.linkedin.com/company/3cor/

Copyright (C) 2026 3COR AI

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/venkat-singi-reddy


version:    26.01.20.5.08

###############################################################################
??  MODIFIED VERSION - DATA CAPTURE MODE ONLY ??

This version has been modified to CAPTURE job details WITHOUT submitting applications.

What it does:
- ? Logs into LinkedIn
- ? Searches for jobs using your search criteria
- ? Extracts comprehensive job details (company, website, category, HR info, etc.)
- ? Saves all data to CSV file
- ? DOES NOT submit job applications

To enable actual job applications:
- Search for "COMMENTED OUT:" in the apply_to_jobs() function
- Follow the instructions to uncomment the application logic
- Change "if False and easy_apply_button_found:" to "if easy_apply_button_found:"
- Change "elif False:" to "else:" for external applications

CSV Output: all excels/all_applied_applications_history.csv
Contains: Job ID, Title, Company, Company Website, Job Category, Work Location,
          HR Name, HR Link, Number of Applications, etc.
###############################################################################
'''


# Imports
import os
import re
import time
import pyautogui
import signal
import atexit
import sys

from random import choice, shuffle, randint
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, NoSuchWindowException, ElementNotInteractableException, WebDriverException, TimeoutException

from config.personals import *
from config.questions import *
from config.search import *
from config.secrets import use_AI, username, password, ai_provider
from config.settings import *

from modules.open_chrome import *
from modules.helpers import *
from modules.clickers_and_finders import *
from modules.validator import validate_config

# -- MongoDB (optional) ------------------------------------------------------
try:
    from config.settings import use_mongodb, mongodb_uri, mongodb_database
except ImportError:
    use_mongodb = False
    mongodb_uri = ""
    mongodb_database = ""

mongo_db = None   # initialised in main() when use_mongodb=True

if use_AI:
    from modules.ai.openaiConnections import ai_create_openai_client, ai_extract_skills, ai_answer_question, ai_close_openai_client
    from modules.ai.deepseekConnections import deepseek_create_client, deepseek_extract_skills, deepseek_answer_question
    from modules.ai.geminiConnections import gemini_create_client, gemini_extract_skills, gemini_answer_question

from typing import Literal


pyautogui.FAILSAFE = False
# if use_resume_generator:    from resume_generator import is_logged_in_GPT, login_GPT, open_resume_chat, create_custom_resume


# -- Graceful shutdown — browser + MongoDB close on ANY exit --------------------
def _graceful_shutdown() -> None:
    """
    Called by atexit and OS signal handlers.
    Ensures the Chrome browser and MongoDB connection are always closed,
    even when the process is killed via terminal close, SIGTERM, or Ctrl+Break.
    """
    try:
        if driver:
            driver.quit()
            print("\n[Shutdown] Browser closed.")
    except Exception:
        pass
    try:
        if use_mongodb and mongo_db is not None:
            from modules.db import close_db
            close_db()
            print("[Shutdown] MongoDB connection closed.")
    except Exception:
        pass


def _signal_handler(sig, frame) -> None:
    """Translate OS signals into a clean SystemExit so atexit handlers run."""
    sig_names = {2: "SIGINT/Ctrl+C", 15: "SIGTERM", 21: "SIGBREAK/Ctrl+Break"}
    print(f"\n[Shutdown] Signal {sig_names.get(sig, sig)} received — shutting down gracefully...")
    sys.exit(0)   # triggers atexit


# Register atexit — runs on normal exit, sys.exit(), and unhandled exceptions
atexit.register(_graceful_shutdown)

# Register signal handlers — covers terminal close, taskkill, Ctrl+Break
signal.signal(signal.SIGTERM, _signal_handler)   # taskkill / systemd stop
try:
    signal.signal(signal.SIGBREAK, _signal_handler)  # Ctrl+Break (Windows only)
except (AttributeError, OSError):
    pass  # SIGBREAK not available on Linux/macOS
# -------------------------------------------------------------------------------


#< Global Variables and logics

if run_in_background == True:
    pause_at_failed_question = False
    pause_before_submit = False
    run_non_stop = False

first_name = first_name.strip()
middle_name = middle_name.strip()
last_name = last_name.strip()
full_name = first_name + " " + middle_name + " " + last_name if middle_name else first_name + " " + last_name

useNewResume = True
randomly_answered_questions = set()

tabs_count = 1
easy_applied_count = 0
external_jobs_count = 0
failed_count = 0
skip_count = 0
dailyEasyApplyLimitReached = False
all_pages_exhausted = False   # set True when every search term reaches its last page naturally

re_experience = re.compile(r'[(]?\s*(\d+)\s*[)]?\s*[-to]*\s*\d*[+]*\s*year[s]?', re.IGNORECASE)

desired_salary_lakhs = str(round(desired_salary / 100000, 2))
desired_salary_monthly = str(round(desired_salary/12, 2))
desired_salary = str(desired_salary)

current_ctc_lakhs = str(round(current_ctc / 100000, 2))
current_ctc_monthly = str(round(current_ctc/12, 2))
current_ctc = str(current_ctc)

notice_period_months = str(notice_period//30)
notice_period_weeks = str(notice_period//7)
notice_period = str(notice_period)

aiClient = None
about_company_for_ai = None # TODO extract about company for AI

#>


#< Login Functions
def is_logged_in_LN() -> bool:
    '''
    Returns True if the browser is currently on an authenticated LinkedIn page.
    Checks URL first (fast path), then falls back to DOM sign-in element detection.
    '''
    url = driver.current_url
    # Fast reject — clearly on login / checkpoint page
    if 'linkedin.com/login' in url:      return False
    if 'linkedin.com/checkpoint/lg' in url: return False
    # Fast accept — on any authenticated LinkedIn page
    if 'linkedin.com/feed'       in url: return True
    if 'linkedin.com/jobs'       in url: return True
    if 'linkedin.com/mynetwork'  in url: return True
    if 'linkedin.com/in/'        in url: return True
    if 'linkedin.com/messaging'  in url: return True
    if 'linkedin.com/notifications' in url: return True
    # DOM heuristic for any other linkedin.com page
    if try_linkText(driver, "Sign in"):  return False
    if try_xp(driver, '//button[@type="submit" and contains(text(), "Sign in")]'): return False
    if try_linkText(driver, "Join now"): return False
    print_lg("Didn't find Sign in link, so assuming user is logged in!")
    return True


def _js_set_input_value(driver, element, value: str) -> None:
    '''
    Sets an input field value in a way that React-controlled inputs recognise.
    Plain "element.value = x" bypasses React's synthetic event system — the form
    sees an empty field.  Using the native HTMLInputElement.prototype value setter
    (the same path React itself monitors) + dispatching a bubbling 'input' event
    makes React update its internal state correctly.
    '''
    driver.execute_script(
        """
        var nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        nativeSetter.call(arguments[0], arguments[1]);
        arguments[0].dispatchEvent(new Event('input',  {bubbles:true}));
        arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
        """,
        element, value
    )


def login_LN() -> None:
    '''
    Function to login for LinkedIn.
    * Fills username + password from secrets.py and submits
    * Waits up to 60 s for the post-login redirect (handles slow networks)
    * Detects 2FA / security challenge pages and waits up to 120 s for manual completion
    * Falls back to manual login prompt if credentials are not configured
    '''
    print_lg("Navigating to LinkedIn login page...")
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)  # Wait for page to settle + any JS redirects

    current = driver.current_url
    print_lg(f"[login] Current URL after navigating to /login: {current}")

    # Dismiss common cookie/consent banners (run before checking URL so modals are gone)
    for consent_xpath in [
        '//button[contains(.,"Accept all")]',
        '//button[contains(.,"Accept")]',
        '//button[contains(.,"Reject all")]',
        '//button[@data-test-id="cookie-policy-manage-btn"]',
        '//button[contains(@class,"artdeco-global-alert__action")]',
    ]:
        try:
            btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, consent_xpath)))
            if btn.is_displayed():
                btn.click()
                time.sleep(1)
                break
        except Exception:
            pass

    current = driver.current_url
    print_lg(f"[login] URL after consent check: {current}")

    # Already on an authenticated page ? done
    if is_logged_in_LN():
        print_lg(f"Already logged in — URL: {current}")
        return

    # Checkpoint / challenge page appeared without submitting credentials — let user solve it
    if 'checkpoint' in current or 'challenge' in current:
        print_lg("Security challenge detected before login — please complete it in the browser...")
        try:
            WebDriverWait(driver, 180).until(
                lambda d: 'checkpoint' not in d.current_url and 'challenge' not in d.current_url
            )
            print_lg(f"[login] Challenge cleared — URL: {driver.current_url}")
            if is_logged_in_LN():
                return
        except Exception:
            pass

    # No credentials configured ? ask for manual login
    if username == "username@example.com" and password == "example_password":
        pyautogui.alert(
            "Username and password are not set in secrets.py.\nPlease log in manually!",
            "Login Manually", "Okay")
        print_lg("Credentials not configured — please login manually!")
        manual_login_retry(is_logged_in_LN, 2)
        return

    # -- Attempt to find and fill the login form -----------------------------
    # LinkedIn (May 2026) uses DYNAMIC IDs (e.g. ":R3jvt8t766ab9j6:") — stable
    # selectors are type/autocomplete attributes only.
    #   Email  : type="email"     autocomplete="username webauthn"
    #   Password: type="password"  autocomplete="current-password"
    #   Button : type="button"    text "Sign in" inside nested <span> elements
    login_submitted = False
    try:
        # -- Username / email field -------------------------------------------
        print_lg("[login] Waiting for username/email field...")
        username_field = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH,
                '//input[@type="email" and contains(@autocomplete,"username")]'))
        )
        print_lg("[login] Found username/email field — filling via JS (React-safe)...")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", username_field)
        driver.execute_script("arguments[0].focus();", username_field)
        time.sleep(0.3)
        _js_set_input_value(driver, username_field, username)
        # Confirm value stuck; retry with send_keys if not
        if username_field.get_attribute("value") != username:
            username_field.send_keys(username)
        print_lg(f"[login] Email field value: {username_field.get_attribute('value')}")
        time.sleep(0.3)

        # -- Password field ---------------------------------------------------
        print_lg("[login] Waiting for password field...")
        password_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH,
                '//input[@type="password" and @autocomplete="current-password"]'))
        )
        print_lg("[login] Found password field — filling via JS (React-safe)...")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", password_field)
        driver.execute_script("arguments[0].focus();", password_field)
        time.sleep(0.3)
        _js_set_input_value(driver, password_field, password)
        if password_field.get_attribute("value") != password:
            password_field.send_keys(password)
        print_lg("[login] Password field filled.")
        time.sleep(0.3)

        print_lg("[login] Credentials filled — attempting to submit...")

        # -- Sign In button ---------------------------------------------------
        # LinkedIn button: type="button" (NOT submit), text "Sign in" inside
        # nested <span><span>Sign in</span></span>. No stable aria-label or class.
        submit_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH,
                '//button[.//span[normalize-space(text())="Sign in"]]'))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", submit_btn)
        time.sleep(0.3)
        # Use JS click to bypass any React portal overlay
        driver.execute_script("arguments[0].click();", submit_btn)
        login_submitted = True
        print_lg("[login] Sign In button clicked.")

    except Exception as e1:
        print_lg(f"[login] Auto-fill login failed: {e1}")
        # Last resort: submit the form via ENTER key on password field
        try:
            pf = driver.find_element(By.XPATH,
                '//input[@type="password" and @autocomplete="current-password"]')
            from selenium.webdriver.common.keys import Keys as _Keys
            pf.send_keys(_Keys.RETURN)
            login_submitted = True
            print_lg("[login] Submitted via ENTER key fallback.")
        except Exception:
            pass  # fall through to manual login below

    # -- Wait for post-login redirect -----------------------------------------
    if login_submitted:
        try:
            print_lg(f"[login] Waiting up to 60 s for redirect away from login page (current: {driver.current_url})...")
            WebDriverWait(driver, 60).until(
                lambda d: 'linkedin.com/login' not in d.current_url
                          and 'linkedin.com/uas/login' not in d.current_url
            )
            print_lg(f"[login] Redirected — URL: {driver.current_url}")

            # Handle 2FA / security challenges after credential submission
            if 'checkpoint' in driver.current_url or 'challenge' in driver.current_url:
                print_lg("2FA / security challenge detected — please complete it in the browser (up to 3 min)...")
                WebDriverWait(driver, 180).until(
                    lambda d: 'checkpoint' not in d.current_url and 'challenge' not in d.current_url
                )
                print_lg(f"[login] Challenge cleared — URL: {driver.current_url}")

            if is_logged_in_LN():
                print_lg(f"Login successful! URL: {driver.current_url}")
                return
            # Redirect happened but not to an authenticated page — fall through
            print_lg(f"[login] Redirected but not authenticated — URL: {driver.current_url}")
        except Exception:
            print_lg(f"[login] Login attempt failed — URL at timeout: {driver.current_url}")

    # -- Auto-login failed or timed out — wait for the user to log in manually -
    print_lg("Couldn't log in automatically — please log in manually in the browser, then confirm.")
    manual_login_retry(is_logged_in_LN, 2)



def get_applied_job_ids() -> set[str]:
    '''
    Initialises the in-session "already seen" cache.

    MongoDB mode (required):
      ? Always returns an EMPTY set.
        Per-job existence is checked live via is_already_seen() / check_and_touch_job().

    Returns a set of Job ID strings (always empty — live checks handle deduplication).
    '''
    if mongo_db is not None:
        print_lg("MongoDB mode — job deduplication uses live per-job queries (no pre-load).")
    else:
        print_lg("?? MongoDB connection is unavailable — starting with empty job cache.")
    return set()   # live checks handled by is_already_seen()


def is_already_seen(job_id: str, applied_jobs: set,
                    title: str = '', company: str = '',
                    work_location: str = '', work_style: str = '',
                    job_link: str = '', external_job_link: str = '') -> bool:
    '''
    Returns True if the job has been seen before (in any previous run).
    Performs a live MongoDB check: upserts available job fields and updates
    last_seen + visits_count when the job is found.
    '''
    already_cached = job_id in applied_jobs
    # Always touch DB when external_job_link is available so URL stays current;
    # skip DB round-trip only when there is nothing new to store AND job is cached.
    if mongo_db is not None and (not already_cached or external_job_link):
        try:
            from modules.db import check_and_touch_job
            partial_doc = {
                "job_id":            job_id,
                "title":             title,
                "company":           company,
                "work_location":     work_location,
                "work_style":        work_style,
                "job_link":          job_link or f"https://www.linkedin.com/jobs/view/{job_id}",
                "external_job_link": external_job_link,
            }
            found = check_and_touch_job(mongo_db, job_id, partial_doc)
            if found:
                applied_jobs.add(job_id)
                if not already_cached:
                    print_lg(f"  [MongoDB] Job {job_id} already in 'linkedin-jobs' — updated last_seen & details, skipping.")
                return True
        except Exception as e:
            print_lg(f"?? MongoDB is_already_seen check failed for '{job_id}': {e}")
    if already_cached:
        return True
    return False



def set_search_location() -> None:
    '''
    Function to set search location
    '''
    if search_location.strip():
        try:
            print_lg(f'Setting search location as: "{search_location.strip()}"')
            search_location_ele = try_xp(driver, ".//input[@aria-label='City, state, or zip code'and not(@disabled)]", False)

            if search_location_ele:
                # Successfully found the search location input
                text_input(actions, search_location_ele, search_location, "Search Location")
                print_lg(f"? Search location set to: {search_location.strip()}")
            else:
                # Element not found, try alternative method
                print_lg("Search location input not found, trying alternative method...")
                try:
                    # Try clicking on the label first
                    try_xp(driver, ".//label[@class='jobs-search-box__input-icon jobs-search-box__keywords-label']")
                    actions.send_keys(Keys.TAB, Keys.TAB).perform()
                    buffer(1)
                    actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
                    actions.send_keys(search_location.strip()).perform()
                    sleep(2)
                    actions.send_keys(Keys.ENTER).perform()
                    print_lg(f"? Search location set using alternative method: {search_location.strip()}")
                except Exception as alt_error:
                    print_lg(f"Alternative method also failed: {str(alt_error)[:100]}")
                    print_lg("Continuing without setting search location - will use LinkedIn default")

        except ElementNotInteractableException as e:
            print_lg(f"Search location element not interactable: {str(e)[:100]}")
            print_lg("Trying alternative input method...")
            try:
                try_xp(driver, ".//label[@class='jobs-search-box__input-icon jobs-search-box__keywords-label']")
                actions.send_keys(Keys.TAB, Keys.TAB).perform()
                buffer(1)
                actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
                actions.send_keys(search_location.strip()).perform()
                sleep(2)
                actions.send_keys(Keys.ENTER).perform()
                print_lg(f"? Search location set using keyboard method: {search_location.strip()}")
            except Exception as kb_error:
                print_lg(f"Keyboard method failed: {str(kb_error)[:100]}")
                print_lg("Continuing without setting search location")
            finally:
                # Try to close any open dialogs
                try:
                    try_xp(driver, ".//button[@aria-label='Cancel']")
                except:
                    pass

        except Exception as e:
            print_lg(f"Failed to set search location: {str(e)[:100]}")
            print_lg("Continuing with default location (or previously set location)")
            # Try to close any open dialogs
            try:
                try_xp(driver, ".//button[@aria-label='Cancel']")
            except:
                pass
    else:
        print_lg("No search location configured, using LinkedIn default")


def apply_filters() -> None:
    '''
    Function to apply job search filters
    '''
    set_search_location()

    try:
        # Set appropriate wait time between filter sections
        # Higher click_gap = more time needed for elements to load
        recommended_wait = max(1, click_gap // 2)  # Minimum 1 second, scales with click_gap

        # Click "All filters" button and wait for modal to load
        print_lg("Opening filter modal...")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space()="All filters"]'))).click()
            buffer(2)  # Wait for filter modal to fully load
            print_lg("Filter modal opened, applying filters...")
        except Exception as modal_error:
            print_lg(f"Failed to open filter modal: {str(modal_error)[:100]}")
            print_lg("Continuing with existing filters or no filters...")
            return  # Exit function if we can't open the filter modal

        # Apply sort_by filter if configured
        if sort_by and sort_by.strip():
            wait_span_click(driver, sort_by)
            print_lg(f"Sort by: {sort_by}")
        else:
            print_lg("No sort_by configured, skipping...")

        # Apply date_posted filter if configured
        if date_posted and date_posted.strip():
            wait_span_click(driver, date_posted)
            print_lg(f"Date posted: {date_posted}")
        else:
            print_lg("No date_posted configured, skipping...")

        buffer(recommended_wait)

        # Experience level and companies filters
        multi_sel_noWait(driver, experience_level)
        multi_sel_noWait(driver, companies, actions)
        if experience_level or companies:
            buffer(recommended_wait)
            print_lg(f"Applied {len(experience_level) + len(companies)} experience/company filters")

        # Job type and work style filters
        multi_sel_noWait(driver, job_type)
        multi_sel_noWait(driver, on_site)
        if job_type or on_site:
            buffer(recommended_wait)
            print_lg(f"Applied {len(job_type) + len(on_site)} job type/work style filters")


        # Location and industry filters
        multi_sel_noWait(driver, location)
        multi_sel_noWait(driver, industry)
        if location or industry:
            buffer(recommended_wait)
            print_lg(f"Applied {len(location) + len(industry)} location/industry filters")

        # Job function and titles filters
        multi_sel_noWait(driver, job_function)
        multi_sel_noWait(driver, job_titles)
        if job_function or job_titles:
            buffer(recommended_wait)
            print_lg(f"Applied {len(job_function) + len(job_titles)} job function/title filters")

        # Boolean filters
        if under_10_applicants:
            boolean_button_click(driver, actions, "Under 10 applicants")
            buffer(1)
        if in_your_network:
            boolean_button_click(driver, actions, "In your network")
            buffer(1)
        if fair_chance_employer:
            boolean_button_click(driver, actions, "Fair Chance Employer")
            buffer(1)

        # Apply salary filter if configured
        if salary and salary.strip():
            wait_span_click(driver, salary)
            print_lg(f"Salary filter: {salary}")
        else:
            print_lg("No salary filter configured, skipping...")

        buffer(recommended_wait)
        
        # Benefits and commitments filters
        multi_sel_noWait(driver, benefits)
        multi_sel_noWait(driver, commitments)
        if benefits or commitments:
            buffer(recommended_wait)
            print_lg(f"Applied {len(benefits) + len(commitments)} benefits/commitment filters")

        # Click "Show results" button
        print_lg("All filters applied, clicking 'Show results'...")
        buffer(1)  # Wait before clicking show results
        show_results_button: WebElement = driver.find_element(By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "apply current filters to show")]')
        show_results_button.click()


        # Optional manual verification of filters (disabled in continuous mode)
        # Uncomment below to enable manual filter verification before each search
        # global pause_after_filters
        # if pause_after_filters:
        #     print_lg("PAUSED: Please verify filters are correct")
        #     pyautogui.confirm("These are your configured search results and filter...", ...)
        #     pause_after_filters = False

    except Exception as e:
        print_lg("="*80)
        print_lg("?? WARNING: Filter application encountered an error")
        print_lg("="*80)
        print_lg(f"Error details: {str(e)}")
        print_lg(f"Error type: {type(e).__name__}")
        print_lg("The bot will continue with existing/default filters")
        print_lg("If you see repeated filter errors, check your config/search.py settings")
        print_lg("="*80)
        # Continue without filters - don't crash the bot



def get_page_info() -> tuple[WebElement | None, int | None]:
    '''
    Function to get pagination element and current page number
    '''
    try:
        pagination_element = try_find_by_classes(driver, ["jobs-search-pagination__pages", "artdeco-pagination", "artdeco-pagination__pages"])
        scroll_to_view(driver, pagination_element)
        current_page = int(pagination_element.find_element(By.XPATH, "//button[contains(@class, 'active')]").text)
    except Exception as e:
        print_lg("Failed to find Pagination element, hence couldn't scroll till end!")
        pagination_element = None
        current_page = None
        print_lg(e)
    return pagination_element, current_page



def get_job_main_details(job: WebElement, blacklisted_companies: set, rejected_jobs: set) -> tuple[str, str, str, str, str, bool]:
    '''
    # Function to get job main details.
    Returns a tuple of (job_id, title, company, work_location, work_style, skip)
    * job_id: Job ID
    * title: Job title
    * company: Company name
    * work_location: Work location of this job
    * work_style: Work style of this job (Remote, On-site, Hybrid)
    * skip: A boolean flag to skip this job
    '''
    skip = False
    job_details_button = job.find_element(By.TAG_NAME, 'a')  # job.find_element(By.CLASS_NAME, "job-card-list__title")  # Problem in India
    scroll_to_view(driver, job_details_button, True)
    job_id = job.get_dom_attribute('data-occludable-job-id')
    title = job_details_button.text
    title = title[:title.find("\n")]
    # company = job.find_element(By.CLASS_NAME, "job-card-container__primary-description").text
    # work_location = job.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
    other_details = job.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
    index = other_details.find(' · ')
    if index == -1:
        company = other_details
        work_location = ""
    else:
        company = other_details[:index]
        work_location = other_details[index+3:]
    work_style = work_location[work_location.rfind('(')+1:work_location.rfind(')')]
    work_location = work_location[:work_location.rfind('(')].strip()
    
    # Skip if previously rejected due to blacklist or already applied
    already_applied = False
    if company in blacklisted_companies:
        print_lg(f'Skipping "{title} | {company}" job (Blacklisted Company). Job ID: {job_id}!')
        skip = True
    elif job_id in rejected_jobs: 
        print_lg(f'Skipping previously rejected "{title} | {company}" job. Job ID: {job_id}!')
        skip = True

    # Check if already applied - capture status without clicking
    try:
        if job.find_element(By.CLASS_NAME, "job-card-container__footer-job-state").text == "Applied":
            already_applied = True
            skip = True
            print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id} - Capturing status without clicking!')
    except: pass

    # Only click the job if we haven't already applied to it
    try:
        if not skip:
            job_details_button.click()
            # Wait for job details panel to load instead of sleeping a fixed duration
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "jobs-unified-top-card__job-title"))
                )
            except Exception:
                pass  # Panel may use a different class; proceed anyway
    except Exception as e:
        print_lg(f'Failed to click "{title} | {company}" job on details button. Job ID: {job_id}!')
        discard_job()
        job_details_button.click()  # To pass the error outside
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobs-unified-top-card__job-title"))
            )
        except Exception:
            pass

    return (job_id,title,company,work_location,work_style,skip)


# Function to check for Blacklisted words in About Company
def extract_company_size(about_company_text: str) -> int | None:
    '''
    Extract "employees on LinkedIn" count from About Company section.
    IMPORTANT: This is NOT the total company size - it's specifically the number of employees with LinkedIn profiles.
    Returns the lower bound of the employee range, or None if not found.

    Examples:
    - "1,001-5,000 employees on LinkedIn" -> returns 1001
    - "10,000+ employees on LinkedIn" -> returns 10000
    - "501-1,000 employees" -> returns 501
    '''
    import re

    # Pattern to match "X-Y employees" or "X+ employees" or "X,XXX-Y,YYY employees"
    # Examples: "1,001-5,000 employees", "10,000+ employees", "51-200 employees on LinkedIn"
    patterns = [
        r'([\d,]+)\s*-\s*([\d,]+)\s+employees',  # Range: 1,001-5,000 employees
        r'([\d,]+)\+\s+employees',                # Plus: 10,000+ employees
        r'([\d,]+)\s+employees',                  # Single: 5000 employees
    ]

    for pattern in patterns:
        match = re.search(pattern, about_company_text, re.IGNORECASE)
        if match:
            # Get the first number (lower bound of range or the single number)
            size_str = match.group(1).replace(',', '')
            try:
                return int(size_str)
            except ValueError:
                continue

    return None


def extract_additional_job_details() -> tuple[str, str, str, str]:
    '''
    Extract additional job details: company website, job category, number of
    applications, and LinkedIn company_id (slug from the company URL).
    Returns: (company_website, job_category, num_applications, company_id)
    '''
    company_website = "Unknown"
    job_category = "Unknown"
    num_applications = "Unknown"
    company_id = "Unknown"

    try:
        # Extract company website AND company_id from About Company section
        try:
            about_company_element = find_by_class(driver, "jobs-company__box", 2)
            company_links = about_company_element.find_elements(By.TAG_NAME, "a")
            for link in company_links:
                href = link.get_attribute("href")
                if href:
                    # Extract company_id (slug) from LinkedIn company URLs
                    slug_match = re.search(r'linkedin\.com/company/([^/?#]+)', href)
                    if slug_match and company_id == "Unknown":
                        company_id = slug_match.group(1).strip('/')
                    # Pick first non-LinkedIn link as company website
                    if "linkedin.com" not in href and href.startswith("http") and company_website == "Unknown":
                        company_website = href
        except Exception:
            print_lg("Failed to extract company website / company_id")

        # Extract job category/industry
        try:
            job_details = driver.find_elements(By.CLASS_NAME, "job-details-jobs-unified-top-card__job-insight")
            for detail in job_details:
                text = detail.text
                if text and "·" not in text and len(text) > 3:
                    job_category = text
                    break
        except Exception:
            print_lg("Failed to extract job category")

        # Extract number of applications
        try:
            insights = driver.find_elements(By.CLASS_NAME, "job-details-jobs-unified-top-card__job-insight")
            for insight in insights:
                text = insight.text
                if "applicant" in text.lower():
                    num_applications = text
                    break
        except Exception:
            print_lg("Failed to extract number of applications")

    except Exception as e:
        print_lg("Error in extract_additional_job_details:", e)

    return (company_website, job_category, num_applications, company_id)


def check_blacklist(rejected_jobs: set, job_id: str, company: str, blacklisted_companies: set) -> tuple[set, set, WebElement] | ValueError:
    jobs_top_card = try_find_by_classes(driver, ["job-details-jobs-unified-top-card__primary-description-container","job-details-jobs-unified-top-card__primary-description","jobs-unified-top-card__primary-description","jobs-details__main-content"])
    about_company_org = find_by_class(driver, "jobs-company__box")
    scroll_to_view(driver, about_company_org)
    about_company_org = about_company_org.text
    about_company = about_company_org.lower()

    # Check company size if minimum_company_size filter is enabled
    if minimum_company_size > 0:
        company_size = extract_company_size(about_company_org)
        if company_size is not None:
            if company_size < minimum_company_size:
                rejected_jobs.add(job_id)
                blacklisted_companies.add(company)
                raise ValueError(
                    f"Company too small: {company_size} LinkedIn employees (minimum: {minimum_company_size})\n"
                    f"Company: {company}\nAbout: {about_company_org[:300]}"
                )
        else:
            print_lg(f'Warning: Could not extract LinkedIn employee count for "{company}". Proceeding with application.')

    skip_checking = False
    for word in about_company_good_words:
        if word.lower() in about_company:
            print_lg(f'Found the word "{word}". So, skipped checking for blacklist words.')
            skip_checking = True
            break
    if not skip_checking:
        for word in about_company_bad_words: 
            if word.lower() in about_company: 
                rejected_jobs.add(job_id)
                blacklisted_companies.add(company)
                raise ValueError(
                    f"Blacklisted word in About Company: \"{word}\"\n"
                    f"Company: {company}\nAbout: {about_company_org[:300]}"
                )
    buffer(0)  # no-op — was buffer(click_gap); now using event-driven waits
    scroll_to_view(driver, jobs_top_card)
    return rejected_jobs, blacklisted_companies, jobs_top_card



# Function to extract years of experience required from About Job
def extract_years_of_experience(text: str) -> int:
    # Extract all patterns like '10+ years', '5 years', '3-5 years', etc.
    matches = re.findall(re_experience, text)
    if len(matches) == 0: 
        print_lg(f'\n{text}\n\nCouldn\'t find experience requirement in About the Job!')
        return 0
    return max([int(match) for match in matches if int(match) <= 12])



def get_job_description(
) -> tuple[
    str | Literal['Unknown'],
    int | Literal['Unknown'],
    bool,
    str | None,
    str | None
    ]:
    '''
    # Job Description
    Function to extract job description from About the Job.
    ### Returns:
    - `jobDescription: str | 'Unknown'`
    - `experience_required: int | 'Unknown'`
    - `skip: bool`
    - `skipReason: str | None`
    - `skipMessage: str | None`
    '''
    try:
        jobDescription = "Unknown"
        experience_required = "Unknown"
        found_masters = 0
        jobDescription = find_by_class(driver, "jobs-box__html-content").text
        jobDescriptionLow = jobDescription.lower()
        skip = False
        skipReason = None
        skipMessage = None
        for word in bad_words:
            if word.lower() in jobDescriptionLow:
                skipMessage = f'\n{jobDescription}\n\nContains bad word "{word}". Skipping this job!\n'
                skipReason = "Found a Bad Word in About Job"
                skip = True
                break
        if not skip and security_clearance == False and ('polygraph' in jobDescriptionLow or 'clearance' in jobDescriptionLow or 'secret' in jobDescriptionLow):
            skipMessage = f'\n{jobDescription}\n\nFound "Clearance" or "Polygraph". Skipping this job!\n'
            skipReason = "Asking for Security clearance"
            skip = True
        if not skip:
            if did_masters and 'master' in jobDescriptionLow:
                print_lg(f'Found the word "master" in \n{jobDescription}')
                found_masters = 2
            experience_required = extract_years_of_experience(jobDescription)
            if current_experience > -1 and experience_required > current_experience + found_masters:
                skipMessage = f'\n{jobDescription}\n\nExperience required {experience_required} > Current Experience {current_experience + found_masters}. Skipping this job!\n'
                skipReason = "Required experience is high"
                skip = True
    except Exception as e:
        if jobDescription == "Unknown":    print_lg("Unable to extract job description!")
        else:
            experience_required = "Error in extraction"
            print_lg("Unable to extract years of experience required!")
            # print_lg(e)
    finally:
        return jobDescription, experience_required, skip, skipReason, skipMessage
        


# Function to upload resume
def upload_resume(modal: WebElement, resume: str) -> tuple[bool, str]:
    try:
        modal.find_element(By.NAME, "file").send_keys(os.path.abspath(resume))
        return True, os.path.basename(default_resume_path)
    except: return False, "Previous resume"

# Function to answer common questions for Easy Apply
def answer_common_questions(label: str, answer: str) -> str:
    if 'sponsorship' in label or 'visa' in label: answer = require_visa
    return answer


# Helper function to check if field is required
def is_field_required(Question: WebElement) -> bool:
    '''
    Check if a form field is required/mandatory
    '''
    try:
        # Check for required attribute
        required_input = Question.find_element(By.XPATH, ".//*[@required or @aria-required='true']")
        if required_input:
            return True
    except:
        pass

    try:
        # Check for asterisk (*) indicating required field
        label_text = Question.find_element(By.TAG_NAME, "label").text
        if '*' in label_text or '(required)' in label_text.lower():
            return True
    except:
        pass

    return False


# Helper function to get select options
def get_select_options(select: Select) -> str:
    '''
    Get available options from a select dropdown as a comma-separated string
    '''
    try:
        options = [option.text for option in select.options if option.text.strip() and option.text != "Select an option"]
        return ", ".join(options[:10])  # Limit to first 10 options
    except:
        return "Unknown options"


# Function to answer the questions for Easy Apply
def answer_questions(modal: WebElement, questions_list: set, work_location: str, job_description: str | None = None ) -> tuple[set, list[dict]]:
    '''
    Answers questions in the Easy Apply form.
    Returns: (questions_list, mandatory_fields_not_filled)
    - questions_list: Set of answered questions
    - mandatory_fields_not_filled: List of dicts with field info that couldn't be filled
    '''
    # Get all questions from the page
    mandatory_fields_not_filled = []

    all_questions = modal.find_elements(By.XPATH, ".//div[@data-test-form-element]")
    # all_questions = modal.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-element")
    # all_list_questions = modal.find_elements(By.XPATH, ".//div[@data-test-text-entity-list-form-component]")
    # all_single_line_questions = modal.find_elements(By.XPATH, ".//div[@data-test-single-line-text-form-component]")
    # all_questions = all_questions + all_list_questions + all_single_line_questions

    for Question in all_questions:
        # Check if it's a select Question
        select = try_xp(Question, ".//select", False)
        if select:
            label_org = "Unknown"
            try:
                label = Question.find_element(By.TAG_NAME, "label")
                label_org = label.find_element(By.TAG_NAME, "span").text
            except: pass
            answer = 'Yes'
            label = label_org.lower()
            select = Select(select)
            selected_option = select.first_selected_option.text
            optionsText = []
            options = '"List of phone country codes"'
            if label != "phone country code":
                optionsText = [option.text for option in select.options]
                options = "".join([f' "{option}",' for option in optionsText])
            prev_answer = selected_option
            if overwrite_previous_answers or selected_option == "Select an option":
                if 'email' in label or 'phone' in label: 
                    answer = prev_answer
                elif 'gender' in label or 'sex' in label: 
                    answer = gender_identity
                elif 'disability' in label:
                    answer = disability_status
                elif 'proficiency' in label: 
                    answer = 'Professional'
                # Visa and work authorization
                elif ('sponsorship' in label or ('visa' in label and 'require' in label)) and ('now' in label or 'future' in label):
                    answer = require_visa_sponsorship
                elif 'eligible to work' in label or 'authorized to work' in label or 'work authorization' in label:
                    answer = work_authorization_us
                # Race/Ethnicity
                elif 'race' in label or 'ethnicity' in label:
                    answer = race_ethnicity
                # Veteran status
                elif 'veteran' in label or 'userra' in label or 'uniformed service' in label:
                    answer = protected_veteran_status
                # Relatives employed by company (compliance question)
                elif ('relative' in label or 'family member' in label or 'family employed' in label) and ('employ' in label or 'work' in label):
                    answer = relatives_in_company
                # Privacy policy and terms acknowledgment
                elif ('acknowledge' in label or 'agree' in label or 'consent' in label or 'accept' in label) and ('privacy' in label or 'terms' in label or 'policy' in label or 'notice' in label or 'agreement' in label):
                    answer = acknowledge_privacy_policy
                # Currently work with specific employer - always answer "No"
                # Detects questions like: "Are you currently working with [employer]?" or "Do you currently work with [company]?"
                elif ('currently' in label or 'current' in label) and ('work' in label or 'working' in label or 'employ' in label) and ('with' in label or 'for' in label or 'at' in label):
                    answer = "No"
                    print_lg(f'Detected "currently work with employer" question - answering: No')
                # Relocation
                elif 'relocation' in label or 'relocate' in label:
                    answer = open_to_relocation
                # Notice period / Availability (for dropdown/select questions)
                elif ('notice' in label and 'period' in label) or ('how soon' in label and ('join' in label or 'start' in label)) or ('availability' in label and ('join' in label or 'start' in label)):
                    answer = notice_period_selection
                # Legal work authorization
                elif ('legal' in label or 'legally' in label) and ('authorization' in label or 'authorized' in label) and ('work' in label):
                    answer = legal_work_authorization
                # CS Degree or equivalent
                elif ('cs' in label or 'computer science' in label) and ('degree' in label or 'equivalent' in label):
                    answer = has_cs_degree
                # Hub city / office location preference
                elif ('hub' in label and 'city' in label) or ('working from' in label) or ('office' in label and 'location' in label):
                    answer = preferred_hub_city
                # How did you hear about this job/role - with fallback options
                elif ('hear' in label or 'come across' in label or 'find' in label or 'learn' in label) and ('job' in label or 'position' in label or 'opportunity' in label or 'role' in label or 'us' in label):
                    answer = how_did_you_hear
                # Education handling
                elif 'school' in label or 'university' in label or 'college' in label:
                    answer = school_name
                elif 'degree' in label or 'education level' in label:
                    answer = degree
                elif 'major' in label or 'specialization' in label or 'discipline' in label or 'field of study' in label or 'area of study' in label:
                    answer = specialization
                # Location handling
                elif any(loc_word in label for loc_word in ['location', 'city', 'state', 'country']):
                    if 'country' in label and 'address' in label:
                        answer = current_country
                    elif 'country' in label:
                        answer = country
                    elif 'state' in label:
                        answer = state
                    elif 'city' in label or 'location' in label:
                        answer = current_city if current_city else work_location
                    else:
                        answer = work_location
                else: 
                    answer = answer_common_questions(label,answer)

                # Special handling for "How did you hear" - try multiple options
                is_referral_question = ('hear' in label or 'come across' in label or 'find' in label or 'learn' in label) and ('job' in label or 'position' in label or 'opportunity' in label or 'role' in label or 'us' in label)

                try:
                    select.select_by_visible_text(answer)
                except NoSuchElementException as e:
                    # Check if this is a gender question for enhanced matching
                    is_gender_question = 'gender' in label or 'sex' in label

                    # For "How did you hear" questions, try multiple matching options with priority order
                    if is_referral_question:
                        # Try configured answer first, then fallback to Social Media and LinkedIn
                        possible_answer_phrases = [how_did_you_hear, "Social Media", "LinkedIn", "LinkedIn Ad", "Social Media (LinkedIn)", "Indeed", "Glassdoor"]
                        print_lg(f'Trying to match "How did you hear" with options: {possible_answer_phrases}')
                    # For gender questions, try multiple variations to ensure "Male" is selected
                    elif is_gender_question and answer.lower() == "male":
                        possible_answer_phrases = [
                            "Male",
                            "male",
                            "MALE",
                            "M",
                            "Man",
                            "man"
                        ]
                        print_lg(f'Gender question detected - trying to select Male with variations: {possible_answer_phrases}')
                    elif answer == 'Decline':
                        possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"]
                    elif 'yes' in answer.lower():
                        possible_answer_phrases = ["Yes", "Agree", "I do", "I have"]
                    elif 'no' in answer.lower():
                        possible_answer_phrases = ["No", "Disagree", "I don't", "I do not"]
                    else:
                        # Try partial matching for any answer
                        possible_answer_phrases = [answer]
                        # Add lowercase and uppercase variants
                        possible_answer_phrases.append(answer.lower())
                        possible_answer_phrases.append(answer.upper())
                        # Try without special characters
                        possible_answer_phrases.append(''.join(c for c in answer if c.isalnum()))
                        # For location fields, add variations (e.g., "Phoenix" from "Phoenix, Arizona")
                        if any(loc_word in label for loc_word in ['location', 'city', 'state']):
                            if ',' in answer:
                                # Add just the city name (before comma)
                                possible_answer_phrases.append(answer.split(',')[0].strip())
                                # Add just the state (after comma)
                                possible_answer_phrases.append(answer.split(',')[1].strip())
                    foundOption = False
                    for phrase in possible_answer_phrases:
                        for option in optionsText:
                            # Check if phrase is in option or option is in phrase (bidirectional matching)
                            if phrase.lower() in option.lower() or option.lower() in phrase.lower():
                                select.select_by_visible_text(option)
                                answer = option
                                foundOption = True
                                break
                        if foundOption:
                            break  # Exit outer loop if option found
                    if not foundOption:
                        #TODO: Use AI to answer the question need to be implemented logic to extract the options for the question
                        print_lg(f'Failed to find an option with text "{answer}" for question labelled "{label_org}", answering randomly!')

                        # Check if this is a required field
                        if is_field_required(Question):
                            print_lg(f'WARNING: Required field "{label_org}" could not be answered properly!')
                            mandatory_fields_not_filled.append({
                                'field_name': label_org,
                                'field_type': 'select',
                                'expected_value': answer,
                                'available_options': get_select_options(select),
                                'action_taken': 'Random selection' if 'hub' not in label.lower() else 'First option selected'
                            })

                        # For hub city preference, choose first option if no match found
                        if ('hub' in label.lower() and 'city' in label.lower()) or ('working from' in label.lower()):
                            select.select_by_index(1)  # First non-default option
                            answer = select.first_selected_option.text
                            print_lg(f'Selected first option for hub city: {answer}')
                        else:
                            select.select_by_index(randint(1, len(select.options)-1))
                            answer = select.first_selected_option.text
                        randomly_answered_questions.add((f'{label_org} [ {options} ]',"select"))
            questions_list.add((f'{label_org} [ {options} ]', answer, "select", prev_answer))
            continue
        
        # Check if it's a radio Question
        radio = try_xp(Question, './/fieldset[@data-test-form-builder-radio-button-form-component="true"]', False)
        if radio:
            prev_answer = None
            label = try_xp(radio, './/span[@data-test-form-builder-radio-button-form-component__title]', False)
            try: label = find_by_class(label, "visually-hidden", 2.0)
            except: pass
            label_org = label.text if label else "Unknown"
            answer = 'Yes'
            label = label_org.lower()

            label_org += ' [ '
            options = radio.find_elements(By.TAG_NAME, 'input')
            options_labels = []
            
            for option in options:
                id = option.get_attribute("id")
                option_label = try_xp(radio, f'.//label[@for="{id}"]', False)
                options_labels.append( f'"{option_label.text if option_label else "Unknown"}"<{option.get_attribute("value")}>' ) # Saving option as "label <value>"
                if option.is_selected(): prev_answer = options_labels[-1]
                label_org += f' {options_labels[-1]},'

            if overwrite_previous_answers or prev_answer is None:
                # Special handling for race/ethnicity - try to match configured value
                if 'race' in label or 'ethnicity' in label:
                    answer = race_ethnicity
                    print_lg(f'Race/Ethnicity detected - trying to select: {answer}')

                    # Try exact match first
                    foundOption = try_xp(radio, f".//label[normalize-space()='{answer}']", False)
                    if foundOption:
                        actions.move_to_element(foundOption).click().perform()
                        print_lg(f'Selected race/ethnicity: {answer}')
                    else:
                        # Try fuzzy matching for common variations
                        possible_answer_phrases = []
                        if 'prefer not' in answer.lower() or 'decline' in answer.lower():
                            possible_answer_phrases = ["Prefer not to answer", "Prefer not to specify", "Prefer not to say", "Decline to self-identify", "Decline", "I prefer not", "I don't wish"]
                        elif 'asian' in answer.lower():
                            possible_answer_phrases = ["Asian", "Asian (Not Hispanic or Latino)", "Asian/Pacific Islander"]
                        else:
                            possible_answer_phrases = [answer]

                        foundOption = False
                        for phrase in possible_answer_phrases:
                            for i, option_label in enumerate(options_labels):
                                if phrase.lower() in option_label.lower():
                                    ele = options[i]
                                    answer = option_label
                                    foundOption = True
                                    actions.move_to_element(ele).click().perform()
                                    print_lg(f'Selected race/ethnicity via fuzzy match: {answer}')
                                    break
                            if foundOption:
                                break

                        # If still not found, select first option as fallback
                        if not foundOption and len(options) > 0:
                            ele = options[0]
                            answer = options_labels[0]
                            print_lg(f'Race/Ethnicity - no match found, selecting first option: {answer}')
                            actions.move_to_element(ele).click().perform()
                            foundOption = True
                # Special handling for gender - just select first available option
                elif 'gender' in label or 'sex' in label:
                    # For gender, simply click the first option to fulfill the requirement
                    if len(options) > 0:
                        ele = options[0]
                        answer = options_labels[0]
                        print_lg(f'Gender detected - selecting first option: {answer}')
                        actions.move_to_element(ele).click().perform()
                        foundOption = True
                    else:
                        foundOption = False
                else:
                    # For other questions, try to match the configured answer
                    if 'citizenship' in label or 'employment eligibility' in label: answer = us_citizenship
                    elif 'veteran' in label or 'protected' in label: answer = veteran_status
                    elif 'disability' in label or 'handicapped' in label:
                        answer = disability_status
                    else: answer = answer_common_questions(label,answer)

                    foundOption = try_xp(radio, f".//label[normalize-space()='{answer}']", False)
                    if foundOption:
                        actions.move_to_element(foundOption).click().perform()
                    else:
                        # Enhanced fuzzy matching for different question types
                        if answer == 'Decline':
                            possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"]
                        else:
                            possible_answer_phrases = [answer]

                        ele = options[0]
                        answer = options_labels[0]
                        for phrase in possible_answer_phrases:
                            for i, option_label in enumerate(options_labels):
                                if phrase in option_label:
                                    foundOption = options[i]
                                    ele = foundOption
                                    answer = f'Decline ({option_label})' if len(possible_answer_phrases) > 1 else option_label
                                    break
                            if foundOption: break
                        # if answer == 'Decline':
                        #     answer = options_labels[0]
                        #     for phrase in ["Prefer not", "not want", "not wish"]:
                        #         foundOption = try_xp(radio, f".//label[normalize-space()='{phrase}']", False)
                        #         if foundOption:
                        #             answer = f'Decline ({phrase})'
                        #             ele = foundOption
                        #             break
                        actions.move_to_element(ele).click().perform()
                        if not foundOption:
                            randomly_answered_questions.add((f'{label_org} ]',"radio"))
                            # Check if this is a required field
                            if is_field_required(Question):
                                print_lg(f'WARNING: Required radio field "{label_org}" could not be answered properly!')
                                mandatory_fields_not_filled.append({
                                    'field_name': label_org,
                                    'field_type': 'radio',
                                    'expected_value': answer,
                                    'available_options': ", ".join(options_labels),
                                    'action_taken': 'Random selection'
                                })
            else: answer = prev_answer
            questions_list.add((label_org+" ]", answer, "radio", prev_answer))
            continue
        
        # Check if it's a text question
        text = try_xp(Question, ".//input[@type='text']", False)
        if text: 
            do_actions = False
            label = try_xp(Question, ".//label[@for]", False)
            try: label = label.find_element(By.CLASS_NAME,'visually-hidden')
            except: pass
            label_org = label.text if label else "Unknown"
            answer = "" # years_of_experience
            label = label_org.lower()

            prev_answer = text.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                if 'experience' in label or 'years' in label: answer = years_of_experience
                elif 'phone' in label or 'mobile' in label: answer = phone_number
                elif 'street' in label: answer = street
                elif 'city' in label or 'location' in label or 'address' in label:
                    answer = current_city if current_city else work_location
                    do_actions = True
                elif 'signature' in label: answer = full_name # 'signature' in label or 'legal name' in label or 'your name' in label or 'full name' in label: answer = full_name     # What if question is 'name of the city or university you attend, name of referral etc?'
                elif 'name' in label:
                    if 'full' in label: answer = full_name
                    elif 'first' in label and 'last' not in label: answer = first_name
                    elif 'middle' in label and 'last' not in label: answer = middle_name
                    elif 'last' in label and 'first' not in label: answer = last_name
                    elif 'employer' in label: answer = recent_employer
                    else: answer = full_name
                elif 'notice' in label:
                    if 'month' in label:
                        answer = notice_period_months
                    elif 'week' in label:
                        answer = notice_period_weeks
                    else: answer = notice_period
                elif 'salary' in label or 'compensation' in label or 'ctc' in label or 'pay' in label: 
                    if 'current' in label or 'present' in label:
                        if 'month' in label:
                            answer = current_ctc_monthly
                        elif 'lakh' in label:
                            answer = current_ctc_lakhs
                        else:
                            answer = current_ctc
                    else:
                        if 'month' in label:
                            answer = desired_salary_monthly
                        elif 'lakh' in label:
                            answer = desired_salary_lakhs
                        else:
                            answer = desired_salary
                elif 'linkedin' in label: answer = linkedIn
                elif 'website' in label or 'blog' in label or 'portfolio' in label or 'link' in label: answer = website
                elif 'scale of 1-10' in label: answer = confidence_level
                elif 'headline' in label: answer = linkedin_headline
                elif ('hear' in label or 'come across' in label or 'find' in label or 'learn' in label) and ('job' in label or 'position' in label or 'opportunity' in label or 'us' in label): answer = referral_source
                # Motivation/Interest questions
                elif ('motivation' in label or 'motivate' in label) and ('exploring' in label or 'new' in label or 'opportunity' in label):
                    answer = primary_motivation
                elif 'why' in label and ('interested' in label or 'applying' in label or 'role' in label or 'position' in label):
                    answer = primary_motivation
                elif ('what attracts' in label or 'what excites' in label) and ('role' in label or 'position' in label):
                    answer = primary_motivation
                # Current employment fields
                elif 'current' in label and ('company' in label or 'employer' in label):
                    answer = current_company
                elif 'current' in label and ('title' in label or 'position' in label or 'role' in label):
                    answer = current_title
                elif 'recent' in label and ('employer' in label or 'company' in label):
                    answer = recent_employer
                # Relatives names field (usually follows relatives question)
                elif ('relative' in label or 'family member' in label) and ('name' in label or 'enter' in label):
                    answer = relatives_names
                # Education fields
                elif 'school' in label or 'university' in label or 'college' in label: answer = school_name
                elif 'degree' in label or 'education level' in label: answer = degree
                elif 'major' in label or 'specialization' in label or 'discipline' in label or 'field of study' in label or 'area of study' in label: answer = specialization
                # Language fluency questions
                elif ('fluent' in label or 'language' in label or 'speak' in label) and ('other' in label or 'besides' in label or 'in addition' in label or 'than english' in label):
                    answer = other_languages_fluent
                # Today's Date text field (some forms use text input instead of date input)
                elif "today's date" in label or ('today' in label and 'date' in label):
                    from datetime import date
                    today_date = date.today().strftime("%m/%d/%Y")  # Format: MM/dd/yyyy
                    answer = today_date
                    print_lg(f"Filling today's date field with: {today_date}")
                # Address fields
                elif 'state' in label or 'province' in label: answer = state
                elif 'zip' in label or 'postal' in label or 'code' in label: answer = zipcode
                elif 'country' in label: answer = country
                else: answer = answer_common_questions(label,answer)
                if answer == "":
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "openai":
                                answer = ai_answer_question(aiClient, label_org, question_type="text", job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                answer = deepseek_answer_question(aiClient, label_org, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                answer = gemini_answer_question(aiClient, label_org, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            else:
                                randomly_answered_questions.add((label_org, "text"))
                                answer = years_of_experience
                            if answer and isinstance(answer, str) and len(answer) > 0:
                                print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                            else:
                                randomly_answered_questions.add((label_org, "text"))
                                answer = years_of_experience
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            randomly_answered_questions.add((label_org, "text"))
                            answer = years_of_experience
                    else:
                        randomly_answered_questions.add((label_org, "text"))
                        answer = years_of_experience

                    # Check if this is a required field and still empty
                    if answer == "" or answer == years_of_experience:
                        if is_field_required(Question):
                            print_lg(f'WARNING: Required text field "{label_org}" could not be filled!')
                            mandatory_fields_not_filled.append({
                                'field_name': label_org,
                                'field_type': 'text',
                                'expected_value': 'Unknown - no config available',
                                'available_options': 'N/A',
                                'action_taken': f'Used default: {answer}'
                            })
                text.clear()
                text.send_keys(answer)
                if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text.get_attribute("value"), "text", prev_answer))
            continue

        # Check if it's a textarea question
        text_area = try_xp(Question, ".//textarea", False)
        if text_area:
            label = try_xp(Question, ".//label[@for]", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = ""
            prev_answer = text_area.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                if 'summary' in label: answer = linkedin_summary
                elif 'cover' in label: answer = cover_letter
                elif 'hiring manager' in label or 'message to' in label: answer = hiring_manager_message
                elif 'reasonable accommodation' in label or 'disability' in label or 'accommodation' in label: answer = reasonable_accommodation
                if answer == "":
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "openai":
                                answer = ai_answer_question(aiClient, label_org, question_type="textarea", job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                answer = deepseek_answer_question(aiClient, label_org, options=None, question_type="textarea", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                answer = gemini_answer_question(aiClient, label_org, options=None, question_type="textarea", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            else:
                                randomly_answered_questions.add((label_org, "textarea"))
                                answer = ""
                            if answer and isinstance(answer, str) and len(answer) > 0:
                                print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                            else:
                                randomly_answered_questions.add((label_org, "textarea"))
                                answer = ""
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            randomly_answered_questions.add((label_org, "textarea"))
                            answer = ""
                    else:
                        randomly_answered_questions.add((label_org, "textarea"))
                        answer = ""
            text_area.clear()
            text_area.send_keys(answer)
            if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text_area.get_attribute("value"), "textarea", prev_answer))
            continue

        # Check if it's a checkbox question
        checkbox = try_xp(Question, ".//input[@type='checkbox']", False)
        if checkbox:
            label = try_xp(Question, ".//span[@class='visually-hidden']", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = try_xp(Question, ".//label[@for]", False)  # Sometimes multiple checkboxes are given for 1 question, Not accounted for that yet
            answer = answer.text if answer else "Unknown"
            prev_answer = checkbox.is_selected()
            checked = prev_answer
            if not prev_answer:
                try:
                    actions.move_to_element(checkbox).click().perform()
                    checked = True
                except Exception as e: 
                    print_lg("Checkbox click failed!", e)
                    pass
            questions_list.add((f'{label} ([X] {answer})', checked, "checkbox", prev_answer))
            continue

        # Check if it's a date input field
        date_input = try_xp(Question, ".//input[@type='date']", False)
        if date_input:
            label = try_xp(Question, ".//label[@for]", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            prev_answer = date_input.get_attribute("value")

            # Check if this is a "Today's Date" field
            if 'today' in label or "today's date" in label or 'current date' in label or 'date' in label:
                from datetime import date
                today_date = date.today().strftime("%Y-%m-%d")  # Format: YYYY-MM-DD for HTML date input

                if not prev_answer or overwrite_previous_answers:
                    try:
                        # Clear and fill the date input
                        date_input.clear()
                        date_input.send_keys(today_date)
                        print_lg(f'Filled date field "{label_org}" with today\'s date: {today_date}')
                        answer = today_date
                    except Exception as e:
                        print_lg(f"Failed to fill date field!", e)
                        answer = prev_answer if prev_answer else "Not filled"
                else:
                    answer = prev_answer

                questions_list.add((label_org, answer, "date", prev_answer))
                continue

    # Select todays date from date picker (for modal/popup date pickers)
    try:
        # Try to find and click "today" button in date picker modals
        today_button = try_xp(driver, "//button[contains(@aria-label, 'This is today') or contains(@aria-label, 'today') or contains(text(), 'Today')]", False)
        if today_button:
            today_button.click()
            print_lg("Clicked 'Today' button in date picker")
    except:
        pass

    # Collect important skills
    # if 'do you have' in label and 'experience' in label and ' in ' in label -> Get word (skill) after ' in ' from label
    # if 'how many years of experience do you have in ' in label -> Get word (skill) after ' in '

    return questions_list, mandatory_fields_not_filled




def external_apply(pagination_element: WebElement, job_id: str, job_link: str, resume: str, date_listed, application_link: str, screenshot_name: str,
                   title: str = 'Unknown', company: str = 'Unknown', work_location: str = 'Unknown', work_style: str = 'Unknown') -> tuple[bool, str, int]:
    '''
    Function to open new tab and save external job application links
    '''
    global tabs_count, dailyEasyApplyLimitReached, skip_count

    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, ".//button[contains(@class,'jobs-apply-button') and contains(@class, 'artdeco-button--3')]"))).click() # './/button[contains(span, "Apply") and not(span[contains(@class, "disabled")])]'
        wait_span_click(driver, "Continue", 1, True, False)
        windows = driver.window_handles
        tabs_count = len(windows)
        driver.switch_to.window(windows[-1])
        try:
            application_link = driver.current_url
        except (ConnectionResetError, WebDriverException) as conn_err:
            print_lg(f"Connection error getting external application URL: {conn_err}")
            application_link = "Connection Error - URL Not Retrieved"
        print_lg('Got the external application link:')
        print_lg(f'{application_link}')
        if close_tabs and driver.current_window_handle != linkedIn_tab: driver.close()
        driver.switch_to.window(linkedIn_tab)
        return False, application_link, tabs_count
    except (ConnectionResetError, WebDriverException) as conn_err:
        print_lg(f"Connection error during external apply: {conn_err}")
        print_lg("Browser connection lost. Exiting external apply...")
        return True, "Connection Lost", tabs_count  # Skip this job
    except Exception as e:
        # print_lg(e)
        print_lg("Failed to apply!")
        failed_job(job_id, job_link, resume, date_listed, "Probably didn't find Apply button or unable to switch tabs.", e, application_link, screenshot_name,
                   title=title, company=company, work_location=work_location, work_style=work_style)
        global failed_count
        failed_count += 1
        return True, application_link, tabs_count


def discard_job() -> None:
    '''
    Closes the LinkedIn Easy Apply modal and confirms the "Discard" action.
    Uses the global `driver` instance.
    '''
    try:
        try_xp(driver, "//button[@aria-label='Dismiss']") or \
        try_xp(driver, "//button[contains(@aria-label,'Dismiss')]")
        buffer(0.5)
        try_xp(driver, "//button[@data-control-name='discard_application_confirm_btn']") or \
        wait_span_click(driver, "Discard", 3)
    except Exception as e:
        print_lg("discard_job: failed to discard modal", e)


def save_job() -> bool:
    '''
    Closes the LinkedIn Easy Apply modal and clicks "Save" to save as draft.
    Returns True if save succeeded, False otherwise.
    Uses the global `driver` instance.
    '''
    try:
        try_xp(driver, "//button[@aria-label='Dismiss']") or \
        try_xp(driver, "//button[contains(@aria-label,'Dismiss')]")
        buffer(0.5)
        result = try_xp(driver, "//button[@data-control-name='save_application_btn']") or \
                 wait_span_click(driver, "Save", 3)
        return bool(result)
    except Exception as e:
        print_lg("save_job: failed to save modal", e)
        return False


def follow_company(modal: WebDriver = driver) -> None:
    '''
    Function to follow or un-follow easy applied companies based om `follow_companies`
    '''
    try:
        follow_checkbox_input = try_xp(modal, ".//input[@id='follow-company-checkbox' and @type='checkbox']", False)
        if follow_checkbox_input and follow_checkbox_input.is_selected() != follow_companies:
            try_xp(modal, ".//label[@for='follow-company-checkbox']")
    except Exception as e:
        print_lg("Failed to update follow companies checkbox!", e)
    


#< Failed attempts and skipped jobs logging
def skipped_job(job_id: str, job_link: str, title: str, company: str,
                work_location: str, work_style: str, resume: str, date_listed,
                skip_reason: str,
                description: str = 'Unknown',
                experience_required = 'Unknown',
                skills = 'Unknown',
                hr_name: str = 'Unknown',
                hr_link: str = 'Unknown',
                company_id: str = 'Unknown',
                company_website: str = 'Unknown',
                job_category: str = 'Unknown',
                num_applications: str = 'Unknown',
                mandatory_field_name: str = "N/A",
                expected_values: str = "N/A",
                screenshot_name: str = "Not Available",
                application_link: str = '',
                reposted: bool = False,
                is_easy_apply: bool = False) -> None:
    '''
    Records a skipped job with full details into the linkedin-jobs collection.
    '''
    if mongo_db is None:
        print_lg(f"?? MongoDB unavailable — skipped job '{title} | {company}' not saved.")
        return
    try:
        from modules.db import upsert_job
        upsert_job(mongo_db, {
            "job_id":               str(job_id),
            "title":                str(title),
            "company":              str(company),
            "company_id":           str(company_id),
            "company_website":      str(company_website),
            "job_category":         str(job_category),
            "work_location":        str(work_location),
            "work_style":           str(work_style),
            "about_job":            str(description),
            "experience_required":  str(experience_required),
            "skills_required":      str(skills),
            "hr_name":              str(hr_name),
            "hr_link":              str(hr_link),
            "num_applications":     str(num_applications),
            "job_link":             str(job_link),
            "external_job_link":    str(application_link) if application_link else '',
            "resume":               str(resume),
            "reposted":             bool(reposted),
            "is_easy_apply":        bool(is_easy_apply),
            "date_posted":          str(date_listed),
            "date_skipped":         datetime.now(),
            "status":               "Skipped",
            "skip_reason":          str(skip_reason),
            "mandatory_field_name": str(mandatory_field_name),
            "expected_values":      str(expected_values),
            "screenshot":           str(screenshot_name),
        })
        print_lg(f"? Skipped job saved to MongoDB: {title} | {company} — Reason: {skip_reason}")
    except Exception as e:
        print_lg(f"?? MongoDB skipped_job failed: {e}")


def failed_job(job_id: str, job_link: str, resume: str, date_listed, error: str, exception: Exception, application_link: str, screenshot_name: str,
               title: str = 'Unknown', company: str = 'Unknown',
               work_location: str = 'Unknown', work_style: str = 'Unknown',
               description: str = 'Unknown', experience_required = 'Unknown',
               skills = 'Unknown', hr_name: str = 'Unknown', hr_link: str = 'Unknown',
               company_id: str = 'Unknown', company_website: str = 'Unknown',
               job_category: str = 'Unknown', num_applications: str = 'Unknown',
               reposted: bool = False, is_easy_apply: bool = False) -> None:
    '''
    Records a failed job attempt with full job details into the linkedin-jobs collection.
    '''
    if mongo_db is None:
        print_lg(f"?? MongoDB unavailable — failed job '{title} | {company}' not saved.")
        return
    try:
        from modules.db import upsert_job
        upsert_job(mongo_db, {
            "job_id":              str(job_id),
            "title":               str(title),
            "company":             str(company),
            "company_id":          str(company_id),
            "company_website":     str(company_website),
            "job_category":        str(job_category),
            "work_location":       str(work_location),
            "work_style":          str(work_style),
            "about_job":           str(description),
            "experience_required": str(experience_required),
            "skills_required":     str(skills),
            "hr_name":             str(hr_name),
            "hr_link":             str(hr_link),
            "num_applications":    str(num_applications),
            "job_link":            str(job_link),
            "external_job_link":   str(application_link),
            "resume":              str(resume),
            "reposted":            bool(reposted),
            "is_easy_apply":       bool(is_easy_apply),
            "date_posted":         str(date_listed),
            "date_tried":          datetime.now(),
            "assumed_reason":      str(error),
            "stack_trace":         str(exception),
            "screenshot":          str(screenshot_name),
            "status":              "Failed",
        })
    except Exception as e:
        print_lg(f"?? MongoDB failed_job failed: {e}")


def screenshot(driver: WebDriver, job_id: str, failedAt: str) -> str:
    '''
    Function to to take screenshot for debugging
    - Returns screenshot name as String
    '''
    screenshot_name = "{} - {} - {}.png".format( job_id, failedAt, str(datetime.now()) )
    path = logs_folder_path+"/screenshots/"+screenshot_name.replace(":",".")
    # special_chars = {'*', '"', '\\', '<', '>', ':', '|', '?'}
    # for char in special_chars:  path = path.replace(char, '-')
    driver.save_screenshot(path.replace("//","/"))
    return screenshot_name
#>



def submitted_jobs(job_id: str, title: str, company: str, work_location: str, work_style: str, description: str, experience_required: int | Literal['Unknown', 'Error in extraction'], 
                   skills: list[str] | Literal['In Development'], hr_name: str | Literal['Unknown'], hr_link: str | Literal['Unknown'], resume: str, 
                   reposted: bool, date_listed: datetime | Literal['Unknown'], date_applied:  datetime | Literal['Pending'], job_link: str, application_link: str, 
                   questions_list: set | None, connect_request: Literal['In Development'], status: str = 'Applied',
                   failure_reason: str = '', mandatory_fields: str = '', screenshot_name: str = '',
                   company_website: str = 'Unknown', job_category: str = 'Unknown', num_applications: str = 'Unknown',
                   company_id: str = 'Unknown', is_easy_apply: bool = False) -> None:
    '''
    Records an applied (or data-captured) job into the linkedin-jobs collection.
    '''
    if mongo_db is None:
        print_lg(f"?? MongoDB unavailable — job '{title} | {company}' not saved.")
        return
    try:
        from modules.db import upsert_job
        upsert_job(mongo_db, {
            "job_id":              str(job_id),
            "title":               str(title),
            "company":             str(company),
            "company_id":          str(company_id),
            "company_website":     str(company_website),
            "job_category":        str(job_category),
            "work_location":       str(work_location),
            "work_style":          str(work_style),
            "about_job":           str(description),
            "experience_required": str(experience_required),
            "skills_required":     str(skills),
            "hr_name":             str(hr_name),
            "hr_link":             str(hr_link),
            "resume":              str(resume),
            "reposted":            bool(reposted),
            "is_easy_apply":       bool(is_easy_apply),
            "date_posted":         str(date_listed),
            "date_applied":        str(date_applied),
            "job_link":            str(job_link),
            "external_job_link":   str(application_link),
            "num_applications":    str(num_applications),
            "questions_found":     str(questions_list),
            "connect_request":     str(connect_request),
            "status":              str(status),
            "failure_reason":      str(failure_reason),
            "mandatory_fields":    str(mandatory_fields),
            "screenshot":          str(screenshot_name),
        })
    except Exception as e:
        print_lg(f"?? MongoDB submitted_jobs failed: {e}")





def _decode_apply_href(href: str) -> str:
    """
    LinkedIn wraps external apply URLs in a safety redirect:
      https://www.linkedin.com/safety/go/?url=<url-encoded-real-url>&urlhash=…

    Extracts and URL-decodes the real company URL from that wrapper.
    If href is not a safety URL it is returned unchanged.
    """
    if not href:
        return ''
    if 'linkedin.com/safety/go' in href:
        try:
            params = parse_qs(urlparse(href).query)
            real = params.get('url', [''])[0]
            decoded = unquote(real)
            if decoded and decoded.startswith('http'):
                print_lg(f"  [_decode_apply_href] Safety URL decoded ? {decoded}")
                return decoded
        except Exception as _de:
            print_lg(f"  [_decode_apply_href] Failed to decode safety URL: {_de}")
    return href



def detect_applied_status(driver_instance) -> bool:
    """
    Return True when LinkedIn's 'Applied' badge/indicator is visible on the
    current job detail page, meaning this job was already applied to.

    Confirmed HTML structures:
      • <div class="artdeco-inline-feedback artdeco-inline-feedback--success">
            <span class="artdeco-inline-feedback__message">Applied 1 week ago</span>
        </div>
      • <a id="jobs-apply-see-application-link" href="/jobs-tracker?stage=applied">
            See application
        </a>
    """
    _applied_xpaths = [
        "//div[contains(@class,'artdeco-inline-feedback--success')]",  # green success badge ?
        "//a[@id='jobs-apply-see-application-link']",                  # "See application" link ?
    ]
    for xp in _applied_xpaths:
        try:
            driver_instance.find_element(By.XPATH, xp)
            print_lg(f"  [detect_applied_status] ? 'Applied' badge found via: {xp}")
            return True
        except NoSuchElementException:
            continue
        except Exception as _e:
            print_lg(f"  [detect_applied_status] ? Error on {xp}: {_e}")
    print_lg("  [detect_applied_status] No 'Applied' badge found")
    return False


#< Main Functions
def apply_to_jobs(search_terms: list[str]) -> None:
    '''
    ?? DATA CAPTURE MODE: Extracts job information WITHOUT applying

    Main function to browse jobs on LinkedIn and capture details

    Process Flow:
    1. Load previously processed job IDs to avoid duplicates
    2. For each search term:
       a. Search for jobs on LinkedIn
       b. Apply configured filters
       c. For each job listing:
          - Extract job details (title, company, location, etc.)
          - Check against blacklist
          - Extract additional details (HR info, description, website, etc.)
          - ? SKIP ACTUAL APPLICATION (currently disabled)
          - ? SAVE job details to CSV
       d. Move to next page until switch_number is reached
    3. Track statistics (jobs captured, skipped counts)

    Args:
        search_terms: List of job search keywords (e.g., ["Python Developer", "Data Scientist"])

    NOTE: To enable actual applications, search for "COMMENTED OUT:" in this file
    '''

    ###########################################################################
    # DATA CAPTURE MODE WARNING
    ###########################################################################
    print_lg("\n" + "="*80)
    print_lg("??  DATA CAPTURE MODE ACTIVE - NO APPLICATIONS WILL BE SUBMITTED ??")
    print_lg("="*80)
    print_lg("The bot will browse jobs and save details to CSV without applying.")
    print_lg("To enable applications, modify the code as indicated in comments.")
    print_lg("="*80 + "\n")
    ###########################################################################

    # ========== INITIALIZATION ==========
    # Load previously applied job IDs to avoid re-applying
    applied_jobs = get_applied_job_ids()

    # Sets to track jobs we've rejected or companies we've blacklisted during this session
    rejected_jobs = set()
    blacklisted_companies = set()

    # Access global variables for statistics and settings
    global current_city, failed_count, skip_count, easy_applied_count, external_jobs_count, tabs_count, pause_before_submit, pause_at_failed_question, useNewResume, all_pages_exhausted
    current_city = current_city.strip()

    # Assume all pages will be exhausted unless a search term is stopped early by switch_number
    all_pages_exhausted = True

    # Randomize search order if configured (helps avoid detection patterns)
    if randomize_search_order:  shuffle(search_terms)

    # ========== MAIN SEARCH LOOP ==========
    # Iterate through each search term (e.g., "Software Engineer", "Java Developer")
    for searchTerm in search_terms:
        # ---------- SEARCH URL CONSTRUCTION ----------
        # Build the LinkedIn job search URL with the current search term
        #search_url = f"https://www.linkedin.com/jobs/search/?keywords={searchTerm}"
        search_url = f"https://www.linkedin.com/jobs/search/?keywords=\"{searchTerm}\""


        # Navigate to the search results page
        driver.get(search_url)
        print_lg("\n________________________________________________________________________________________________________________________\n")
        print_lg(f'\n>>>> Now searching for "{searchTerm}" <<<<\n\n')

        # ---------- APPLY ADDITIONAL FILTERS ----------
        # Apply user-configured filters (location, date posted, experience level, etc.)
        # These are set in config/search.py
        apply_filters()

        current_count = 0
        try:
            while current_count < switch_number:
                # Wait until job listings are loaded
                try:
                    wait.until(EC.presence_of_all_elements_located((By.XPATH, "//li[@data-occludable-job-id]")))
                except Exception as wait_error:
                    print_lg(f"Timeout waiting for job listings to load: {wait_error}")
                    print_lg("This could mean: no jobs found, page loading issue, or network problem")
                    print_lg("Skipping this search term and moving to next...")
                    break  # Break the while loop, move to next search term

                pagination_element, current_page = get_page_info()

                # Find all job listings in current page — wait until at least one appears
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//li[@data-occludable-job-id]"))
                    )
                except Exception:
                    pass  # Proceed even if wait times out; empty-list check below handles it
                job_listings = driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")

                # Check if job listings were actually found
                if not job_listings or len(job_listings) == 0:
                    print_lg("No job listings found on this page. Moving to next search term...")
                    break  # Break the while loop, move to next search term

            
                for job in job_listings:
                    # ---------- KEEP SCREEN AWAKE ----------
                    # Prevent screen timeout during long sessions
                    if keep_screen_awake: pyautogui.press('shiftright')

                    # ---------- CHECK JOB COUNT LIMIT ----------
                    # Stop if we've reached the configured limit for this search term
                    if current_count >= switch_number:
                        print_lg("\n" + "="*80)
                        print_lg(f"REACHED JOB LIMIT FOR THIS SEARCH")
                        print_lg("="*80)
                        print_lg(f"Processed {current_count} jobs (limit: {switch_number})")
                        print_lg("Moving to next search term...")
                        print_lg("="*80 + "\n")
                        all_pages_exhausted = False   # stopped early — pages not fully exhausted
                        break

                    print_lg("\n-@-\n")  # Visual separator in logs

                    # ---------- EXTRACT BASIC JOB DETAILS ----------
                    # Get job ID, title, company, location, work style (remote/hybrid/onsite)
                    # This function also checks if we've already applied or if company is blacklisted
                    try:
                        job_id,title,company,work_location,work_style,skip = get_job_main_details(job, blacklisted_companies, rejected_jobs)
                    except Exception as e:
                        # Could fail if job element is stale or already applied
                        print_lg(f"Failed to get job details (possibly already applied or stale element): {e}")
                        continue

                    # ---------- HANDLE ALREADY APPLIED JOBS ----------
                    # Capture already-applied jobs without clicking on them
                    if skip:
                        # If we've already seen this job in a previous run, just skip silently
                        if is_already_seen(job_id, applied_jobs,
                                           title=title, company=company,
                                           work_location=work_location, work_style=work_style):
                            print_lg(f'Skipping already-seen job ID {job_id} ("{title}" | {company}) — already in history.')
                            continue
                        # First time we see this job marked "Applied" on LinkedIn — record it once
                        recorded = False
                        try:
                            if job.find_element(By.CLASS_NAME, "job-card-container__footer-job-state").text == "Applied":
                                job_link = "https://www.linkedin.com/jobs/view/" + job_id
                                submitted_jobs(
                                    job_id=job_id, title=title, company=company,
                                    work_location=work_location, work_style=work_style,
                                    description="Already Applied - Not captured",
                                    experience_required="Unknown", skills="In Development",
                                    hr_name="Unknown", hr_link="Unknown", resume="N/A",
                                    reposted=False, date_listed="Unknown", date_applied="Pending",
                                    job_link=job_link, application_link="Already Applied",
                                    questions_list=None, connect_request="In Development",
                                    company_website="Unknown", job_category="Unknown", num_applications="Unknown"
                                )
                                applied_jobs.add(job_id)
                                print_lg(f'Recorded already-applied job: "{title} | {company}" (Job ID: {job_id})')
                                current_count += 1
                                recorded = True
                        except:
                            pass  # No footer state — blacklisted / rejected job in listing
                        # Record new blacklisted-company jobs that weren't "Applied" on LinkedIn
                        if not recorded and company in blacklisted_companies:
                            job_link_b = "https://www.linkedin.com/jobs/view/" + job_id
                            skipped_job(job_id, job_link_b, title, company, work_location, work_style,
                                        "N/A", "Unknown",
                                        skip_reason="Blacklisted company (see earlier record for this company)",
                                        application_link=job_link_b,
                                        reposted=False)
                            applied_jobs.add(job_id)
                            skip_count += 1
                            print_lg(f'Recorded blacklisted-company job: "{title} | {company}" (Job ID: {job_id})')
                        continue


                    # ---------- SKIP IF ALREADY SEEN IN ANY PREVIOUS RUN ----------
                    _jlink_touch = f"https://www.linkedin.com/jobs/view/{job_id}"

                    if is_already_seen(job_id, applied_jobs,
                                       title=title, company=company,
                                       work_location=work_location, work_style=work_style,
                                       job_link=_jlink_touch):
                        # Job is already in history. Re-detect apply type and update
                        # is_easy_apply in MongoDB so the flag stays accurate.
                        if use_mongodb and mongo_db is not None:
                            is_easy_apply = False
                            try:
                                driver.find_element(By.XPATH,
                                    "//button[@id='jobs-apply-button-id' and contains(@aria-label,'Easy Apply')]")
                                is_easy_apply = True
                            except NoSuchElementException:
                                print_lg(f"  [easy apply not-detected] No Easy Apply button found for job {job_id} ? is_easy_apply=False")
                            try:
                                from modules.db import update_is_easy_apply
                                update_is_easy_apply(mongo_db, job_id, is_easy_apply)
                                print_lg(f"  ? is_easy_apply updated for job {job_id}: {is_easy_apply}")
                            except Exception as _ue:
                                print_lg(f"  ? Could not update is_easy_apply for {job_id}: {_ue}")
                        print_lg(f'Skipping already-seen job ID {job_id} ("{title}" | {company}) — already in history.')
                        continue

                    # ---------- REDUNDANT APPLIED CHECK (LinkedIn UI) ----------
                    # Only reached for genuinely new job IDs not in our history files
                    try:
                        if find_by_class(driver, "jobs-s-apply__application-link", 2):
                            print_lg(f'LinkedIn shows already applied for "{title} | {company}" (Job ID: {job_id}) — saving as Applied.')
                            _jl = "https://www.linkedin.com/jobs/view/" + job_id
                            submitted_jobs(job_id, title, company, work_location, work_style,
                                           "Unknown", "Unknown", "Unknown", "Unknown", "Unknown",
                                           "Unknown", False, "Unknown", datetime.now(), _jl, _jl,
                                           None, "In Development", status="Applied", is_easy_apply=False)
                            applied_jobs.add(job_id)
                            easy_applied_count += 1
                            continue
                    except Exception as e:
                        print_lg(f'Trying to process "{title} | {company}" job. Job ID: {job_id}')

                    job_link = "https://www.linkedin.com/jobs/view/"+job_id

                    # -- Detect apply button type -------------------------------------------
                    is_easy_apply = False
                    is_already_applied = False

                    # Easy Apply — stable button ID + aria-label check
                    try:
                        _btn = driver.find_element(By.XPATH,
                            "//button[@id='jobs-apply-button-id' and contains(@aria-label,'Easy Apply')]")
                        is_easy_apply = True
                        print_lg(f"  [apply detect] Easy Apply detected ? is_easy_apply=True | aria-label='{_btn.get_attribute('aria-label')}'")
                    except NoSuchElementException:
                        print_lg("  [easy apply not-detected] No Easy Apply button found ? is_easy_apply=False")

                    # Already Applied — success badge
                    try:
                        driver.find_element(By.XPATH,
                            "//div[contains(@class,'artdeco-inline-feedback--success')]")
                        is_already_applied = True
                        print_lg("  [apply detect] Already Applied (success badge)")
                    except NoSuchElementException:
                        pass

                    if not is_already_applied:
                        # Already Applied — see-application link
                        try:
                            driver.find_element(By.XPATH, "//a[@id='jobs-apply-see-application-link']")
                            is_already_applied = True
                            print_lg("  [apply detect] Already Applied (see-application link)")
                        except NoSuchElementException:
                            pass

                    application_link = ''
                    date_applied = "Pending"
                    hr_link = "Unknown"
                    hr_name = "Unknown"
                    connect_request = "In Development" # Still in development
                    date_listed = "Unknown"
                    skills = "Needs an AI" # Still in development
                    resume = "Pending"
                    reposted = False
                    questions_list = None
                    screenshot_name = "Not Available"
                    company_website = "Unknown"
                    job_category = "Unknown"
                    num_applications = "Unknown"
                    company_id = "Unknown"

                    try:
                        rejected_jobs, blacklisted_companies, jobs_top_card = check_blacklist(rejected_jobs,job_id,company,blacklisted_companies)
                        # Extract additional job details after successfully loading job details
                        company_website, job_category, num_applications, company_id = extract_additional_job_details()
                    except ValueError as e:
                        err_msg = str(e).strip()
                        # First line of error is the clean short reason; rest is detail
                        skip_reason = err_msg.split('\n')[0]
                        print_lg(err_msg, 'Skipping this job!\n')
                        skipped_job(job_id, job_link, title, company, work_location, work_style, resume, date_listed,
                                    skip_reason=skip_reason,
                                    description=err_msg,
                                    company_id=company_id, company_website=company_website,
                                    job_category=job_category, num_applications=num_applications,
                                    screenshot_name=screenshot_name,
                                    application_link=application_link,
                                    reposted=reposted,
                                    is_easy_apply=is_easy_apply)
                        applied_jobs.add(job_id)
                        rejected_jobs.add(job_id)
                        skip_count += 1
                        continue
                    except Exception as e:
                        print_lg("Failed to scroll to About Company!")
                        # print_lg(e)



                    # Hiring Manager info
                    try:
                        hr_info_card = WebDriverWait(driver,2).until(EC.presence_of_element_located((By.CLASS_NAME, "hirer-card__hirer-information")))
                        hr_link = hr_info_card.find_element(By.TAG_NAME, "a").get_attribute("href")
                        hr_name = hr_info_card.find_element(By.TAG_NAME, "span").text
                        # if connect_hr:
                        #     driver.switch_to.new_window('tab')
                        #     driver.get(hr_link)
                        #     wait_span_click("More")
                        #     wait_span_click("Connect")
                        #     wait_span_click("Add a note")
                        #     message_box = driver.find_element(By.XPATH, "//textarea")
                        #     message_box.send_keys(connect_request_message)
                        #     if close_tabs: driver.close()
                        #     driver.switch_to.window(linkedIn_tab) 
                        # def message_hr(hr_info_card):
                        #     if not hr_info_card: return False
                        #     hr_info_card.find_element(By.XPATH, ".//span[normalize-space()='Message']").click()
                        #     message_box = driver.find_element(By.XPATH, "//div[@aria-label='Write a message…']")
                        #     message_box.send_keys()
                        #     try_xp(driver, "//button[normalize-space()='Send']")        
                    except Exception as e:
                        print_lg(f'HR info was not given for "{title}" with Job ID: {job_id}!')
                        # print_lg(e)


                    # Calculation of date posted
                    try:
                        # try: time_posted_text = find_by_class(driver, "jobs-unified-top-card__posted-date", 2).text
                        # except: 
                        time_posted_text = jobs_top_card.find_element(By.XPATH, './/span[contains(normalize-space(), " ago")]').text
                        print("Time Posted: " + time_posted_text)
                        if time_posted_text.__contains__("Reposted"):
                            reposted = True
                            time_posted_text = time_posted_text.replace("Reposted", "")


                        date_listed = calculate_date_posted(time_posted_text.strip())
                    except Exception as e:
                        print_lg("Failed to calculate the date posted!",e)


                    description, experience_required, skip, reason, message = get_job_description()
                    if skip:
                        print_lg(message)
                        skipped_job(job_id, job_link, title, company, work_location, work_style, resume, date_listed,
                                    skip_reason=reason,
                                    description=description, experience_required=experience_required,
                                    hr_name=hr_name, hr_link=hr_link,
                                    company_id=company_id, company_website=company_website,
                                    job_category=job_category, num_applications=num_applications,
                                    screenshot_name=screenshot_name,
                                    application_link=application_link,
                                    reposted=reposted,
                                    is_easy_apply=is_easy_apply)
                        applied_jobs.add(job_id)
                        rejected_jobs.add(job_id)
                        skip_count += 1
                        continue

                    
                    if use_AI and description != "Unknown":
                        try:
                            if ai_provider.lower() == "openai":
                                skills = ai_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "deepseek":
                                skills = deepseek_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "gemini":
                                skills = gemini_extract_skills(aiClient, description)
                            else:
                                skills = "In Development"
                            print_lg(f"Extracted skills using {ai_provider} AI")
                        except Exception as e:
                            print_lg("Failed to extract skills:", e)
                            skills = "Error extracting skills"

                    uploaded = False

                    # -- APPLY TYPE DETECTION ----------------------------------------------
                    if is_easy_apply:
                        print_lg(f'  Easy Apply detected for "{title} | {company}" (ID: {job_id}) — is_easy_apply=True')
                        date_applied = "Not Applied - Easy Apply"
                    elif is_already_applied:
                        date_applied = datetime.now()
                        print_lg(f'  Already Applied badge detected for "{title} | {company}" — status=Applied')
                    else:
                        # External apply or no button — check for Applied badge via detect_applied_status
                        if detect_applied_status(driver):
                            date_applied = datetime.now()
                            print_lg(f'  Applied badge confirmed for "{title} | {company}" — status=Applied')
                        else:
                            print_lg(f'  No Easy Apply / badge for "{title} | {company}" — status=New')
                            date_applied = "Not Applied - No Apply Link Found"


                    ###############################################################################
                    # SAVE JOB DETAILS
                    ###############################################################################

                    # date_applied is already set by the detection block above — no need for
                    # a "Pending" fallback since we never leave it unset anymore.

                    # Determine status for MongoDB:
                    #   'Applied' — Applied badge detected (date_applied is datetime)
                    #   'New'     — Easy Apply / External / no button found
                    if isinstance(date_applied, datetime):
                        job_status = 'Applied'
                    else:
                        job_status = 'New'

                    # application_link is always '' — no external URL capture
                    application_link = ''

                    # Save all captured job details to CSV/MongoDB
                    submitted_jobs(job_id, title, company, work_location, work_style, description,
                                   experience_required, skills, hr_name, hr_link, resume, reposted,
                                   date_listed, date_applied, job_link, application_link,
                                   questions_list, connect_request,
                                   status=job_status,
                                   company_website=company_website, job_category=job_category,
                                   num_applications=num_applications, company_id=company_id,
                                   is_easy_apply=is_easy_apply)

                    print_lg(f'Job processed: "{title} | {company}" (ID: {job_id}) — applied: {date_applied}')
                    current_count += 1
                    if is_easy_apply:
                        easy_applied_count += 1
                    applied_jobs.add(job_id)



                # Switching to next page
                if pagination_element == None:
                    print_lg("Couldn't find pagination element, probably at the end page of results!")
                    # pages naturally exhausted — all_pages_exhausted stays True
                    break
                try:
                    pagination_element.find_element(By.XPATH, f"//button[@aria-label='Page {current_page+1}']").click()
                    print_lg(f"\n>-> Now on Page {current_page+1} \n")

                    # Wait for page to load
                    buffer(2)


                    # Continue to top of while loop to process jobs on new page
                    print_lg(f"Loading jobs from page {current_page+1}...")
                    continue

                except NoSuchElementException:
                    print_lg(f"\n>-> Didn't find Page {current_page+1}. Probably at the end page of results!\n")
                    print_lg("="*80)
                    print_lg("REACHED END OF SEARCH RESULTS")
                    print_lg("="*80)
                    print_lg(f"Processed all available pages for current search")
                    print_lg(f"Total jobs processed in this search: {current_count}")
                    print_lg("="*80 + "\n")
                    # pages naturally exhausted — all_pages_exhausted stays True
                    break

        except (NoSuchWindowException, WebDriverException) as e:
            print_lg("Browser window closed or session is invalid. Ending application process.")
            print_lg(f"Details: {e}")
            return  # Exit gracefully instead of re-raising
        except ConnectionResetError as e:
            print_lg("Connection to browser was reset by remote host.")
            print_lg(f"Details: {e}")
            print_lg("This usually happens when the browser is closed manually or network issues occur.")
            return  # Exit gracefully
        except KeyboardInterrupt:
            print_lg("\n\nKeyboard interrupt detected (Ctrl+C pressed).")
            print_lg("Terminating job application process gracefully...")
            return  # Exit gracefully
        except Exception as e:
            print_lg("Failed to find Job listings!")
            critical_error_log("In Applier", e)
            try:
                print_lg(driver.page_source, pretty=True)
            except Exception as page_source_error:
                print_lg(f"Failed to get page source, browser might have crashed. {page_source_error}")
            # print_lg(e)

        
def run(total_runs: int) -> int:
    if dailyEasyApplyLimitReached:
        print_lg("Daily Easy Apply limit already reached, skipping this run.")
        return total_runs
    print_lg("\n########################################################################################################################\n")
    print_lg(f"Date and Time: {datetime.now()}")
    print_lg(f"Cycle number: {total_runs}")
    print_lg(f"Currently looking for jobs posted within '{date_posted}' and sorting them by '{sort_by}'")
    apply_to_jobs(search_terms)
    print_lg("########################################################################################################################\n")

    # Log completion status
    print_lg("\n" + "-"*80)
    print_lg(f"CYCLE {total_runs} COMPLETED")
    print_lg("-"*80)
    print_lg(f"Total jobs captured so far: {easy_applied_count + external_jobs_count}")
    print_lg(f"  - Easy Apply available: {easy_applied_count}")
    print_lg(f"  - External links captured: {external_jobs_count}")
    print_lg(f"Failed: {failed_count}, Skipped: {skip_count}")
    print_lg("-"*80 + "\n")

    if not dailyEasyApplyLimitReached:
        # Short buffer between runs (only relevant if run_non_stop is enabled)
        if run_non_stop:
            print_lg("Waiting 10 seconds before next cycle...")
            sleep(10)
        else:
            print_lg("Preparing to exit (run_non_stop is disabled)...")
            sleep(3)  # Short pause before final summary
    buffer(3)
    return total_runs + 1



chatGPT_tab = False
linkedIn_tab = False


def main() -> None:
    total_runs = 1
    try:
        global linkedIn_tab, tabs_count, useNewResume, aiClient, mongo_db
        alert_title = "Error Occurred. Closing Browser!"
        validate_config()

        # -- MongoDB initialisation ------------------------------------------
        if use_mongodb:
            print_lg("\n" + "="*80)
            print_lg("??  MONGODB INITIALISATION")
            print_lg("="*80)
            try:
                from modules.db import get_db
                mongo_db = get_db(mongodb_uri, mongodb_database)
                print_lg("? MongoDB ready — all job data will be stored in linkedin-jobs collection.")
            except Exception as _mongo_err:
                print_lg(f"?? Could not connect to MongoDB: {_mongo_err}")
                print_lg("MongoDB is required. Job data will not be saved this run.")
                mongo_db = None
            print_lg("="*80 + "\n")
        else:
            print_lg("?? use_mongodb is False — MongoDB is required. No job data will be saved.")

        if not os.path.exists(default_resume_path):
            print_lg(f'WARNING: Default resume "{default_resume_path}" is missing!')
            print_lg('The bot will continue using your previous upload from LinkedIn.')
            print_lg('To upload a new resume, update the "default_resume_path" in config/questions.py')
            useNewResume = False
        
        # Login to LinkedIn
        tabs_count = len(driver.window_handles)
        driver.get("https://www.linkedin.com/login")
        if not is_logged_in_LN(): login_LN()
        
        linkedIn_tab = driver.current_window_handle

        # # Login to ChatGPT in a new tab for resume customization
        # if use_resume_generator:
        #     try:
        #         driver.switch_to.new_window('tab')
        #         driver.get("https://chat.openai.com/")
        #         if not is_logged_in_GPT(): login_GPT()
        #         open_resume_chat()
        #         global chatGPT_tab
        #         chatGPT_tab = driver.current_window_handle
        #     except Exception as e:
        #         print_lg("Opening OpenAI chatGPT tab failed!")
        if use_AI:
            if ai_provider == "openai":
                aiClient = ai_create_openai_client()
            # Create DeepSeek client
            elif ai_provider == "deepseek":
                aiClient = deepseek_create_client()
            elif ai_provider == "gemini":
                aiClient = gemini_create_client()

            try:
                about_company_for_ai = " ".join([word for word in (first_name+" "+last_name).split() if len(word) > 3])
                print_lg(f"Extracted about company info for AI: '{about_company_for_ai}'")
            except Exception as e:
                print_lg("Failed to extract about company info!", e)
        
        # Start applying to jobs
        driver.switch_to.window(linkedIn_tab)
        total_runs = run(total_runs)

        # Check if we should continue running or terminate
        if not run_non_stop:
            print_lg("\n" + "="*80)
            print_lg("SINGLE CYCLE COMPLETED - TERMINATING")
            print_lg("="*80)
            print_lg("Reason: 'run_non_stop' is set to False in config/settings.py")
            print_lg("The bot completed one full search cycle and will now exit.")
            print_lg("")
            print_lg("To enable continuous running:")
            print_lg("  1. Open config/settings.py")
            print_lg("  2. Change 'run_non_stop = False' to 'run_non_stop = True'")
            print_lg("  3. Re-run the bot")
            print_lg("="*80 + "\n")
        elif dailyEasyApplyLimitReached:
            print_lg("\n" + "="*80)
            print_lg("DAILY EASY APPLY LIMIT REACHED - TERMINATING")
            print_lg("="*80)
            print_lg("LinkedIn has indicated you've reached the daily application limit.")
            print_lg("The bot will now exit to prevent errors.")
            print_lg("You can resume tomorrow when the limit resets.")
            print_lg("="*80 + "\n")

        while(run_non_stop):
            if all_pages_exhausted:
                print_lg("\n" + "="*80)
                print_lg("ALL SEARCH RESULTS EXHAUSTED — STOPPING")
                print_lg("="*80)
                print_lg("Every search term has reached the last page of results.")
                print_lg("No new pages to process. Closing browser.")
                print_lg("="*80 + "\n")
                break
            if cycle_date_posted:
                date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]
                global date_posted
                date_posted = date_options[date_options.index(date_posted)+1 if date_options.index(date_posted)+1 > len(date_options) else -1] if stop_date_cycle_at_24hr else date_options[0 if date_options.index(date_posted)+1 >= len(date_options) else date_options.index(date_posted)+1]
            if alternate_sortby:
                global sort_by
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
                total_runs = run(total_runs)
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
            total_runs = run(total_runs)
            if dailyEasyApplyLimitReached:
                break
        


    except KeyboardInterrupt:
        print_lg("\n\n" + "="*80)
        print_lg("KEYBOARD INTERRUPT DETECTED (Ctrl+C pressed)")
        print_lg("="*80)
        print_lg("Terminating gracefully and saving progress...")
        print_lg("Please wait while we clean up...")
    except ConnectionResetError as e:
        print_lg("\n\n" + "="*80)
        print_lg("CONNECTION RESET ERROR")
        print_lg("="*80)
        print_lg(f"The browser connection was forcibly closed: {e}")
        print_lg("This can happen when:")
        print_lg("  - Browser was closed manually")
        print_lg("  - Network connection was interrupted")
        print_lg("  - LinkedIn detected unusual activity")
        print_lg("Terminating gracefully...")
    except (NoSuchWindowException, WebDriverException) as e:
        print_lg("\n\n" + "="*80)
        print_lg("BROWSER CONNECTION ERROR")
        print_lg("="*80)
        print_lg(f"Browser window closed or session is invalid: {e}")
        print_lg("Exiting gracefully...")
    except Exception as e:
        print_lg("="*80)
        print_lg("?? CRITICAL ERROR in Main Application Flow")
        print_lg("="*80)
        critical_error_log("In Applier Main", e)
        print_lg(f"Error: {str(e)}")
        print_lg(f"Error type: {type(e).__name__}")
        print_lg("The bot will attempt to exit gracefully...")
        print_lg("="*80)
    finally:
        summary = "Total runs: {}\nJobs Easy Applied: {}\nExternal job links collected: {}\nTotal applied or collected: {}\nFailed jobs: {}\nIrrelevant jobs skipped: {}\n".format(total_runs,easy_applied_count,external_jobs_count,easy_applied_count + external_jobs_count,failed_count,skip_count)
        print_lg(summary)
        print_lg("\n\nTotal runs:                     {}".format(total_runs))
        print_lg("Jobs Easy Applied:              {}".format(easy_applied_count))
        print_lg("External job links collected:   {}".format(external_jobs_count))
        print_lg("                              ----------")
        print_lg("Total applied or collected:     {}".format(easy_applied_count + external_jobs_count))
        print_lg("\nFailed jobs:                    {}".format(failed_count))
        print_lg("Irrelevant jobs skipped:        {}\n".format(skip_count))
        if randomly_answered_questions: print_lg("\n\nQuestions randomly answered:\n  {}  \n\n".format(";\n".join(str(question) for question in randomly_answered_questions)))
        quotes = choice([
            "Never quit. You're one step closer than before. - 3COR AI", 
            "All the best with your future interviews, you've got this. - 3COR AI", 
            "Keep up with the progress. You got this. - 3COR AI", 
            "If you're tired, learn to take rest but never give up. - 3COR AI",
            "Success is not final, failure is not fatal, It is the courage to continue that counts. - Winston Churchill (Not a sponsor)",
            "Believe in yourself and all that you are. Know that there is something inside you that is greater than any obstacle. - Christian D. Larson (Not a sponsor)",
            "Every job is a self-portrait of the person who does it. Autograph your work with excellence. - Jessica Guidobono (Not a sponsor)",
            "The only way to do great work is to love what you do. If you haven't found it yet, keep looking. Don't settle. - Steve Jobs (Not a sponsor)",
            "Opportunities don't happen, you create them. - Chris Grosser (Not a sponsor)",
            "The road to success and the road to failure are almost exactly the same. The difference is perseverance. - Colin R. Davis (Not a sponsor)",
            "Obstacles are those frightful things you see when you take your eyes off your goal. - Henry Ford (Not a sponsor)",
            "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt (Not a sponsor)",
            ])
        sponsors = "Be the first to have your name here!"
        timeSaved = (easy_applied_count * 80) + (external_jobs_count * 20) + (skip_count * 10)
        timeSavedMsg = ""
        if timeSaved > 0:
            timeSaved += 60
            timeSavedMsg = f"In this run, you saved approx {round(timeSaved/60)} mins ({timeSaved} secs), please consider supporting the project."
        msg = f"{quotes}\n\n\n{timeSavedMsg}\nYou can also get your quote and name shown here, or prioritize your bug reports by supporting the project\n\n\nSummary:\n{summary}\n\n\nBest regards,\n3COR AI\nhttps://www.linkedin.com/company/3cor/\n\nTop Sponsors:\n{sponsors}"
        pyautogui.alert(msg, "Exiting..")
        print_lg(msg,"Closing the browser...")
        if tabs_count >= 10:
            msg = "NOTE: IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM!\n\nOr it's highly likely that application will just open browser and not do anything next time!" 
            pyautogui.alert(msg,"Info")
            print_lg("\n"+msg)
        if use_AI and aiClient:
            try:
                if ai_provider.lower() == "openai":
                    ai_close_openai_client(aiClient)
                elif ai_provider.lower() == "deepseek":
                    ai_close_openai_client(aiClient)
                elif ai_provider.lower() == "gemini":
                    pass # Gemini client does not need to be closed
                print_lg(f"Closed {ai_provider} AI client.")
            except Exception as e:
                print_lg("Failed to close AI client:", e)
        try:
            if driver:
                driver.quit()
        except WebDriverException as e:
            print_lg("Browser already closed.", e)
        except Exception as e:
            critical_error_log("When quitting...", e)
        # -- Close MongoDB ---------------------------------------------------
        if use_mongodb and mongo_db is not None:
            try:
                from modules.db import close_db
                close_db()
            except Exception as _cdb_err:
                print_lg(f"Note: MongoDB close error (non-critical): {_cdb_err}")


if __name__ == "__main__":
    main()
