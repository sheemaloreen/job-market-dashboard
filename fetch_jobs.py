import requests
import os
import re
import time
import oracledb
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

# --- Skill list to search for in job descriptions ---
SKILL_PATTERNS = {
    "SQL": [r"\bsql\b"],
    "Python": [r"\bpython\b"],
    "Excel": [r"\bexcel\b"],
    "Tableau": [r"\btableau\b"],
    "Power BI": [r"\bpower\s*bi\b"],
    "R": [r"\br\b", r"\br language\b"],
    "AWS": [r"\baws\b", r"\bamazon web services\b"],
    "Azure": [r"\bazure\b", r"\bmicrosoft azure\b"],
    "GCP": [r"\bgcp\b", r"\bgoogle cloud\b"],
    "Scrum": [r"\bscrum\b"],
    "Agile": [r"\bagile\b"],
    "Java": [r"\bjava\b"],
    "JavaScript": [r"\bjavascript\b"],
    "Machine Learning": [r"\bmachine learning\b"],
    "Statistics": [r"\bstatistics\b", r"\bstatistical\b"],
    "Pandas": [r"\bpandas\b"],
    "NumPy": [r"\bnumpy\b"],
    "Spark": [r"\bspark\b", r"\bapache spark\b"],
    "Hadoop": [r"\bhadoop\b"],
    "ETL": [r"\betl\b"],
    "PowerPoint": [r"\bpowerpoint\b"]
}


def extract_skills(text):
    if not text:
        return []

    found = []
    text = text.lower()

    for skill, patterns in SKILL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                found.append(skill)
                break

    return found


# --- Adzuna collection (single country per call) ---
def fetch_adzuna(query="data analyst", country="gb", pages=1):
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")

    jobs = []

    for page in range(1, pages + 1):
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"

        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": 20,
            "what": query
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  Error fetching '{query}' ({country}) page {page} from Adzuna: {e}")
            continue

        for job in data.get("results", []):
            jobs.append({
                "job_id": f"adzuna_{job.get('id')}",
                "title": job.get("title", "")[:200],
                "company": (job.get("company", {}).get("display_name") or "")[:200],
                "country": country,
                "source": "adzuna",
                "url": job.get("redirect_url", "")[:500],
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "posted_date": job.get("created", "")[:10] if job.get("created") else None,
                "description": job.get("description", "")
            })

        # be polite to the API and keep calls spaced out
        time.sleep(0.5)

    return jobs


# --- RemoteOK collection ---
JOB_KEYWORDS = [
    "data analyst", "business analyst", "bi analyst", "reporting analyst",
    "analytics analyst", "data analytics", "business intelligence",
    "sql", "sql developer", "database", "database developer",
    "database administrator", "dba", "data engineer", "etl",
    "etl developer", "data warehouse", "data warehouse developer",
    "tableau", "power bi", "bi developer", "report developer",
    "python", "python developer",
    "data scientist", "machine learning", "ml engineer", "ai engineer",
    "qa", "quality assurance", "software tester", "test engineer", "qa analyst",
    "junior data", "graduate data", "junior analyst", "data associate", "research analyst"
]


def fetch_remoteok():
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"  Error fetching RemoteOK: {e}")
        return []

    jobs = []

    for job in data:
        if not isinstance(job, dict) or "id" not in job:
            continue  # first item is often metadata, not a real job

        position = job.get("position") or ""
        description = job.get("description") or ""
        search_text = f"{position} {description}".lower()

        if not any(keyword in search_text for keyword in JOB_KEYWORDS):
            continue

        jobs.append({
            "job_id": f"remoteok_{job.get('id')}",
            "title": position[:200],
            "company": (job.get("company") or "")[:200],
            "country": "remote",
            "source": "remoteok",
            "url": f"https://remoteok.com/remote-jobs/{job.get('id')}"[:500],
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
            "posted_date": None,
            "description": description
        })

    return jobs

# --- Remotive collection ---
def fetch_remotive():
    url = "https://remotive.com/api/remote-jobs"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"  Error fetching Remotive: {e}")
        return []

    jobs = []
    for job in data.get("jobs", []):
        title = job.get("title") or ""
        description = job.get("description") or ""
        search_text = f"{title} {description}".lower()

        if not any(keyword in search_text for keyword in JOB_KEYWORDS):
            continue

        posted_date = None
        raw_date = job.get("publication_date")
        if raw_date:
            try:
                posted_date = datetime.fromisoformat(raw_date).strftime("%Y-%m-%d")
            except ValueError:
                posted_date = None

        jobs.append({
            "job_id": f"remotive_{job.get('id')}",
            "title": title[:200],
            "company": (job.get("company_name") or "")[:200],
            "country": "remote",
            "source": "remotive",
            "url": (job.get("url") or "")[:500],
            "salary_min": None,   # Remotive gives a free-text salary string, not min/max
            "salary_max": None,
            "posted_date": posted_date,
            "description": description
        })

    return jobs


