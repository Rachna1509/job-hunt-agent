from rich.console import Console
from rich.table import Table
import os, json
import time
import requests
import pandas as pd
from openai import OpenAI

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set.")
if not RAPIDAPI_KEY:
    raise ValueError("RAPIDAPI_KEY is not set.")

client = OpenAI(api_key=OPENAI_API_KEY)

# --- Fetch jobs from API ---
def fetch_jobs(role, location, pages=1):
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    all_jobs = []
    for page in range(1, pages + 1):
        params = {
            "query": f"{role} in {location}",
            "page": str(page),
            "num_pages": "1"
        }
        print(f"Fetching page {page}: {params['query']}")
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        for job in data.get("data", []):
            all_jobs.append({
                "Title": job.get("job_title", ""),
                "Company": job.get("employer_name", ""),
                "Location": job.get("job_city", "") or location,
                "Source": job.get("job_publisher", ""),
                "Link": job.get("job_apply_link", "") or job.get("job_google_link", ""),
                "Description": job.get("job_description", "")[:2000]
            })
        time.sleep(0.5)
    print(f"Fetched {len(all_jobs)} jobs from {location}")
    return all_jobs

# --- GPT-4o Mini to Score Jobs ---
def score_job(resume_text, job_text):
    prompt = (
        "Rate the match between this resume and this job from 0 to 100. "
        "Answer with only the number.\n\n"
        f"Resume:\n{resume_text}\n\nJob:\n{job_text}\n"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        score = response.choices[0].message.content.strip()
        return int(score)
    except Exception as e:
        print("❌ Error scoring job:", e)
        return 0

# --- MAIN WORKFLOW ---
def main():
    # Read resume
    with open("resume.txt", "r") as f:
        resume_text = f.read()

    # Read from environment
    role = os.environ.get("JOB_ROLE", "Product Manager")
    cities_json = os.environ.get("JOB_CITIES", '["Los Angeles"]')
    cities = json.loads(cities_json)

    print(f"\n🔍 Searching for role: '{role}' in cities: {cities}")

    all_jobs = []
    for city in cities:
        jobs = fetch_jobs(role, city, pages=1)
        all_jobs.extend(jobs)

    # Score jobs
    for job in all_jobs:
        job_text = f"{job['Title']} at {job['Company']} in {job['Location']}.\n{job['Description']}"
        job["Match %"] = score_job(resume_text, job_text)
        time.sleep(0.5)

    # Filter & sort
    filtered = [j for j in all_jobs if j["Match %"] >= 70]
    filtered.sort(key=lambda x: x["Match %"], reverse=True)

    print(f"\n✅ {len(filtered)} jobs passed the 70% threshold.")

    # Console Output
    console = Console()
    table = Table(title="Top Matching Jobs")
    table.add_column("Title", style="cyan", no_wrap=True)
    table.add_column("Company", style="magenta")
    table.add_column("Location", style="green")
    table.add_column("Match %", justify="right", style="bold yellow")

    for j in filtered[:5]:
        table.add_row(j["Title"], j["Company"], j["Location"], str(j["Match %"]))

    console.print(table)

    # Save CSV
    df = pd.DataFrame(filtered)
    df.to_csv("jobs_scored.csv", index=False)
    print("\n💾 Saved jobs_scored.csv")

if __name__ == "__main__":
    main()
