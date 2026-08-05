import os
from dotenv import load_dotenv

load_dotenv()

# ---------- 1) 测试 Snowflake ----------
import snowflake.connector

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    password=os.environ["SNOWFLAKE_PASSWORD"],
    warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    database="US_OPEN_CENSUS",
    schema="PUBLIC",
)
cur = conn.cursor()
cur.execute('''
    SELECT SUM("B01001e1") AS ca_population
    FROM US_OPEN_CENSUS.PUBLIC."2019_CBG_B01"
    WHERE LEFT("CENSUS_BLOCK_GROUP", 2) = '06'
''')
row = cur.fetchone()
print(f"[Snowflake] California population = {row[0]:,}")
cur.close()
conn.close()

# ---------- 2) 测试 Gemini ----------
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
resp = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Reply with exactly: Gemini is working",
)
print(f"[Gemini] {resp.text.strip()}")