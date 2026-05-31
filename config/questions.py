'''
Author:     Venkat S
LinkedIn:   https://www.linkedin.com/company/3cor/

Copyright (C) 2026 3COR AI

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/venkat-singi-reddy


version:    26.01.20.5.08
'''


###################################################### APPLICATION INPUTS ######################################################


# >>>>>>>>>>> Easy Apply Questions & Inputs <<<<<<<<<<<

# Give an relative path of your default resume to be uploaded. If file in not found, will continue using your previously uploaded resume in LinkedIn.
default_resume_path = "all resumes/default/resume.pdf"      # (In Development)

# What do you want to answer for questions that ask about years of experience you have, this is different from current_experience? 
years_of_experience = "12"          # A number in quotes Eg: "0","1","2","3","4", etc.

# Do you need visa sponsorship now or in future?
require_visa = "Yes"           # "Yes" or "No"

# What is the link to your portfolio website, leave it empty as "", if you want to leave this question unanswered
website = "https://www.singireddi.com"                        # "www.example.bio" or "" and so on....

# Please provide the link to your LinkedIn profile.
linkedIn = "https://www.linkedin.com/company/3cor/"       # "https://www.linkedin.com/company/3cor/" or "" and so on...

# What is the status of your citizenship? # If left empty as "", tool will not answer the question. However, note that some companies make it compulsory to be answered
# Valid options are: "U.S. Citizen/Permanent Resident", "Non-citizen allowed to work for any employer", "Non-citizen allowed to work for current employer", "Non-citizen seeking work authorization", "Canadian Citizen/Permanent Resident" or "Other"
us_citizenship = "Non-citizen seeking work authorization"



## SOME ANNOYING QUESTIONS BY COMPANIES ?? ##

# What to enter in your desired salary question (American and European), What is your expected CTC (South Asian and others)?, only enter in numbers as some companies only allow numbers,
desired_salary = 175000         # 80000, 90000, 100000 or 120000 and so on... Do NOT use quotes
'''
Note: If question has the word "lakhs" in it (Example: What is your expected CTC in lakhs), 
then it will add '.' before last 5 digits and answer. Examples: 
* 2400000 will be answered as "24.00"
* 850000 will be answered as "8.50"
And if asked in months, then it will divide by 12 and answer. Examples:
* 2400000 will be answered as "200000"
* 850000 will be answered as "70833"
'''

# What is your current CTC? Some companies make it compulsory to be answered in numbers...
current_ctc = 140000            # 800000, 900000, 1000000 or 1200000 and so on... Do NOT use quotes
'''
Note: If question has the word "lakhs" in it (Example: What is your current CTC in lakhs), 
then it will add '.' before last 5 digits and answer. Examples: 
* 2400000 will be answered as "24.00"
* 850000 will be answered as "8.50"
# And if asked in months, then it will divide by 12 and answer. Examples:
# * 2400000 will be answered as "200000"
# * 850000 will be answered as "70833"
'''

# (In Development) # Currency of salaries you mentioned. Companies that allow string inputs will add this tag to the end of numbers. Eg: 
# currency = "INR"                 # "USD", "INR", "EUR", etc.

# What is your notice period in days?
notice_period = 15                 # Any number >= 0 without quotes. Eg: 0, 7, 15, 30, 45, etc.
'''
Note: If question has 'month' or 'week' in it (Example: What is your notice period in months), 
then it will divide by 30 or 7 and answer respectively. Examples:
* For notice_period = 66:
  - "66" OR "2" if asked in months OR "9" if asked in weeks
* For notice_period = 15:"
  - "15" OR "0" if asked in months OR "2" if asked in weeks
* For notice_period = 0:
  - "0" OR "0" if asked in months OR "0" if asked in weeks
'''

# Your LinkedIn headline in quotes Eg: "Software Engineer @ Google, Masters in Computer Science", "Recent Grad Student @ MIT, Computer Science"
linkedin_headline = "Lead Software Engineer and 12+ years of experience" # "Headline" or "" to leave this question unanswered

# Your summary in quotes, use \n to add line breaks if using single quotes "Summary".You can skip \n if using triple quotes """Summary"""
linkedin_summary = """
12+ years of experience in designing and developing scalable, high performance backend services using Java, Spring, Spring Boot and other open source frameworks.
8 + years of full-stack development experience using Html, JSPs, TypeScript, React and Angular.
Proven experience creating, maintaining, and troubleshooting real-time, high-performance, and high-availability Java applications intended for on-premise and cloud deployments.
Expertise with monitoring and observability tools such as Grafana, Prometheus, DataDog and Splunk for performance analysis.
Very strong experience creating APIs/GraphQL/gRPC and Web Services in Java and Python
Designed non-blocking APIs using Spring WebFlux (Mono, Flux)
Designed and implemented microservices and event-driven architectures leveraging cloud-native services on both GCP, AWS and tools like Apache Kafka.
"""

