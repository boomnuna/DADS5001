"""
One-time script: reads the Airbnb CSV and upserts every row into MongoDB.
Run this LOCALLY (never on Streamlit Cloud).

Usage:
    pip install pymongo[srv] pandas python-dotenv
    python load_to_mongo.py
"""

import os
import pandas as pd
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

# for read .env file
load_dotenv()  

# get password from .env file 
MONGO_URI        = os.getenv("MONGO_URI", "mongodb+srv://USER:PASS@cluster.mongodb.net/")
MONGO_DB         = os.getenv("MONGO_DB",  "dataset_airbnb")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "dads_dataset")
CSV_PATH         = os.getenv("CSV_PATH",  "Airbnb_Open_Data.csv")

# preprocessing df
def preprocessing(df):
    # process "price", "service fee"
    target = ["price", "service fee"]
    for col in df.columns:
        if col in target:
            df[col] = df[col].astype(str).str.replace(r"[\$,\s]", "", regex=True).replace("nan", None) # replace $ with ''
            df[col] = pd.to_numeric(df[col], errors="coerce") # convert to numerical 
    # process "minimum nights"
    df['minimum nights'] = df['minimum nights'].clip(lower=0)
    # process "last review"
    df['last review'] = pd.to_datetime(df['last review'], errors='coerce')
    today = pd.Timestamp.today().normalize() # set timestamp to midnight 
    df.loc[df['last review'] >= today, 'last review'] = pd.NaT 
    df['last review'] = df['last review'].astype(str).replace("NaT", None)
    # process "availability 365"
    df['availability 365'] = df['availability 365'].clip(lower=0)
    return df

# main
def main():
    # read dataset
    print(f"Reading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    df = preprocessing(df)
    records = df.where(pd.notna(df), None).to_dict("records") #  replace value to none if N/A & convert to list[dict] to put to mongodb 
    print(f"{len(records)} rows loaded.")

    # create mongodb connection
    client = MongoClient(MONGO_URI)
    # select mongodb database and table
    col = client[MONGO_DB][MONGO_COLLECTION]

    #TODO: OPS operation (faster than upadate one-by-one)
    # preparing batch of data
    batch_size = 500
    ops = [] 
    num_batch = 1
    for rec in records:
        ops.append(
            UpdateOne(
                {"id": rec.get("id")}, # get 'id' value
                {"$set": rec}, 
                upsert=True) # update if exist, insert if not exist
        )
        # put to mongodb and reset
        if len(ops) == batch_size:
            col.bulk_write(ops, ordered=False)
            ops = []
            # print batch number
            if num_batch%10==0:
                print(num_batch)
            num_batch = num_batch+1

    # for last batch if it not reach batch size    
    if ops:
        col.bulk_write(ops, ordered=False)
    
    print(f"✅  Upserted {len(records):,} documents into {MONGO_DB}.{MONGO_COLLECTION}")

if __name__ == "__main__":
    main()
