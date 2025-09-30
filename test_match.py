import os
from openai import OpenAI

# Load API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set your OPENAI_API_KEY environment variable.")

client = OpenAI(api_key=api_key)

# Read resume
with open("resume.txt", "r") as f:
    resume_text = f.read()

# Sample job description
job_description = """
We are hiring a Data Analyst with experience in SQL, Python, and dashboards.
The ideal candidate has 2+ years in analytics and strong problem-solving skills.
"""

prompt = f"Compare this resume to the job description below and rate the match from 0 to 100.\n\nResume:\n{resume_text}\n\nJob:\n{job_description}\n\nAnswer with only the number."

response = client.responses.create(
    model="gpt-4o-mini",
    input=prompt
)

print("Match score:", response.output_text)
