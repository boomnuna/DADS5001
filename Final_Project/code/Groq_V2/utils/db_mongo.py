"""
utils/db_mongo.py
MongoDB Atlas — เก็บ portfolio, watchlist, trade history
"""

import streamlit as st
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime
import pandas as pd


@st.cache_resource
def get_mongo_client():
    """สร้าง MongoClient ครั้งเดียว (cache_resource)"""
    try:
        uri = st.secrets["MONGO_URI"]
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")  # ทดสอบ connection
        return client
    except Exception as e:
        st.error(f"❌ MongoDB connection failed: {e}")
        return None


def get_db():
    client = get_mongo_client()
    if client is None:
        return None
    db_name = st.secrets.get("MONGO_DB", "tradex_db")
    return client[db_name]


# ─── Portfolio ────────────────────────────────────────────────────────────────
def save_portfolio(user_id: str, holdings: list):
    """บันทึกพอร์ตโฟลิโอ"""
    db = get_db()
    if db is None:
        return False
    db.portfolios.update_one(
        {"user_id": user_id},
        {"$set": {"holdings": holdings, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return True


def load_portfolio(user_id: str = "default") -> list:
    """โหลดพอร์ตโฟลิโอ"""
    db = get_db()
    if db is None:
        return []
    doc = db.portfolios.find_one({"user_id": user_id})
    return doc.get("holdings", []) if doc else []


# ─── Trade History ─────────────────────────────────────────────────────────────
def save_trade(trade: dict):
    """บันทึกประวัติการซื้อขาย"""
    db = get_db()
    if db is None:
        return False
    trade["created_at"] = datetime.utcnow()
    db.trades.insert_one(trade)
    return True


def load_trades(user_id: str = "default", limit: int = 50) -> pd.DataFrame:
    """โหลดประวัติการซื้อขาย"""
    db = get_db()
    if db is None:
        return pd.DataFrame()
    cursor = db.trades.find(
        {"user_id": user_id},
        sort=[("created_at", -1)],
        limit=limit
    )
    docs = list(cursor)
    if not docs:
        return pd.DataFrame()
    df = pd.DataFrame(docs)
    df.drop(columns=["_id"], errors="ignore", inplace=True)
    return df


# ─── Watchlist ────────────────────────────────────────────────────────────────
def save_watchlist(user_id: str, symbols: list):
    db = get_db()
    if db is None:
        return False
    db.watchlists.update_one(
        {"user_id": user_id},
        {"$set": {"symbols": symbols, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return True


def load_watchlist(user_id: str = "default") -> list:
    db = get_db()
    if db is None:
        return ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]
    doc = db.watchlists.find_one({"user_id": user_id})
    return doc.get("symbols", ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]) if doc else ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]


# ─── AI Analysis Cache ────────────────────────────────────────────────────────
def save_ai_analysis(symbol: str, analysis: dict):
    """เก็บผล AI analysis ใน MongoDB (cache ใน cloud)"""
    db = get_db()
    if db is None:
        return False
    db.ai_cache.update_one(
        {"symbol": symbol},
        {"$set": {"analysis": analysis, "created_at": datetime.utcnow()}},
        upsert=True,
    )
    return True


def load_ai_analysis(symbol: str, max_age_hours: int = 6) -> dict | None:
    """โหลด AI analysis (ถ้าไม่เก่าเกินไป)"""
    db = get_db()
    if db is None:
        return None
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    doc = db.ai_cache.find_one(
        {"symbol": symbol, "created_at": {"$gt": cutoff}}
    )
    return doc.get("analysis") if doc else None