'''
Note: If left empty as "", the tool will not answer the question. However, note that some companies make it compulsory to be answered. Use \n to add line breaks.
''' 

# Your cover letter in quotes, use \n to add line breaks if using single quotes "Cover Letter".You can skip \n if using triple quotes """Cover Letter""" (This question makes sense though)
cover_letter = """
Dear Hiring Manager,
I am writing to express my interest in the Lead Software Engineer position at your esteemed organization. With over 12 years of experience in designing and developing scalable, high-performance backend services using Java, Spring,Spring Boot, Mirco services and any Public/Private Cloud Platfroms , I am confident in my ability to contribute effectively to your team.
"""

# Your user_information_all letter in quotes, use \n to add line breaks if using single quotes "user_information_all".You can skip \n if using triple quotes """user_information_all""" (This question makes sense though)
# We use this to pass to AI to generate answer from information , Assuing Information contians eg: resume  all the information like name, experience, skills, Country, any illness etc. 
user_information_all ="""
"""
'''
Note: If left empty as "", the tool will not answer the question. However, note that some companies make it compulsory to be answered. Use \n to add line breaks.
''' 

# Name of your most recent employer
recent_employer = "WellsFargo" # "", "Lala Company", "Google", "Snowflake", "Databricks"

# Current company (for text fields asking "Current Company")
current_company = "Wells Fargo"    # "Wells Fargo", "Google", "Microsoft", etc.

# Current job title (for text fields asking "Current Title" or "Current Position")
current_title = "Lead Software Engineer"  # "Lead Software Engineer", "Senior Developer", "Software Engineer", etc.

# Example question: "On a scale of 1-10 how much experience do you have building web or mobile applications? 1 being very little or only in school, 10 being that you have built and launched applications to real users"
confidence_level = "8"             # Any number between "1" to "10" including 1 and 10, put it in quotes ""


## EDUCATION INFORMATION ##

# School/University/College name - use "Not Applicable" or "Other" or "0" if you prefer not to specify or if field is not relevant
school_name = "Other"     # "University of Example", "Not Applicable", "Other", "0", etc.

# Degree/Education level - choose the format that best matches typical job applications
degree = "Master's"                # "Master's", "M.S", "MS", "Masters", "Bachelor's", "B.S", "BS", "PhD", etc.

# Field of Study/Major/Specialization/Discipline - be specific about your area of study
specialization = "Computer Science"  # "Computer Science", "Computer Applications", "Information Science", "Information Technology", etc.
discipline = "Computer Science"      # Same as specialization - some companies use "Discipline" instead of "Specialization"
'''
Note: These fields help answer education-related questions in job applications.
Common variations:
- School: "Not Applicable", "Other", "0" (if not wanting to specify)
- Degree: "Master's" or "M.S" or "MS" or "Masters" (choose one format and stick with it)
- Specialization/Discipline: "Computer Science" is most common, but some jobs may ask for:
  * "Computer Applications" - more application-focused
  * "Information Science" - more data/information focused
  * "Information Technology" - more IT infrastructure focused
'''

# How did you hear about this job/position?
referral_source = "LinkedIn"         # "LinkedIn", "Indeed", "Company Website", "Referral", "Job Board", etc.
'''
Note: This answers questions like "How did you hear about this job?" or "Where did you find this position?"
Common answers: "LinkedIn", "Indeed", "Glassdoor", "Company Website", "Referral", "Job Fair", etc.
'''


## ADDITIONAL APPLICATION QUESTIONS ##

# Gender identity
gender_identity = "Male"             # "Male", "Female", "Non-binary", "Prefer not to say", "I prefer not to specify"

# Visa and work authorization
require_visa_sponsorship = "Yes"     # "Yes", "No" - Do you require sponsorship now or in the future?
work_authorization_us = "Yes"        # "Yes", "No", "Unknown" - Are you currently eligible to work in the US?

# Race/Ethnicity (for diversity forms)
race_ethnicity = "I prefer not to specify"  # Or specific race if you want to share

# Location preferences
current_country = "USA"              # Current country of residence
open_to_relocation = "Yes"           # "Yes", "No" - Are you open to relocation?
preferred_hub_city = "N/A: Remote Only"  # Or specific city - will choose first option if this doesn't match

# Primary motivation for exploring new opportunities
primary_motivation = "I have led major initiatives across Java, Spring Boot, distributed architectures, and cloud platforms including GCP and AWS. This role stands out to me because it aligns deeply with my passion for designing resilient, customer focused solutions, driving engineering excellence, and mentoring teams. My background in microservices, automated testing, and cloud-native development positions me well to contribute meaningfully from day one."
'''
Note: This answers questions like:
- "What is your primary motivation for exploring new opportunities?"
- "Why are you interested in this role?"
- "What attracts you to this position?"
'''

