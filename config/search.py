'''
Author:     Venkat S
LinkedIn:   https://www.linkedin.com/company/3cor/

Copyright (C) 2026 3COR AI

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/venkat-singi-reddy


version:    26.01.20.5.08
'''


###################################################### LINKEDIN SEARCH PREFERENCES ######################################################

# Job search terms — each entry in the list can be:
#
#   1. A plain string  →  keywords are sent WITHOUT double quotes (broad match)
#      Example:  "Software Engineer"
#      LinkedIn URL: keywords=Software Engineer
#
#   2. A dict with "terms" + "operator"  →  each term is quoted and joined with AND / OR
#      Example:  {"terms": ["Software Engineer", "Java"], "operator": "AND"}
#      LinkedIn URL: keywords="Software Engineer" AND "Java"
#
#      Example:  {"terms": ["Software Engineer", "Backend Engineer"], "operator": "OR"}
#      LinkedIn URL: keywords="Software Engineer" OR "Backend Engineer"
#
#      Single-term dict (one term + any operator) wraps the term in double quotes:
#      Example:  {"terms": ["Lead Software Engineer"], "operator": "AND"}
#      LinkedIn URL: keywords="Lead Software Engineer"
#
# Valid operator values: "AND", "OR"  (case-insensitive)
search_terms = [
    #"Lead Software Engineer",                                                      # plain → no quotes
    #{"terms": ["Lead", "Software Engineer"], "operator": "AND"},           # → "Software Engineer" AND "Java"
    {"terms": ["Java", "Backend"], "operator": "AND"},# → "Software Engineer" OR "Backend Engineer"
    #{"terms": ["software engineer","sr"], "operator": "AND"},
    #{"terms": ["Software Engineer","Senior"], "operator": "AND"},
    {"terms": ["Tech","Lead"], "operator": "AND"},
    {"terms": ["Tech","Java"], "operator": "AND"},
    #{"terms": ["Principal","Engineer"], "operator": "AND"},
    {"terms": ["fullstack","engineer"], "operator": "AND"},
    {"terms": ["fullstack","java"], "operator": "AND"},
    {"terms": ["full-stack","engineer"], "operator": "AND"},
    {"terms": ["full-stack","Java"], "operator": "AND"},
    {"terms": ["Java","Engineer"], "operator": "AND"},
    {"terms": ["Java"], "operator": "AND"},
    #{"terms": ["Staff", "Engineer"], "operator": "AND"},  #single term → "Lead Software Engineer"
]

#  "Python Developer", "Selenium Developer", "React Developer", "Java Developer", "Front End Developer", "Full Stack Developer", "Web Developer", "Nodejs Developer"

# Search location, this will be filled in "City, state, or zip code" search box. If left empty as "", tool will not fill it.
search_location = "United States"               # Some valid examples: "", "United States", "India", "Chicago, Illinois, United States", "90001, Los Angeles, California, United States", "Bengaluru, Karnataka, India", etc.

# After how many number of applications in current search should the bot switch to next search? 
switch_number = 9999               # Only numbers greater than 0... Don't put in quotes - CONTINUOUS MODE: Set high to process all jobs

# Do you want to randomize the search order for search_terms?
randomize_search_order = False     # True of False, Note: True or False are case-sensitive


# >>>>>>>>>>> Job Search Filters <<<<<<<<<<<
''' 
You could set your preferences or leave them as empty to not select options except for 'True or False' options. Below are some valid examples for leaving them empty:
This is below format: QUESTION = VALID_ANSWER

## Examples of how to leave them empty. Note that True or False options cannot be left empty! 
* question_1 = ""                    # answer1, answer2, answer3, etc.
* question_2 = []                    # (multiple select)
* question_3 = []                    # (dynamic multiple select)

## Some valid examples of how to answer questions:
* question_1 = "answer1"                  # "answer1", "answer2", "answer3" or ("" to not select). Answers are case sensitive.
* question_2 = ["answer1", "answer2"]     # (multiple select) "answer1", "answer2", "answer3" or ([] to not select). Note that answers must be in [] and are case sensitive.
* question_3 = ["answer1", "Random AnswER"]     # (dynamic multiple select) "answer1", "answer2", "answer3" or ([] to not select). Note that answers must be in [] and need not match the available options.

'''

