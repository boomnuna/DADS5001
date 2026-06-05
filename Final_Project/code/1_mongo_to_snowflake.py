"""
STEP 1: ดึงข้อมูลจาก MongoDB Atlas แล้วโหลดเข้า Snowflake
รันไฟล์นี้ครั้งเดียวเพื่อเตรียมข้อมูล

วิธีรัน: python 1_mongo_to_snowflake.py
"""

from pymongo import MongoClient
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import toml
import os

# ============================================================
# 🔧 อ่านค่าจาก .streamlit/secrets.toml
# ============================================================

secrets = toml.load(".streamlit/secrets.toml")

MONGO_URI        = secrets["MONGO_URI"]
MONGO_DB         = secrets["MONGO_DB"]
MONGO_COLLECTION = secrets["MONGO_COLLECTION"]

SNOWFLAKE_USER      = secrets["SNOWFLAKE_USER"]
SNOWFLAKE_PASSWORD  = secrets["SNOWFLAKE_PASSWORD"]
SNOWFLAKE_ACCOUNT   = secrets["SNOWFLAKE_ACCOUNT"]
SNOWFLAKE_WAREHOUSE = secrets["SNOWFLAKE_WAREHOUSE"]
SNOWFLAKE_DATABASE  = secrets["SNOWFLAKE_DATABASE"]
SNOWFLAKE_SCHEMA    = secrets["SNOWFLAKE_SCHEMA"]

# ============================================================
# STEP 1: ดึงข้อมูลจาก MongoDB
# ============================================================
print("📦 กำลังดึงข้อมูลจาก MongoDB...")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]

data = list(collection.find({}, {"_id": 0}))
df_raw = pd.DataFrame(data)

print(f"✅ ดึงข้อมูลได้ {len(df_raw)} rows")
print(f"📋 Columns: {df_raw.columns.tolist()}")

# ============================================================
# STEP 2: Clean & Flatten ข้อมูล
# ============================================================
print("\n🧹 กำลัง clean ข้อมูล...")

df = pd.DataFrame()

# --- ฟิลด์พื้นฐาน ---
simple_fields = [
    "name", "listing_url", "description", "room_type",
    "accommodates", "bathrooms", "bedrooms", "beds",
    "number_of_reviews", "availability_365"
]
for field in simple_fields:
    if field in df_raw.columns:
        df[field.upper()] = df_raw[field]

# --- Price: แปลงจาก string "$120.00" → float ---
if "price" in df_raw.columns:
    df["PRICE"] = (
        df_raw["price"]
        .astype(str)
        .str.replace(r'[\$,]', '', regex=True)
        .replace('nan', None)
    )
    df["PRICE"] = pd.to_numeric(df["PRICE"], errors="coerce")

# --- Review scores ---
if "review_scores" in df_raw.columns:
    df["REVIEW_SCORE_RATING"] = df_raw["review_scores"].apply(
        lambda x: x.get("review_scores_rating") if isinstance(x, dict) else None
    )

# --- Location จาก nested address ---
if "address" in df_raw.columns:
    df["COUNTRY"] = df_raw["address"].apply(
        lambda x: x.get("country") if isinstance(x, dict) else None
    )
    df["CITY"] = df_raw["address"].apply(
        lambda x: x.get("market") if isinstance(x, dict) else None
    )
    df["NEIGHBOURHOOD"] = df_raw["address"].apply(
        lambda x: x.get("suburb") if isinstance(x, dict) else None
    )
    df["LATITUDE"] = df_raw["address"].apply(
        lambda x: x.get("location", {}).get("coordinates", [None, None])[1]
        if isinstance(x, dict) else None
    )
    df["LONGITUDE"] = df_raw["address"].apply(
        lambda x: x.get("location", {}).get("coordinates", [None, None])[0]
        if isinstance(x, dict) else None
    )

# --- Host info ---
if "host" in df_raw.columns:
    df["HOST_NAME"] = df_raw["host"].apply(
        lambda x: x.get("host_name") if isinstance(x, dict) else None
    )
    df["HOST_IS_SUPERHOST"] = df_raw["host"].apply(
        lambda x: x.get("host_is_superhost") if isinstance(x, dict) else None
    )

print(f"✅ Clean เสร็จ — {len(df)} rows, {len(df.columns)} columns")
print(f"📋 Columns: {df.columns.tolist()}")

# ============================================================
# STEP 3: โหลดเข้า Snowflake
# ============================================================
print("\n❄️  กำลังโหลดเข้า Snowflake...")

conn = snowflake.connector.connect(
    user=SNOWFLAKE_USER,
    password=SNOWFLAKE_PASSWORD,
    account=SNOWFLAKE_ACCOUNT,
    warehouse=SNOWFLAKE_WAREHOUSE,
    database=SNOWFLAKE_DATABASE,
    schema=SNOWFLAKE_SCHEMA
)

# สร้าง Table
create_table_sql = """
CREATE OR REPLACE TABLE LISTINGS (
    NAME STRING,
    LISTING_URL STRING,
    DESCRIPTION STRING,
    ROOM_TYPE STRING,
    ACCOMMODATES INT,
    BATHROOMS FLOAT,
    BEDROOMS FLOAT,
    BEDS FLOAT,
    NUMBER_OF_REVIEWS INT,
    AVAILABILITY_365 INT,
    PRICE FLOAT,
    REVIEW_SCORE_RATING FLOAT,
    COUNTRY STRING,
    CITY STRING,
    NEIGHBOURHOOD STRING,
    LATITUDE FLOAT,
    LONGITUDE FLOAT,
    HOST_NAME STRING,
    HOST_IS_SUPERHOST BOOLEAN
)
"""
conn.cursor().execute(create_table_sql)
print("✅ สร้าง Table LISTINGS เรียบร้อย")

# Upload DataFrame
success, nchunks, nrows, _ = write_pandas(conn, df, "LISTINGS")
print(f"✅ โหลดข้อมูลเข้า Snowflake สำเร็จ — {nrows} rows")

conn.close()
client.close()
print("\n🎉 เสร็จสิ้น! พร้อมรัน dashboard แล้ว")
