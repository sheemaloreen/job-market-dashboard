# Job Market Dashboard

A pipeline I built to track what skills are actually in demand for data analyst and BI roles, by collecting real job postings every day instead of relying on a single static dataset.

**Live dashboard:** https://sheema-job-market-dashboard.streamlit.app

## What this does

I wanted to know what skills employers actually ask for in data analyst and BI job postings, across the UK, US, and remote roles — instead of guessing based on what a course covers. So I built a pipeline that pulls real job postings daily from three sources (Adzuna, RemoteOK, and Remotive), scans each posting's description for around 20 common data/analytics skills using regex matching, and stores everything in a normalized database. A GitHub Actions workflow runs this automatically every day, so the dataset keeps growing over time. The dashboard reads from that database and shows which skills come up most often, how postings break down by source and country, and salary ranges where reported.

## How it's structured
Adzuna + RemoteOK + Remotive APIs → Python (collect + extract skills) → Oracle Database → Streamlit dashboard
↑
GitHub Actions runs this daily, automatically

## A few decisions I made and why

- **Three data sources instead of one.** Adzuna alone is UK-focused, so I added RemoteOK and Remotive to get better US and remote-role coverage. Each source returns data slightly differently, so I normalized all three into the same structure before storing anything.

- **A proper many-to-many relationship for skills, not a single text column.** A job posting can require many skills, and a skill like SQL shows up in hundreds of postings. Instead of cramming a list of skills into one field, I built three tables — postings, skills, and a link table connecting them — so I can ask questions like "which skill appears in the most postings" with a simple join, instead of parsing text every time.

- **Regex with word boundaries for skill matching, not simple text search.** A plain "contains" search for the skill "R" would match inside words like "Analyst" constantly. Using word-boundary regex patterns (`\br\b`) means a skill only counts if it appears as an actual standalone word.

- **Paced data collection to respect API limits.** Adzuna's free tier only allows a limited number of calls per month, so instead of pulling everything at once, the pipeline collects a manageable batch daily. This also means the dataset naturally shows trends over time, not just a single snapshot.

- **It skips duplicates on rerun.** Since the same job posting can show up in multiple daily runs, the pipeline checks whether a posting already exists before inserting it, so the numbers stay accurate instead of double-counting the same job repeatedly.

## Tech stack

- Python, Requests, re (regex) — for pulling job data and extracting skills from descriptions
- Oracle Autonomous Database — for storage (normalized schema: postings, skills, and a link table)
- GitHub Actions — for daily automated collection
- Streamlit + Plotly — for the dashboard

## Running it yourself

```bash
git clone https://github.com/sheemaloreen/job-market-dashboard.git
cd job-market-dashboard
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

You'll need a `.env` file with:
ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_app_key
ORACLE_USER=ADMIN
ORACLE_PASSWORD=your_password
ORACLE_WALLET_PASSWORD=your_wallet_password
ORACLE_DSN=your_dsn

And your own Oracle wallet files in an `oracle_wallet/` folder. Then:
```bash
python fetch_jobs.py     # collects one day's postings manually
streamlit run app.py     # runs the dashboard locally
```

## A related project

This dashboard shares its database with my [Crypto Market Dashboard](https://github.com/sheemaloreen/crypto-market-pipeline) — both projects run on the same Oracle instance but keep completely separate tables, which turned out to be a genuinely normal, efficient way to structure things rather than spinning up a new database for every small project.

