'''
Author:     Venkat S
LinkedIn:   https://www.linkedin.com/company/3cor/

Copyright (C) 2026 3COR AI

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html

version:    26.01.20.5.08
'''

from modules.helpers import get_default_temp_profile, make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, file_name, failed_file_name, logs_folder_path, generated_resume_path
from config.questions import default_resume_path
if stealth_mode:
    import undetected_chromedriver as uc
else: 
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    # from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from modules.helpers import find_default_profile_directory, critical_error_log, print_lg
from selenium.common.exceptions import SessionNotCreatedException

def createChromeSession(isRetry: bool = False):
    make_directories([file_name,failed_file_name,logs_folder_path+"/screenshots",default_resume_path,generated_resume_path+"/temp"])
    # Set up WebDriver with Chrome Profile
    options = uc.ChromeOptions() if stealth_mode else Options()
    if run_in_background:   options.add_argument("--headless")
    if disable_extensions:  options.add_argument("--disable-extensions")

    print_lg("IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM! Or it's highly likely that application will just open browser and not do anything!")
    profile_dir = find_default_profile_directory()
    if isRetry:
        print_lg("Will login with a guest profile, browsing history will not be saved in the browser!")
    elif profile_dir and not safe_mode:
        options.add_argument(f"--user-data-dir={profile_dir}")
    else:
        print_lg("Logging in with a guest profile, Web history will not be saved!")
        options.add_argument(f"--user-data-dir={get_default_temp_profile()}")
    if stealth_mode:
        try:
            print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
            # Try to create driver with automatic version detection
            driver = uc.Chrome(options=options, version_main=None)
        except SessionNotCreatedException as version_error:
            # If version mismatch, try to extract Chrome version and use it
            error_msg = str(version_error)
            if "Current browser version is" in error_msg:
                import re
                match = re.search(r'Current browser version is (\d+)', error_msg)
                if match:
                    chrome_version = int(match.group(1))
                    print_lg(f"Detected Chrome version {chrome_version}, retrying with correct ChromeDriver...")
                    driver = uc.Chrome(options=options, version_main=chrome_version)
                else:
                    raise
            else:
                raise
    else:
        driver = webdriver.Chrome(options=options)

    driver.maximize_window()
    wait = WebDriverWait(driver, 5)
    actions = ActionChains(driver)
    return options, driver, actions, wait

try:
    options, driver, actions, wait = None, None, None, None
    options, driver, actions, wait = createChromeSession()
except SessionNotCreatedException as e:
    error_msg = str(e)
    if "cannot connect to chrome" in error_msg.lower() and "version" in error_msg.lower():
        # Chrome version mismatch - try with guest profile
        print_lg("Chrome version mismatch detected. Retrying with guest profile...")
        critical_error_log("Chrome/ChromeDriver version mismatch, retrying", e)
        try:
            options, driver, actions, wait = createChromeSession(True)
        except Exception as retry_error:
            msg = f'Chrome/ChromeDriver version mismatch!\n\nYour Chrome version: 145\nRequired ChromeDriver: 146\n\nSOLUTIONS:\n1. Update Google Chrome to latest version (Recommended)\n2. Wait a few days for undetected-chromedriver to update\n3. Try setting stealth_mode = False in config/settings.py\n\nError: {error_msg}'
            print_lg(msg)
            critical_error_log("Chrome version mismatch - cannot proceed", retry_error)
            from pyautogui import alert
            alert(msg, "Chrome Version Mismatch")
            exit()
    else:
        critical_error_log("Failed to create Chrome Session, retrying with guest profile", e)
        options, driver, actions, wait = createChromeSession(True)
except Exception as e:
    msg = 'Seems like Google Chrome is out dated. Update browser and try again! \n\n\nIf issue persists, try Safe Mode. Set, safe_mode = True in config.py \n\nPlease check GitHub discussions/support for solutions https://github.com/venkat-singi-reddy \n                                   OR \nReach out in discord ( https://discord.gg/fFp7uUzWCY )'
    if isinstance(e,TimeoutError): msg = "Couldn't download Chrome-driver. Set stealth_mode = False in config!"
    print_lg(msg)
    critical_error_log("In Opening Chrome", e)
    from pyautogui import alert
    alert(msg, "Error in opening chrome")
    try: driver.quit()
    except NameError: exit()
    