# Notice period / Availability to join
notice_period_selection = "15-30 days"  # "Immediate Joiner", "15-30 days", "30-60 days", "60-90 days", etc.
'''
Note: This is for dropdown/select questions asking about notice period.
Different from the numeric notice_period field above, this is used when the application
provides specific options to choose from like:
- "Immediate Joiner"
- "15-30 days"
- "30-60 days"
- "60-90 days"
'''

# Today's Date (for date fields asking for current date)
# The bot will automatically use the system date in MM/dd/yyyy format
# No configuration needed - this is handled automatically
'''
Note: When a date field asks for "Today's Date", the bot will automatically
fill it with the current system date formatted as MM/dd/yyyy
Example: 02/26/2026
'''

# How did you learn about this role/position?
how_did_you_hear = "LinkedIn"        # "LinkedIn", "Social Media", "Indeed", "Glassdoor", "Company Website", etc.
'''
Note: This is for "How did you learn about this role?" questions.
The bot will try to match this with available options. Common options include:
- "LinkedIn"
- "Social Media"
- "Indeed"
- "Glassdoor"
- "Company Career Site"
- "Referral"
If exact match not found, will try "Social Media" then "LinkedIn" as fallback.
'''

# Legal work authorization
legal_work_authorization = "Yes"     # "Yes", "No" - Do you have legal authorization to work in this country?
'''
Note: This answers questions like:
- "Do you have legal authorization to work in the country where this job is located?"
- "Are you legally authorized to work in [country]?"
'''

# Language fluency (other than English)
other_languages_fluent = "Yes, Hindi/Telugu"  # Your answer for language fluency questions
'''
Note: This answers questions like:
- "Are you fluent in any language other than English? Please specify."
- "What other languages do you speak?"
If you don't speak other languages, use "No" or "None"
'''

# CS Degree or equivalent
has_cs_degree = "Yes"                # "Yes", "No" - Do you have a Computer Science degree or equivalent?
'''
Note: This answers questions like:
- "Do you have a CS (or equivalent degree)?"
- "Do you have a Computer Science degree?"
- "Do you have a degree in Computer Science or related field?"
'''

# Hiring manager message / Cover letter for applications
hiring_manager_message = """Dear Hiring Manager,
I am writing to express my interest in the Lead Software Engineer position at your esteemed organization. With over 12 years of experience in designing and developing scalable, high-performance backend services using Java, Spring, Spring Boot, Microservices and any Public/Private Cloud Platforms, I am confident in my ability to contribute effectively to your team.
"""

# Reasonable accommodation
reasonable_accommodation = ""        # Leave empty if none needed

# Veteran status (for protected veterans form)
protected_veteran_status = "I am not a protected veteran"  # "I identify as one or more of the classifications of protected veteran listed above", "I am not a protected veteran", "I prefer not to specify"

# Relatives employed by company (compliance question)
relatives_in_company = "No"          # "Yes", "No" - Do you have relatives employed by the company?
relatives_names = "N/A"              # If "No", enter "N/A". If "Yes", enter names: "John Doe, Jane Smith"

# Privacy policy and terms acknowledgment (auto-consent)
# These questions ask you to acknowledge/agree/consent to privacy notices, terms, etc.
# Options: "Yes", "Agree", "Acknowledge", "I agree", "I acknowledge", "Consent", etc.
acknowledge_privacy_policy = "Yes"   # Default: "Yes" - Automatically agrees to privacy policies and terms
'''
Note: This setting applies to questions like:
- "I acknowledge that I have read and agree to the Privacy Notice"
- "Do you agree to the Terms of Service?"
- "I consent to the collection of my data as described in the Privacy Policy"
The bot will automatically select "Yes", "Agree", "Acknowledge", or "Consent" options.
'''

##



# >>>>>>>>>>> RELATED SETTINGS <<<<<<<<<<<

## Allow Manual Inputs
# Should the tool pause before every submit application during easy apply to let you check the information?
pause_before_submit = False         # True or False, Note: True or False are case-sensitive - SAFE MODE: Disabled for efficiency
'''
Note: Will be treated as False if `run_in_background = True`
'''

# Should the tool pause if it needs help in answering questions during easy apply?
# Note: If set as False will answer randomly...
pause_at_failed_question = True    # True or False, Note: True or False are case-sensitive - SAFE MODE: Enabled for quality control
'''
Note: Will be treated as False if `run_in_background = True`
'''
##

# Do you want to overwrite previous answers?
overwrite_previous_answers = False # True or False, Note: True or False are case-sensitive







############################################################################################################
'''
THANK YOU for using my tool ??! Wishing you the best in your job hunt ????!
'''
############################################################################################################