# --- Run collection ---
SEARCH_QUERIES = [
    "Data Analyst",
    "Business Analyst",
    "BI Analyst",
    "Junior Data Analyst",
    "Business Intelligence",
    "SQL Developer",
    "Database Administrator",
    "Data Engineer",
    "ETL Developer",
    "Power BI Developer",
    "Tableau Developer",
    "Python Developer",
    "Data Scientist",
    "Machine Learning Engineer",
    "QA Analyst"
]

COUNTRIES = ["gb", "us"]

adzuna_jobs = []
print("Fetching Adzuna jobs...")

for country in COUNTRIES:
    for query in SEARCH_QUERIES:
        jobs = fetch_adzuna(query=query, country=country, pages=1)  # 15 queries x 2 countries = 30 calls
        print(f"  [{country}] {query}: {len(jobs)} jobs")
        adzuna_jobs.extend(jobs)

print(f"Total Adzuna jobs: {len(adzuna_jobs)}")

print("\nFetching RemoteOK jobs...")
remoteok_jobs = fetch_remoteok()
print(f"RemoteOK: {len(remoteok_jobs)} jobs")

print("\nFetching Remotive jobs...")
remotive_jobs = fetch_remotive()
print(f"Remotive: {len(remotive_jobs)} jobs")

all_jobs = adzuna_jobs + remoteok_jobs + remotive_jobs
print(f"\nTotal collected: {len(all_jobs)}")

# --- Connect to Oracle ---
connection = oracledb.connect(
    user=os.getenv("ORACLE_USER"),
    password=os.getenv("ORACLE_PASSWORD"),
    dsn=os.getenv("ORACLE_DSN"),
    config_dir="oracle_wallet",
    wallet_location="oracle_wallet",
    wallet_password=os.getenv("ORACLE_WALLET_PASSWORD")
)
cursor = connection.cursor()

collected_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
inserted_count = 0
skipped_count = 0
error_count = 0

for job in all_jobs:
    try:
        # Skip if this job posting already exists (avoid duplicate errors on reruns)
        cursor.execute("SELECT COUNT(*) FROM job_postings WHERE job_id = :job_id", job_id=job["job_id"])
        if cursor.fetchone()[0] > 0:
            skipped_count += 1
            continue

        cursor.execute("""
            INSERT INTO job_postings
                (job_id, title, company, country, source, url,
                 salary_min, salary_max, posted_date, collected_date, description)
            VALUES
                (:job_id, :title, :company, :country, :source, :url,
                 :salary_min, :salary_max,
                 TO_DATE(:posted_date, 'YYYY-MM-DD'),
                 TO_DATE(:collected_date, 'YYYY-MM-DD'),
                 :description)
        """,
            job_id=job["job_id"], title=job["title"], company=job["company"],
            country=job["country"], source=job["source"], url=job["url"],
            salary_min=job["salary_min"], salary_max=job["salary_max"],
            posted_date=job["posted_date"], collected_date=collected_date,
            description=job["description"]
        )

        # Extract and link skills
        skills_found = extract_skills(job["description"])
        for skill in skills_found:
            cursor.execute("""
                MERGE INTO skills s
                USING (SELECT :skill_name AS skill_name FROM dual) src
                ON (s.skill_name = src.skill_name)
                WHEN NOT MATCHED THEN INSERT (skill_name) VALUES (:skill_name)
            """, skill_name=skill)

            cursor.execute("""
                INSERT INTO posting_skills (job_id, skill_id)
                SELECT :job_id, skill_id FROM skills WHERE skill_name = :skill_name
            """, job_id=job["job_id"], skill_name=skill)

        inserted_count += 1

    except oracledb.Error as e:
        error_count += 1
        print(f"  Skipping job {job.get('job_id')} due to DB error: {e}")
        connection.rollback()
        continue

connection.commit()
print(f"\nInserted {inserted_count} new job postings.")
print(f"Skipped {skipped_count} duplicates.")
print(f"Errored on {error_count} jobs.")

cursor.close()
connection.close()