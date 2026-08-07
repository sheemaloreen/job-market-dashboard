import streamlit as st
import pandas as pd
import plotly.express as px
import oracledb
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Job Market Dashboard", layout="wide")


@st.cache_data(ttl=3600)  # cache for 1 hour so we're not hammering the DB on every click
def load_postings():
    connection = oracledb.connect(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN"),
        config_dir="oracle_wallet",
        wallet_location="oracle_wallet",
        wallet_password=os.getenv("ORACLE_WALLET_PASSWORD")
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
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=os.getenv("ORACLE_DSN"),
        config_dir="oracle_wallet",
        wallet_location="oracle_wallet",
        wallet_password=os.getenv("ORACLE_WALLET_PASSWORD")
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
st.caption("Data analyst / BI job postings collected daily via an automated pipeline — Adzuna + RemoteOK → Oracle Autonomous DB → Streamlit")

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
st.plotly_chart(fig_skills, use_container_width=True)

# --- Postings by source and country ---
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Postings by Source")
    source_counts = filtered_postings["SOURCE"].value_counts().reset_index()
    source_counts.columns = ["SOURCE", "COUNT"]
    fig_source = px.pie(source_counts, names="SOURCE", values="COUNT")
    st.plotly_chart(fig_source, use_container_width=True)

with col_b:
    st.subheader("Postings by Country")
    country_counts = filtered_postings["COUNTRY"].value_counts().reset_index()
    country_counts.columns = ["COUNTRY", "COUNT"]
    fig_country = px.bar(country_counts, x="COUNTRY", y="COUNT")
    st.plotly_chart(fig_country, use_container_width=True)

# --- Postings collected over time ---
st.subheader("Postings Collected Over Time")
daily_counts = (
    filtered_postings.groupby("COLLECTED_DATE")["JOB_ID"]
    .count()
    .reset_index(name="COUNT")
    .sort_values("COLLECTED_DATE")
)
fig_trend = px.line(daily_counts, x="COLLECTED_DATE", y="COUNT", markers=True)
st.plotly_chart(fig_trend, use_container_width=True)
if len(daily_counts) < 5:
    st.info("Trend is still thin — this fills in as the daily automation collects more days of data.")

# --- Salary distribution (where available) ---
st.subheader("Salary Range (where reported)")
salary_df = filtered_postings.dropna(subset=["SALARY_MIN", "SALARY_MAX"])
if len(salary_df) > 0:
    fig_salary = px.histogram(salary_df, x="SALARY_MIN", nbins=30, color="COUNTRY")
    st.plotly_chart(fig_salary, use_container_width=True)
else:
    st.info("No postings in the current filter have salary data — Adzuna and RemoteOK often omit it.")

# --- Raw postings table ---
st.subheader("Browse Postings")
st.dataframe(
    filtered_postings[["TITLE", "COMPANY", "COUNTRY", "SOURCE", "SALARY_MIN", "SALARY_MAX", "POSTED_DATE", "URL"]]
    .sort_values("POSTED_DATE", ascending=False)
    .reset_index(drop=True)
)