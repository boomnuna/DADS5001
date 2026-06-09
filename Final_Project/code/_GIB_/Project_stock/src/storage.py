from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.config import USER_ID


@st.cache_resource(show_spinner=False)
def get_mongo_client():
    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        return None
    try:
        from pymongo import MongoClient

        return MongoClient(uri, serverSelectionTimeoutMS=3000)
    except Exception:
        return None


def save_watchlist_to_mongo(tickers: list[str]) -> str:
    client = get_mongo_client()
    if client is None:
        return "Demo mode: MongoDB is not connected. Watchlist stays in Streamlit session."

    db_name = os.getenv("MONGODB_DATABASE", "ai_stock_demo")
    db = client[db_name]
    payload = {
        "user_id": USER_ID,
        "tickers": tickers,
        "updated_at": datetime.now(timezone.utc),
    }
    db.watchlists.update_one({"user_id": USER_ID}, {"$set": payload}, upsert=True)
    db.search_history.insert_one(
        {
            "user_id": USER_ID,
            "tickers": tickers,
            "searched_at": datetime.now(timezone.utc),
        }
    )
    return "Saved watchlist and search history to MongoDB."


@st.cache_resource(show_spinner=False)
def get_snowflake_connection():
    required = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
    ]
    if not all(os.getenv(key) for key in required):
        return None
    try:
        import snowflake.connector

        return snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
        )
    except Exception:
        return None


def snowflake_status() -> str:
    return (
        "Snowflake connected."
        if get_snowflake_connection() is not None
        else "Demo mode: Snowflake is not connected. Tables are represented as Pandas DataFrames."
    )


def build_snowflake_demo_tables(
    prices: pd.DataFrame,
    technical: pd.DataFrame,
    predictions: pd.DataFrame,
    ai_result: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    return {
        "STOCK_PRICES": prices.copy(),
        "TECHNICAL_METRICS": technical[
            ["date", "ticker", "ma20", "ma50", "rsi", "macd", "macd_signal", "bb_upper", "bb_lower"]
        ].copy(),
        "ML_PREDICTIONS": predictions.copy(),
        "AI_SENTIMENT": ai_result.copy(),
    }

