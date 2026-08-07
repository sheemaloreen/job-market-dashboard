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
print("SUCCESS: Connected to Oracle!")
connection.close()