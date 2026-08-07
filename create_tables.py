import oracledb
import os
from dotenv import load_dotenv

load_dotenv()

connection = oracledb.connect(
    user=os.getenv("ORACLE_USER"),
    password=os.getenv("ORACLE_PASSWORD"),
    dsn=os.getenv("ORACLE_DSN"),
    config_dir="oracle_wallet",
    wallet_location="oracle_wallet",
    wallet_password=os.getenv("ORACLE_WALLET_PASSWORD")
)

cursor = connection.cursor()

cursor.execute("""
CREATE TABLE job_postings (
    job_id VARCHAR2(100) PRIMARY KEY,
    title VARCHAR2(200),
    company VARCHAR2(200),
    country VARCHAR2(10),
    source VARCHAR2(20),
    url VARCHAR2(500),
    salary_min NUMBER,
    salary_max NUMBER,
    posted_date DATE,
    collected_date DATE
)
""")

cursor.execute("""
CREATE TABLE skills (
    skill_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    skill_name VARCHAR2(50) UNIQUE
)
""")

cursor.execute("""
CREATE TABLE posting_skills (
    job_id VARCHAR2(100) REFERENCES job_postings(job_id),
    skill_id NUMBER REFERENCES skills(skill_id),
    PRIMARY KEY (job_id, skill_id)
)
""")

connection.commit()
print("Tables created successfully.")

cursor.close()
connection.close()