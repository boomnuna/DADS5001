"""
src/storage.py
MongoDB — เก็บ Watchlist, Search History
Snowflake — เก็บ Price, Indicators, Predictions, AI Sentiment
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.config import USER_ID


# ════════════════════════════════════════════════════════════════════════════
# MongoDB
# ════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_mongo_client():
    try:
        from pymongo import MongoClient
        uri = st.secrets.get("MONGO_URI", "")
        if not uri:
            return None
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client
    except Exception as e:
        st.warning(f"MongoDB: {e}")
        return None


def _get_mongo_db():
    client = get_mongo_client()
    if client is None:
        return None
    return client[st.secrets.get("MONGO_DB", "ai_stock_db")]


def save_watchlist(tickers: list[str]) -> str:
    """บันทึก watchlist + search history ลง MongoDB"""
    db = _get_mongo_db()
    if db is None:
        return "⚠️ Demo mode: MongoDB ไม่ได้เชื่อมต่อ"
    now = datetime.now(timezone.utc)
    db.watchlists.update_one(
        {"user_id": USER_ID},
        {"$set": {"tickers": tickers, "updated_at": now}},
        upsert=True,
    )
    db.search_history.insert_one({
        "user_id":     USER_ID,
        "tickers":     tickers,
        "searched_at": now,
    })
    return f"✅ บันทึก Watchlist {tickers} ลง MongoDB แล้ว"


def load_watchlist() -> list[str]:
    """โหลด watchlist จาก MongoDB"""
    db = _get_mongo_db()
    if db is None:
        return []
    doc = db.watchlists.find_one({"user_id": USER_ID})
    return doc.get("tickers", []) if doc else []


def load_search_history(limit: int = 10) -> list[dict]:
    """โหลดประวัติการค้นหา"""
    db = _get_mongo_db()
    if db is None:
        return []
    cursor = db.search_history.find(
        {"user_id": USER_ID},
        sort=[("searched_at", -1)],
        limit=limit
    )
    return [{"tickers": d["tickers"], "time": d["searched_at"]} for d in cursor]


# ════════════════════════════════════════════════════════════════════════════
# Snowflake
# ════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_snowflake_conn():
    try:
        import snowflake.connector
        sf = st.secrets["snowflake"]
        conn = snowflake.connector.connect(
            account   = sf["account"],
            user      = sf["user"],
            password  = sf["password"],
            warehouse = sf["warehouse"],
            database  = sf["database"],
            schema    = sf["schema"],
        )
        return conn
    except Exception as e:
        st.warning(f"Snowflake: {e}")
        return None


def _sf_execute(sql: str, params: list | None = None) -> bool:
    conn = get_snowflake_conn()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.warning(f"Snowflake execute: {e}")
        return False


def _sf_query(sql: str, params: list | None = None) -> pd.DataFrame:
    conn = get_snowflake_conn()
    if conn is None:
        return pd.DataFrame()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        df = cur.fetch_pandas_all()
        cur.close()
        return df
    except Exception as e:
        st.warning(f"Snowflake query: {e}")
        return pd.DataFrame()


def setup_snowflake_tables() -> None:
    """สร้างตารางใน Snowflake ถ้ายังไม่มี"""
    _sf_execute("""
        CREATE TABLE IF NOT EXISTS stock_prices (
            id          STRING DEFAULT UUID_STRING(),
            ticker      STRING,
            price_date  DATE,
            open_price  FLOAT,
            high_price  FLOAT,
            low_price   FLOAT,
            close_price FLOAT,
            volume      BIGINT,
            saved_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)
    _sf_execute("""
        CREATE TABLE IF NOT EXISTS technical_metrics (
            id               STRING DEFAULT UUID_STRING(),
            ticker           STRING,
            metric_date      DATE,
            ma20             FLOAT,
            ma50             FLOAT,
            rsi              FLOAT,
            macd             FLOAT,
            macd_signal      FLOAT,
            bb_upper         FLOAT,
            bb_lower         FLOAT,
            technical_score  FLOAT,
            technical_signal STRING,
            saved_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)
    _sf_execute("""
        CREATE TABLE IF NOT EXISTS ml_predictions (
            id               STRING DEFAULT UUID_STRING(),
            ticker           STRING,
            prediction_date  DATE DEFAULT CURRENT_DATE(),
            probability_up   FLOAT,
            prediction_score FLOAT,
            predicted_label  STRING,
            model_name       STRING,
            backtest_acc     FLOAT,
            saved_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)
    _sf_execute("""
        CREATE TABLE IF NOT EXISTS ai_sentiment (
            id               STRING DEFAULT UUID_STRING(),
            ticker           STRING,
            analysis_date    DATE DEFAULT CURRENT_DATE(),
            sentiment_label  STRING,
            sentiment_score  FLOAT,
            recommendation   STRING,
            combined_score   FLOAT,
            ai_summary       STRING,
            saved_at         TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)


def save_prices_to_snowflake(prices: pd.DataFrame) -> bool:
    """บันทึกราคาหุ้นล่าสุดลง Snowflake"""
    if prices.empty:
        return False
    conn = get_snowflake_conn()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        # บันทึกเฉพาะ 30 วันล่าสุดของแต่ละหุ้น
        recent = prices.sort_values("date").groupby("ticker").tail(30)
        for _, row in recent.iterrows():
            cur.execute("""
                INSERT INTO stock_prices (ticker, price_date, open_price, high_price, low_price, close_price, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [
                row["ticker"], str(row["date"])[:10],
                row["open"], row["high"], row["low"], row["close"], int(row["volume"]),
            ])
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.warning(f"Save prices error: {e}")
        return False


def save_analysis_to_snowflake(
    technical:   pd.DataFrame,
    predictions: pd.DataFrame,
    ai_result:   pd.DataFrame,
) -> bool:
    """บันทึกผลวิเคราะห์ลง Snowflake"""
    conn = get_snowflake_conn()
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        # Technical
        for _, row in technical.iterrows():
            cur.execute("""
                INSERT INTO technical_metrics
                    (ticker, metric_date, ma20, ma50, rsi, macd_signal, bb_upper, bb_lower, technical_score, technical_signal)
                VALUES (%s, CURRENT_DATE(), %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                row["ticker"], row.get("ma20"), row.get("ma50"),
                row.get("rsi"), row.get("macd_score"), row.get("bb_upper"),
                row.get("bb_lower"), row.get("technical_score"), row.get("technical_signal"),
            ])
        # Predictions
        for _, row in predictions.iterrows():
            cur.execute("""
                INSERT INTO ml_predictions (ticker, probability_up, prediction_score, predicted_label, model_name, backtest_acc)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [
                row["ticker"], row.get("probability_up"), row.get("prediction_score"),
                row.get("predicted_label"), row.get("model_name"), row.get("backtest_accuracy"),
            ])
        # AI Sentiment
        if not ai_result.empty:
            for _, row in ai_result.iterrows():
                cur.execute("""
                    INSERT INTO ai_sentiment (ticker, sentiment_label, sentiment_score, recommendation, combined_score, ai_summary)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [
                    row["ticker"], row.get("sentiment_label"), row.get("sentiment_score"),
                    row.get("recommendation"), row.get("combined_score"),
                    str(row.get("ai_summary", ""))[:500],
                ])
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.warning(f"Save analysis error: {e}")
        return False


def load_snowflake_history(ticker: str, days: int = 30) -> pd.DataFrame:
    """โหลดประวัติ prediction จาก Snowflake"""
    return _sf_query("""
        SELECT ticker, prediction_date, prediction_score, predicted_label, recommendation
        FROM (
            SELECT p.ticker, p.prediction_date, p.prediction_score, p.predicted_label, a.recommendation
            FROM ml_predictions p
            LEFT JOIN ai_sentiment a ON p.ticker = a.ticker AND p.prediction_date = a.analysis_date
            WHERE p.ticker = %s
        )
        ORDER BY prediction_date DESC
        LIMIT %s
    """, [ticker, days])


def mongo_status() -> str:
    client = get_mongo_client()
    return "✅ MongoDB เชื่อมต่อแล้ว" if client else "⚠️ MongoDB ไม่ได้เชื่อมต่อ"


def snowflake_status() -> str:
    conn = get_snowflake_conn()
    return "✅ Snowflake เชื่อมต่อแล้ว" if conn else "⚠️ Snowflake ไม่ได้เชื่อมต่อ"


# ════════════════════════════════════════════════════════════════════════════
# Analysis History (MongoDB)
# ════════════════════════════════════════════════════════════════════════════

def save_analysis_history(tickers: list[str], results: list[dict]) -> str:
    """บันทึกประวัติการวิเคราะห์ลง MongoDB"""
    db = _get_mongo_db()
    if db is None:
        return "⚠️ MongoDB ไม่ได้เชื่อมต่อ"
    now = datetime.now(timezone.utc)
    db.analysis_history.insert_one({
        "user_id":     USER_ID,
        "tickers":     tickers,
        "results":     results,
        "analyzed_at": now,
    })
    return f"✅ บันทึกประวัติการวิเคราะห์ {tickers} ลง MongoDB แล้ว"


def load_analysis_history(limit: int = 5) -> list[dict]:
    """โหลดประวัติการวิเคราะห์ล่าสุด"""
    db = _get_mongo_db()
    if db is None:
        return []
    cursor = db.analysis_history.find(
        {"user_id": USER_ID},
        sort=[("analyzed_at", -1)],
        limit=limit
    )
    return list(cursor)
