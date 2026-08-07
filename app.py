import streamlit as st
import pandas as pd
import plotly.express as px
import oracledb
import os
import base64
import zipfile
import io
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Job Market Dashboard", layout="wide")


def get_secret(key):
    """Works both locally (.env) and on Streamlit Cloud (st.secrets)."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


def ensure_wallet():
    """Unpacks the wallet from a base64 secret, only on Streamlit Cloud.
    Locally, the oracle_wallet folder already exists, so this does nothing."""
    if os.path.exists("oracle_wallet/tnsnames.ora"):
        return

    wallet_b64 = get_secret("WALLET_B64")
    if not wallet_b64:
        raise RuntimeError("WALLET_B64 secret not found.")

    wallet_b64 = wallet_b64.strip().replace("\n", "").replace("\r", "")
    wallet_bytes = base64.b64decode(wallet_b64)

    os.makedirs("oracle_wallet", exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(wallet_bytes)) as z:
        z.extractall("oracle_wallet")


ensure_wallet()


@st.cache_data(ttl=3600)
def load_postings():
    connection = oracledb.connect(
        user=get_secret("ORACLE_USER"),
        password=get_secret("ORACLE_PASSWORD"),
        dsn=get_secret("ORACLE_DSN"),
        config_dir="oracle_wallet",
        wallet_location="oracle_wallet",
        wallet_password=get_secret("ORACLE_WALLET_PASSWORD")
    )
    query = """
        SELECT job_id, title, company, country, source, url,
               salary_min, salary_max, posted_date, collected_date
        FROM job_postings
    """
    df = pd.read_sql(query, con=connection)
    connection.close()
    return df


@st.cache_data(ttl=3600)
def load_skills():
    connection = oracledb.connect(
        user=get_secret("ORACLE_USER"),
        password=get_secret("ORACLE_PASSWORD"),
        dsn=get_secret("ORACLE_DSN"),
        config_dir="oracle_wallet",
        wallet_location="oracle_wallet",
        wallet_password=get_secret("ORACLE_WALLET_PASSWORD")
    )
    query = """
        SELECT jp.job_id, jp.country, jp.source, s.skill_name
        FROM posting_skills ps
        JOIN job_postings jp ON ps.job_id = jp.job_id
        JOIN skills s ON ps.skill_id = s.skill_id
    """
    df = pd.read_sql(query, con=connection)
    connection.close()
    return df


postings = load_postings()
skills = load_skills()

st.title("📊 Job Market Dashboard")
st.caption("Data analyst / BI job postings collected daily via an automated pipeline — Adzuna + RemoteOK + Remotive → Oracle Autonomous DB → Streamlit")

# --- Top-level metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Postings", len(postings))
col2.metric("Countries", postings["COUNTRY"].nunique())
col3.metric("Companies", postings["COMPANY"].nunique())
col4.metric("Latest Collection", str(postings["COLLECTED_DATE"].max()))

# --- Country filter (applies to everything below) ---
country_list = sorted(postings["COUNTRY"].unique())
selected_countries = st.multiselect("Filter by country", country_list, default=country_list)

filtered_postings = postings[postings["COUNTRY"].isin(selected_countries)]
filtered_skills = skills[skills["COUNTRY"].isin(selected_countries)]

# --- Top skills chart ---
st.subheader("Most In-Demand Skills")
skill_counts = (
    filtered_skills.groupby("SKILL_NAME")["JOB_ID"]
    .nunique()
    .reset_index(name="POSTING_COUNT")
    .sort_values("POSTING_COUNT", ascending=False)
    .head(15)
)
fig_skills = px.bar(
    skill_counts, x="POSTING_COUNT", y="SKILL_NAME", orientation="h",
    labels={"POSTING_COUNT": "Number of Postings", "SKILL_NAME": "Skill"}
)
fig_skills.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig_skills, width="stretch")

# --- Postings by source and country ---
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Postings by Source")
    source_counts = filtered_postings["SOURCE"].value_counts().reset_index()
    source_counts.columns = ["SOURCE", "COUNT"]
    fig_source = px.pie(source_counts, names="SOURCE", values="COUNT")
    st.plotly_chart(fig_source, width="stretch")

with col_b:
    st.subheader("Postings by Country")
    country_counts = filtered_postings["COUNTRY"].value_counts().reset_index()
    country_counts.columns = ["COUNTRY", "COUNT"]
    fig_country = px.bar(country_counts, x="COUNTRY", y="COUNT")
    st.plotly_chart(fig_country, width="stretch")

# --- Postings collected over time ---
st.subheader("Postings Collected Over Time")
daily_counts = (
    filtered_postings.groupby("COLLECTED_DATE")["JOB_ID"]
    .count()
    .reset_index(name="COUNT")
    .sort_values("COLLECTED_DATE")
)
fig_trend = px.line(daily_counts, x="COLLECTED_DATE", y="COUNT", markers=True)
st.plotly_chart(fig_trend, width="stretch")
if len(daily_counts) < 5:
    st.info("Trend is still thin — this fills in as the daily automation collects more days of data.")

# --- Salary distribution (where available) ---
st.subheader("Salary Range (where reported)")
salary_df = filtered_postings.dropna(subset=["SALARY_MIN", "SALARY_MAX"])
if len(salary_df) > 0:
    fig_salary = px.histogram(salary_df, x="SALARY_MIN", nbins=30, color="COUNTRY")
    st.plotly_chart(fig_salary, width="stretch")
else:
    st.info("No postings in the current filter have salary data — Adzuna and RemoteOK often omit it.")

# --- Raw postings table ---
st.subheader("Browse Postings")
st.dataframe(
    filtered_postings[["TITLE", "COMPANY", "COUNTRY", "SOURCE", "SALARY_MIN", "SALARY_MAX", "POSTED_DATE", "URL"]]
    .sort_values("POSTED_DATE", ascending=False)
    .reset_index(drop=True)
)