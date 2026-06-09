"""
utils/db_snowflake.py
Snowflake — เก็บ historical snapshots และ aggregated analytics
"""

import streamlit as st
import pandas as pd
import snowflake.connector
from datetime import datetime


@st.cache_resource
def get_snowflake_conn():
    """สร้าง Snowflake connection (cache_resource)"""
    try:
        sf = st.secrets["snowflake"]
        conn = snowflake.connector.connect(
            account   = sf["account"],
            user      = sf["user"],
            password  = sf["password"],
            warehouse = sf["warehouse"],
            database  = sf["database"],
            schema    = sf["schema"],
            role      = sf.get("role", "SYSADMIN"),
        )
        return conn
    except Exception as e:
        st.error(f"❌ Snowflake connection failed: {e}")
        return None


def _run_query(sql: str, params=None) -> pd.DataFrame:
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
        st.warning(f"Snowflake query error: {e}")
        return pd.DataFrame()


def _execute(sql: str, params=None) -> bool:
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
        st.warning(f"Snowflake execute error: {e}")
        return False


# ─── Setup Tables (เรียกครั้งแรก) ─────────────────────────────────────────────
def setup_tables():
    """สร้างตารางถ้ายังไม่มี"""
    _execute("""
        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            snapshot_id   STRING DEFAULT UUID_STRING(),
            user_id       STRING,
            symbol        STRING,
            qty           FLOAT,
            avg_cost      FLOAT,
            current_price FLOAT,
            market_value  FLOAT,
            pnl           FLOAT,
            pnl_pct       FLOAT,
            snapshot_date DATE DEFAULT CURRENT_DATE(),
            created_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)
    _execute("""
        CREATE TABLE IF NOT EXISTS trade_log (
            trade_id      STRING DEFAULT UUID_STRING(),
            user_id       STRING,
            symbol        STRING,
            trade_type    STRING,
            qty           FLOAT,
            price         FLOAT,
            total_value   FLOAT,
            trade_date    DATE,
            created_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)


# ─── Portfolio Snapshots ──────────────────────────────────────────────────────
def save_portfolio_snapshot(user_id: str, holdings_df: pd.DataFrame):
    """บันทึก snapshot รายวันของพอร์ต"""
    conn = get_snowflake_conn()
    if conn is None or holdings_df.empty:
        return False
    try:
        cur = conn.cursor()
        for _, row in holdings_df.iterrows():
            cur.execute("""
                INSERT INTO portfolio_snapshots
                    (user_id, symbol, qty, avg_cost, current_price, market_value, pnl, pnl_pct, snapshot_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE())
            """, (
                user_id,
                row.get("symbol"),
                row.get("qty", 0),
                row.get("avg_cost", 0),
                row.get("current_price", 0),
                row.get("market_value", 0),
                row.get("pnl", 0),
                row.get("pnl_pct", 0),
            ))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        st.warning(f"Snapshot save error: {e}")
        return False


@st.cache_data(ttl=3600)
def load_portfolio_history(user_id: str = "default", days: int = 90) -> pd.DataFrame:
    """โหลดประวัติมูลค่าพอร์ต"""
    return _run_query("""
        SELECT
            snapshot_date,
            SUM(market_value) AS total_value,
            SUM(pnl)          AS total_pnl
        FROM portfolio_snapshots
        WHERE user_id = %s
          AND snapshot_date >= DATEADD(day, -%s, CURRENT_DATE())
        GROUP BY snapshot_date
        ORDER BY snapshot_date
    """, [user_id, days])


@st.cache_data(ttl=3600)
def load_trade_log(user_id: str = "default", limit: int = 100) -> pd.DataFrame:
    """โหลด trade log จาก Snowflake"""
    return _run_query("""
        SELECT *
        FROM trade_log
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, [user_id, limit])


def save_trade_to_snowflake(user_id: str, trade: dict) -> bool:
    """บันทึก trade ลง Snowflake"""
    return _execute("""
        INSERT INTO trade_log (user_id, symbol, trade_type, qty, price, total_value, trade_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, [
        user_id,
        trade["symbol"],
        trade["trade_type"],
        trade["qty"],
        trade["price"],
        trade["total_value"],
        trade.get("trade_date", datetime.utcnow().date()),
    ])
