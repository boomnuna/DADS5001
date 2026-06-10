from __future__ import annotations

import hashlib
from datetime import date

import duckdb
import numpy as np
import pandas as pd
import streamlit as st

from src.config import DEMO_END, DEMO_START, DEFAULT_TICKERS


PROFILE = {
    "NVDA": {"start": 480.0, "drift": 0.0018, "vol": 0.026, "volume": 46_000_000},
    "GOOGL": {"start": 140.0, "drift": 0.0008, "vol": 0.016, "volume": 28_000_000},
    "MSFT": {"start": 375.0, "drift": 0.0010, "vol": 0.014, "volume": 24_000_000},
    "AAPL": {"start": 185.0, "drift": 0.0005, "vol": 0.015, "volume": 52_000_000},
    "AMZN": {"start": 165.0, "drift": 0.0007, "vol": 0.018, "volume": 38_000_000},
    "META": {"start": 480.0, "drift": 0.0011, "vol": 0.020, "volume": 18_000_000},
    "TSLA": {"start": 220.0, "drift": 0.0004, "vol": 0.032, "volume": 81_000_000},
}


def _seed_for(ticker: str) -> int:
    digest = hashlib.sha256(ticker.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


@st.cache_data(show_spinner=False)
def load_demo_prices(
    tickers: tuple[str, ...] = tuple(DEFAULT_TICKERS),
    start: date = DEMO_START,
    end: date = DEMO_END,
) -> pd.DataFrame:
    dates = pd.bdate_range(start=start, end=end)
    frames: list[pd.DataFrame] = []

    for ticker in tickers:
        profile = PROFILE.get(ticker, PROFILE["MSFT"])
        rng = np.random.default_rng(_seed_for(ticker))
        shocks = rng.normal(profile["drift"], profile["vol"], len(dates))
        close = [profile["start"]]
        for shock in shocks[1:]:
            close.append(max(close[-1] * (1 + shock), 1.0))

        close_arr = np.array(close)
        open_arr = close_arr * (1 + rng.normal(0, 0.004, len(dates)))
        high_arr = np.maximum(open_arr, close_arr) * (1 + rng.uniform(0.001, 0.018, len(dates)))
        low_arr = np.minimum(open_arr, close_arr) * (1 - rng.uniform(0.001, 0.018, len(dates)))
        volume = (profile["volume"] * (1 + rng.normal(0, 0.14, len(dates)))).astype(int)

        frames.append(
            pd.DataFrame(
                {
                    "date": dates,
                    "ticker": ticker,
                    "open": open_arr.round(2),
                    "high": high_arr.round(2),
                    "low": low_arr.round(2),
                    "close": close_arr.round(2),
                    "volume": np.maximum(volume, 1_000_000),
                }
            )
        )

    return pd.concat(frames, ignore_index=True)


@st.cache_data(show_spinner=False)
def duckdb_price_summary(prices: pd.DataFrame) -> pd.DataFrame:
    con = duckdb.connect(database=":memory:")
    con.register("prices", prices)
    latest = con.execute(
        """
        with ranked as (
            select
                *,
                row_number() over(partition by ticker order by date desc) as rn
            from prices
        )
        select
            ticker,
            date as latest_date,
            close as latest_close,
            volume as latest_volume
        from ranked
        where rn = 1
        order by ticker
        """
    ).df()

    stats = con.execute(
        """
        select
            ticker,
            min(date) as start_date,
            max(date) as end_date,
            avg(volume) as avg_volume,
            stddev_samp(close) as close_std
        from prices
        group by ticker
        order by ticker
        """
    ).df()
    con.close()

    returns = []
    for ticker, group in prices.sort_values("date").groupby("ticker"):
        close = group["close"].reset_index(drop=True)
        returns.append(
            {
                "ticker": ticker,
                "return_1m": _period_return(close, 21),
                "return_3m": _period_return(close, 63),
                "return_6m": _period_return(close, min(126, len(close) - 1)),
                "volatility": close.pct_change().dropna().std() * np.sqrt(252) * 100,
            }
        )

    return latest.merge(stats, on="ticker").merge(pd.DataFrame(returns), on="ticker")


def _period_return(close: pd.Series, days: int) -> float:
    if len(close) <= days:
        days = len(close) - 1
    if days <= 0:
        return 0.0
    return (close.iloc[-1] / close.iloc[-days] - 1) * 100