sort_by = "Most recent"            # "Most recent", "Most relevant" or ("" to not select) - Set to "Most recent" for optimal filtering
date_posted = "Past week"        # "Any time", "Past month", "Past week", "Past 24 hours" or ("" to not select) - SAFE MODE: Set to Past week
salary = ""                        # "$40,000+", "$60,000+", "$80,000+", "$100,000+", "$120,000+", "$140,000+", "$160,000+", "$180,000+", "$200,000+"


experience_level = []              # (multiple select) "Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"
job_type = []                      # (multiple select) "Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship", "Other"
on_site = []                       # (multiple select) "On-site", "Remote", "Hybrid"

companies = []                     # (dynamic multiple select) make sure the name you type in list exactly matches with the company name you're looking for, including capitals. 
                                   # Eg: "7-eleven", "Google","X, the moonshot factory","YouTube","CapitalG","Adometry (acquired by Google)","Meta","Apple","Byte Dance","Netflix", "Snowflake","Mineral.ai","Microsoft","JP Morgan","Barclays","Visa","American Express", "Snap Inc", "JPMorgan Chase & Co.", "Tata Consultancy Services", "Recruiting from Scratch", "Epic", and so on...
location = []                      # (dynamic multiple select)
industry = []                      # (dynamic multiple select)
job_function = []                  # (dynamic multiple select)
job_titles = []                    # (dynamic multiple select)
benefits = []                      # (dynamic multiple select)
commitments = []                   # (dynamic multiple select)

under_10_applicants = False        # True or False, Note: True or False are case-sensitive
in_your_network = False            # True or False, Note: True or False are case-sensitive
fair_chance_employer = False       # True or False, Note: True or False are case-sensitive


## >>>>>>>>>>> RELATED SETTING <<<<<<<<<<<

# Pause after applying filters to let you modify the search results and filters?
pause_after_filters = False         # True or False, Note: True or False are case-sensitive

##

## >>>>>>>>>>> SKIP IRRELEVANT JOBS <<<<<<<<<<<

# Exact company names to always skip — matched case-insensitively against the company name shown in the job listing.
# These are applied immediately when the job card is loaded, before any About Company check.
blacklisted_company_names = ["FullStack","HCLTech","Anblicks","AgileEngine","Turing","Tata Consultancy Services", "Infosys", "Wipro","Agoda","Jobs via Dice","DataAnnotation","TEKsystems","Cognizant","ZipRecruiter","Leidos","Elsevier","Jobs via eFinancialCareers","oneZero Financial Systems","Capgemini","Lorvenk Technologies","Synechron","Programmers.io","BeaconFire Inc.","BeaconFire","Arkhya Tech. Inc.","Google","Palo Alto Networks"]      # (dynamic multiple search) or leave empty as []. Ex: ["Tata Consultancy Services", "Infosys", "Wipro"]


'''
Note: Company names must match the text shown in the LinkedIn job card (the subtitle line, before the ·).
Matching is case-insensitive. To skip by keyword in the About Company section instead, use `about_company_bad_words` below.
'''

# Avoid applying to these companies, and companies with these bad words in their 'About Company' section...
about_company_bad_words = ["Staffing", "Recruiting"]       # (dynamic multiple search) or leave empty as []. Ex: ["Staffing", "Recruiting", "Name of Company you don't want to apply to"]

# Skip checking for `about_company_bad_words` for these companies if they have these good words in their 'About Company' section... [Exceptions, For example, I want to apply to "Robert Half" although it's a staffing company]
about_company_good_words = []      # (dynamic multiple search) or leave empty as []. Ex: ["Robert Half", "Dice"]

