from rich.console import Console
from rich.table import Table
import os, json, time, requests, pandas as pd
from openai import OpenAI

# --- CONFIG ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set.")
if not RAPIDAPI_KEY:
    raise ValueError("RAPIDAPI_KEY is not set.")

client = OpenAI(api_key=OPENAI_API_KEY)

# --- JOB SCRAPING FUNCTION ---
def fetch_jobs(role="Product Manager", locations=["Los Angeles"], pages=1):
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    all_jobs = []
    for location in locations:
        for page in range(1, pages + 1):
            params = {
                "query": f"{role} in {location}",
                "page": str(page),
                "num_pages": "1"
            }
            print(f"Fetching {role} in {location} (page {page})")
            r = requests.get(url, headers=headers, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            for job in data.get("data", []):
                all_jobs.append({
                    "Title": job.get("job_title", ""),
                    "Company": job.get("employer_name", ""),
                    "Location": job.get("job_city", location),
                    "Link": job.get("job_apply_link", "") or job.get("job_google_link", ""),
                    "Description": job.get("job_description", "")[:2000],
                    "Source": job.get("job_publisher", "")
                })
            time.sleep(0.5)
    print(f"✅ Fetched {len(all_jobs)} jobs")
    return all_jobs

# --- SCORING FUNCTION ---
def score_job(resume_text, job_text):
    prompt = (
        "Rate the match between this resume and this job from 0 to 100. "
        "Only output the number.\n\n"
        f"Resume:\n{resume_text}\n\nJob:\n{job_text}\n"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",  # Better scoring model
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return int(resp.choices[0].message.content.strip())
    except Exception as e:
        print("⚠️ Error scoring job:", e)
        return 0

# --- MAIN FUNCTION ---
def main():
    # Get role & cities from env (from dashboard)
    role = os.getenv("JOB_ROLE", "Product Manager")
    cities_json = os.getenv("JOB_CITIES", '["Los Angeles"]')
    locations = json.loads(cities_json)

    # Load resume
    with open("resume.txt", "r") as f:
        resume_text = f.read()

    # Fetch and score jobs
    jobs = fetch_jobs(role, locations, pages=1)
    for job in jobs:
        job_text = f"{job['Title']} at {job['Company']} in {job['Location']}.\n{job['Description']}"
        job["Match %"] = score_job(resume_text, job_text)
        time.sleep(0.8)

    # Save CSV
    df = pd.DataFrame(jobs)
    df.sort_values(by="Match %", ascending=False, inplace=True)
    df.to_csv("jobs_scored.csv", index=False)
    print("✅ Saved jobs_scored.csv")

    # Rich summary
    filtered = df[df["Match %"] >= 70]
    table = Table(title="Top Matching Jobs")
    table.add_column("Title", style="cyan", no_wrap=True)
    table.add_column("Company", style="magenta")
    table.add_column("Location", style="green")
    table.add_column("Match %", justify="right", style="bold yellow")
    for _, j in filtered.head(5).iterrows():
        table.add_row(j["Title"], j["Company"], j["Location"], str(j["Match %"]))
    Console().print(table)

if __name__ == "__main__":
    main()
