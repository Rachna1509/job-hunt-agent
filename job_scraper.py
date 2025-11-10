from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
import os, json, time, requests, pandas as pd
from openai import OpenAI

console = Console()

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
    """Fetch jobs from RapidAPI JSearch"""
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
            try:
                console.log(f"[cyan]Fetching {role} in {location} (page {page})[/cyan]")
                r = requests.get(url, headers=headers, params=params, timeout=20)
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
                time.sleep(0.3)
            except Exception as e:
                console.log(f"[red]⚠️ Error fetching {location} page {page}: {e}[/red]")
                continue

    console.log(f"[green]✅ Fetched {len(all_jobs)} jobs total[/green]")
    return all_jobs


# --- SCORING FUNCTION ---
def score_job(resume_text, job_text):
    """Score job-resume match using OpenAI GPT-4o"""
    prompt = (
        "Rate how well this resume matches the job from 0 to 100. "
        "Only output a single integer number.\n\n"
        f"Resume:\n{resume_text}\n\nJob:\n{job_text}\n"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result = resp.choices[0].message.content.strip()
        return int(result) if result.isdigit() else 0
    except Exception as e:
        console.log(f"[red]Error scoring job: {e}[/red]")
        return 0


# --- PARALLEL SCORING FUNCTION ---
def score_all_jobs(jobs, resume_text):
    """Score jobs concurrently for faster execution"""
    scored_jobs = []
    total = len(jobs)
    console.log(f"[bold yellow]Scoring {total} jobs using 5 threads...[/bold yellow]")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                score_job,
                resume_text,
                f"{j['Title']} at {j['Company']} in {j['Location']}.\n{j['Description']}"
            ): j for j in jobs
        }

        for i, future in enumerate(as_completed(futures), start=1):
            job = futures[future]
            try:
                job["Match %"] = future.result()
            except Exception as e:
                job["Match %"] = 0
                console.log(f"[red]⚠️ Scoring failed for {job['Title']}[/red]: {e}")
            scored_jobs.append(job)
            console.log(f"[green]Scored {i}/{total}[/green] - {job['Title']}")

    console.log(f"[green]✅ Completed scoring {len(scored_jobs)} jobs[/green]")
    return scored_jobs


# --- MAIN FUNCTION ---
def main():
    role = os.getenv("JOB_ROLE", "Product Manager")
    cities_json = os.getenv("JOB_CITIES", '["Los Angeles"]')
    locations = json.loads(cities_json)

    resume_path = "resume.txt"
    if not os.path.exists(resume_path):
        raise FileNotFoundError("resume.txt not found. Please ensure resume upload writes to this file.")

    with open(resume_path, "r") as f:
        resume_text = f.read()

    # Fetch and score jobs
    jobs = fetch_jobs(role, locations, pages=1)
    if not jobs:
        console.log("[red]❌ No jobs found. Exiting.[/red]")
        return

    scored = score_all_jobs(jobs, resume_text)

    # Save CSV
    df = pd.DataFrame(scored)
    df.sort_values(by="Match %", ascending=False, inplace=True)
    df.to_csv("jobs_scored.csv", index=False)
    console.log("[bold green]✅ Saved jobs_scored.csv[/bold green]")

    # Summary table
    filtered = df[df["Match %"] >= 70]
    if not filtered.empty:
        table = Table(title="Top Matching Jobs")
        table.add_column("Title", style="cyan", no_wrap=True)
        table.add_column("Company", style="magenta")
        table.add_column("Location", style="green")
        table.add_column("Match %", justify="right", style="bold yellow")

        for _, j in filtered.head(5).iterrows():
            table.add_row(j["Title"], j["Company"], j["Location"], str(j["Match %"]))
        console.print(table)
    else:
        console.log("[yellow]No jobs above 70% match threshold.[/yellow]")


if __name__ == "__main__":
    main()