# Minimum company size filter (employees on LinkedIn)
# Set to 0 to disable this filter, or set a minimum number to only apply to companies with at least that many employees
minimum_company_size = 300       # Only apply to companies with 300+ employees on LinkedIn. Set to 0 to disable. Examples: 0, 300, 500, 1000, 5000, 10000
'''
Note: This checks the "X employees on LinkedIn" count shown in the About Company section, NOT the total company size.
Format example: "24,017 employees on LinkedIn" or "24,017 on LinkedIn"
Common LinkedIn employee ranges: 1-10, 11-50, 51-200, 201-500, 501-1,000, 1,001-5,000, 5,001-10,000, 10,000+

Example: A company with 10,000 total employees might only show "2,000 employees on LinkedIn"
The bot will skip companies below your minimum_company_size threshold based on their LinkedIn employee count.
'''

# Avoid applying to these companies if they have these bad words in their 'Job Description' section...  (In development)
bad_words = ["OPT, CPT","without sponsorship","will not provide immigration sponsorship","sponsorship of an employment Visa at this time","We are unable to sponsor","Visa Sponsorship (first time sponsorship or transfer) is NOT Available","This is not a position for which sponsorship will be provided","Visa sponsorship is not available","unable to offer employment sponsorship","U.S. citizenship is required","TS/SCI Clearance","Immigration sponsorship is not available","does not offer sponsorship", "no sponsorship","C2C", "Corp2Corp", "CNC","will not sponsor", "F-1 OPT","F-1 STEM OPT","F-1 CPT","no visa sponsorship","not eligible for visa sponsorship","will not provide sponsorship"]                   # (dynamic multiple search) or leave empty as []. Case Insensitive. Ex: ["word_1", "phrase 1", "word word", "polygraph", "US Citizenship", "Security Clearance"]

# Only apply to jobs whose 'Job Description' contains these required good words. Leave empty as [] to disable this check.
# Case Insensitive. Ex: ["Java", "Spring Boot"] — see job_description_good_words_operator below for AND/OR logic.
job_description_good_words = ["Java", "API", "backend", "full-stack","restful","aws","gcp", "typescript","cloud"]      # (dynamic multiple search) or leave empty as [] to skip this check. Ex: ["Java"], ["Python", "Django"], ["React", "TypeScript"]

# Operator to use when checking job_description_good_words:
#   "OR"  → skip the job if NONE of the words are found  (at least one must match)
#   "AND" → skip the job if ANY of the words is missing  (all words must match)
job_description_good_words_operator = "OR"  # "OR" or "AND"

# Do you have an active Security Clearance? (True for Yes and False for No)
security_clearance = False         # True or False, Note: True or False are case-sensitive

# Do you have a Masters degree? (True for Yes and False for No). If True, the tool will apply to jobs containing the word 'master' in their job description and if it's experience required <= current_experience + 2 and current_experience is not set as -1. 
did_masters = True                 # True or False, Note: True or False are case-sensitive

# Avoid applying to jobs if their required experience is above your current_experience. (Set value as -1 if you want to apply to all ignoring their required experience...)
current_experience = 12            # Integers > -2 (Ex: -1, 0, 1, 2, 3, 4...)
##






############################################################################################################
'''
THANK YOU for using my tool ??! Wishing you the best in your job hunt ????!

Sharing is caring! If you found this tool helpful, please share it with your peers ??. Your support keeps this project alive.

Support my work on <PATREON_LINK>. Together, we can help more job seekers.

As an independent developer, I pour my heart and soul into creating tools like this, driven by the genuine desire to make a positive impact.

Your support, whether through donations big or small or simply spreading the word, means the world to me and helps keep this project alive and thriving.

Gratefully yours ????,
3COR AI
'''
############################################################################################################