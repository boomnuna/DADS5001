"""
utils/data_fetcher.py
ดึงข้อมูลหุ้นจาก Yahoo Finance ผ่าน yfinance
ใช้ st.cache_data และ st.cache_resource ตามโจทย์
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import duckdb
import numpy as np
from datetime import datetime, timedelta


# ─── DuckDB in-memory (shared via cache_resource) ─────────────────────────────
@st.cache_resource
def get_duckdb_conn():
    """สร้าง DuckDB connection ครั้งเดียว reuse ทุก session"""
    conn = duckdb.connect(database=":memory:", read_only=False)
    return conn


# ─── yfinance Ticker object (cache_resource = object ไม่ serialize) ───────────
@st.cache_resource
def get_ticker(symbol: str):
    """Cache yfinance Ticker object"""
    return yf.Ticker(symbol.upper())


# ─── ราคาหุ้น historical (cache_data = serialize ได้, expire 15 นาที) ─────────
@st.cache_data(ttl=900)
def get_price_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    ดึงราคาหุ้นย้อนหลัง
    period: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    """
    ticker = yf.Ticker(symbol.upper())
    df = ticker.history(period=period)
    if df.empty:
        return pd.DataFrame()
    df.index = df.index.tz_localize(None)
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    return df


@st.cache_data(ttl=900)
def get_current_price(symbol: str) -> dict:
    """ดึงราคาปัจจุบัน + ข้อมูลพื้นฐาน"""
    ticker = yf.Ticker(symbol.upper())
    info = ticker.info
    fast = ticker.fast_info

    try:
        current = fast.last_price or info.get("currentPrice", 0)
        prev_close = fast.previous_close or info.get("previousClose", current)
        change = current - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0
    except Exception:
        current, change, change_pct = 0, 0, 0

    return {
        "symbol": symbol.upper(),
        "name": info.get("longName", symbol),
        "price": round(current, 2),
        "change": round(change, 2),
        "change_pct": round(change_pct, 2),
        "market_cap": info.get("marketCap", 0),
        "pe_ratio": info.get("trailingPE", None),
        "eps": info.get("trailingEps", None),
        "52w_high": info.get("fiftyTwoWeekHigh", None),
        "52w_low": info.get("fiftyTwoWeekLow", None),
        "volume": info.get("volume", 0),
        "avg_volume": info.get("averageVolume", 0),
        "dividend_yield": info.get("dividendYield", None),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "description": info.get("longBusinessSummary", ""),
        "beta": info.get("beta", None),
        "target_mean": info.get("targetMeanPrice", None),
        "recommendation": info.get("recommendationKey", "N/A"),
    }


@st.cache_data(ttl=1800)
def get_analyst_targets(symbol: str) -> pd.DataFrame:
    """ดึง analyst price targets"""
    ticker = yf.Ticker(symbol.upper())
    try:
        recs = ticker.recommendations
        if recs is not None and not recs.empty:
            recs.index = recs.index.tz_localize(None)
            return recs.tail(10)
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_financials(symbol: str) -> dict:
    """ดึงงบการเงิน"""
    ticker = yf.Ticker(symbol.upper())
    return {
        "income_stmt": ticker.income_stmt,
        "balance_sheet": ticker.balance_sheet,
        "cash_flow": ticker.cashflow,
    }


@st.cache_data(ttl=600)
def get_news(symbol: str) -> list:
    """ดึงข่าวล่าสุด"""
    ticker = yf.Ticker(symbol.upper())
    try:
        news = ticker.news or []
        return news[:8]
    except Exception:
        return []


# ─── Technical Indicators (คำนวณด้วย pandas บน DuckDB) ──────────────────────
def compute_technicals(df: pd.DataFrame) -> pd.DataFrame:
    """คำนวณ technical indicators ด้วย pandas + เก็บใน DuckDB"""
    if df.empty:
        return df

    df = df.copy()

    # Moving Averages
    df["MA20"]  = df["Close"].rolling(20).mean()
    df["MA50"]  = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    # RSI
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    ema12       = df["Close"].ewm(span=12).mean()
    ema26       = df["Close"].ewm(span=26).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9).mean()
    df["MACD_Hist"]   = df["MACD"] - df["MACD_Signal"]

    # Bollinger Bands
    std20         = df["Close"].rolling(20).std()
    df["BB_Upper"] = df["MA20"] + 2 * std20
    df["BB_Lower"] = df["MA20"] - 2 * std20

    # เก็บลง DuckDB เพื่อ query ด้วย SQL ได้
    try:
        conn = get_duckdb_conn()
        conn.execute("DROP TABLE IF EXISTS price_data")
        conn.execute("CREATE TABLE price_data AS SELECT * FROM df")
    except Exception:
        pass

    return df


@st.cache_data(ttl=900)
def get_multi_prices(symbols: list, period: str = "1y") -> pd.DataFrame:
    """ดึงราคาปิดของหลายหุ้นพร้อมกัน"""
    frames = {}
    for sym in symbols:
        df = get_price_history(sym, period)
        if not df.empty:
            frames[sym] = df["Close"]
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames)


def query_duckdb(sql: str) -> pd.DataFrame:
    """Run SQL query บน DuckDB"""
    conn = get_duckdb_conn()
    try:
        return conn.execute(sql).df()
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})


# ─── Backtest helper ──────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def run_backtest(symbol: str, strategy: str, period: str = "2y") -> pd.DataFrame:
    """
    Simple backtest engine
    strategy: 'ma_crossover' | 'rsi_mean_reversion'
    """
    df = get_price_history(symbol, period)
    if df.empty:
        return pd.DataFrame()

    df = compute_technicals(df)
    df["Signal"] = 0

    if strategy == "ma_crossover":
        df["Signal"] = np.where(df["MA20"] > df["MA50"], 1, -1)
    elif strategy == "rsi_mean_reversion":
        df["Signal"] = np.where(df["RSI"] < 35, 1, np.where(df["RSI"] > 65, -1, 0))

    df["Return"]    = df["Close"].pct_change()
    df["Strategy"]  = df["Signal"].shift(1) * df["Return"]
    df["Buy_Hold"]  = df["Return"]

    df["Cum_Strategy"] = (1 + df["Strategy"].fillna(0)).cumprod()
    df["Cum_BuyHold"]  = (1 + df["Buy_Hold"].fillna(0)).cumprod()

    return df
