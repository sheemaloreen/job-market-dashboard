import requests
import os
from dotenv import load_dotenv

load_dotenv()

app_id = os.getenv("ADZUNA_APP_ID")
app_key = os.getenv("ADZUNA_APP_KEY")

url = f"https://api.adzuna.com/v1/api/jobs/gb/search/1"
params = {
    "app_id": app_id,
    "app_key": app_key,
    "results_per_page": 5,
    "what": "data analyst"
}

response = requests.get(url, params=params)
print("Status code:", response.status_code)

data = response.json()
print("Total results available:", data.get("count"))

for job in data.get("results", []):
    print("-", job.get("title"), "|", job.get("company", {}).get("display_name"))