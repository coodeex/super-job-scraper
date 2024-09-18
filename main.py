import time
import json
from openai import OpenAI
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Initialize OpenAI client
client = OpenAI()

# Initialize Selenium WebDriver
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Open the browser and navigate to the URL
url = 'https://www.aalto.fi/en/open-positions'
driver.get(url)

# Wait for the page to fully load (adjust time if necessary)
time.sleep(5)

# Get the page source
html = driver.page_source

# Parse the HTML content with BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

# Extract all tags and classes from the HTML
tags_classes = {}
for tag in soup.find_all():
    tag_name = tag.name
    class_list = tag.get('class')
    if class_list:
        class_list = ' '.join(class_list)
        if tag_name in tags_classes:
            tags_classes[tag_name].add(class_list)
        else:
            tags_classes[tag_name] = set([class_list])

# Prepare a summary of tags and classes
tags_classes_summary = []
for tag_name, classes in tags_classes.items():
    for class_name in classes:
        tags_classes_summary.append(f"Tag: {tag_name}, Class: {class_name}")

tags_classes_text = "\n".join(tags_classes_summary)

# Define Pydantic model for expected JSON response
class ElementInfo(BaseModel):
    tag: str
    class_name: str

# Use OpenAI API to analyze the tags and classes to suggest which ones contain job postings
prompt = f"""You are given a list of HTML tags and their class names extracted from a webpage that lists job positions. Your task is to analyze the tags and classes and identify which tag and class are most likely to contain the job postings, specifically the job titles and the links to the job descriptions.

Here is the list of tags and classes:

{tags_classes_text}

Please provide the tag name and class name that should be used to extract the job postings.

Provide the answer in JSON format:
{{
  "tag": "<tag_name>",
  "class_name": "<class_name>"
}}
"""

# OpenAI API call to get the tag and class for job postings using Pydantic parsing
completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are an expert at structured data extraction."},
        {"role": "user", "content": prompt}
    ],
    response_format=ElementInfo,
)

element_info = completion.choices[0].message.parsed
print("OpenAI response for HTML elements to scrape:")
print(element_info)

# Use the parsed response to get the tag and class
tag_name = element_info.tag
class_name = element_info.class_name

# Use BeautifulSoup to find the job postings based on the returned tag/class
job_elements = soup.find_all(tag_name, class_=class_name)

jobs = []

for job_element in job_elements:
    # Extract the job title and link
    a_tag = job_element.find('a')
    if a_tag:
        title = a_tag.get_text(strip=True)
        link = a_tag.get('href')
        if link:
            if not link.startswith('http'):
                link = 'https://www.aalto.fi' + link
            jobs.append({'title': title, 'link': link})

# Define Pydantic model for job summaries
class JobSummary(BaseModel):
    summary: str

# Use OpenAI to analyze the extracted job postings
job_descriptions = json.dumps(jobs, indent=2)

prompt = f"""You are given a list of job postings in JSON format. Each job has a 'title' and a 'link'. Analyze this list and return a brief summary of the job positions.

Here is the JSON data:

{job_descriptions}

Provide a summary of these job positions.
"""

# OpenAI API call to summarize the job postings using Pydantic parsing
completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": "You are an expert at structured data extraction."},
        {"role": "user", "content": prompt}
    ],
    response_format=JobSummary,
)

summary = completion.choices[0].message.parsed.summary
print("\nSummary of Job Positions:")
print(summary)

# Loop through the job postings and open links in new tabs
for idx, job in enumerate(jobs, start=1):
    print(f"{idx}. {job['title']}")
    print(f"   Link: {job['link']}\n")
    if job['link']:
        # Open the link in a new tab
        driver.execute_script(f"window.open('{job['link']}', '_blank');")
        time.sleep(1)  # Adjust sleep if necessary



# make an infinite loop to keep the browser open
while True:
    pass

# Close the browser
#driver.quit()
