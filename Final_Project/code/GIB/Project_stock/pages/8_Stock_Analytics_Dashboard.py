import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ai_service import run_demo_ai_analysis
from src.config import APP_TITLE, DEFAULT_TICKERS, PALETTE
from src.data_pipeline import duckdb_price_summary, load_demo_prices
from src.indicators import add_technical_indicators, latest_technical_scores
from src.ml_model import train_prediction_models
from src.storage import build_snowflake_demo_tables
from src.ui import disclaimer, setup_page

setup_page(f"{APP_TITLE} - Dashboard")

tickers = st.session_state.get("selected_tickers", DEFAULT_TICKERS)
st.title("Stock Analytics Dashboard")
st.caption("Compare return, risk, technical score, ML prediction, and AI sentiment.")

prices = load_demo_prices(tuple(tickers))
summary = duckdb_price_summary(prices)
indicators = add_technical_indicators(prices)
technical = latest_technical_scores(indicators)
predictions = train_prediction_models(indicators)
ai_result = run_demo_ai_analysis(technical, predictions)
tables = build_snowflake_demo_tables(prices, indicators, predictions, ai_result)

scoreboard = (
    summary[["ticker", "return_1m", "return_3m", "return_6m", "volatility"]]
    .merge(technical[["ticker", "technical_score", "technical_signal"]], on="ticker")
    .merge(predictions[["ticker", "prediction_score"]], on="ticker")
    .merge(ai_result[["ticker", "sentiment_score", "combined_score", "recommendation"]], on="ticker")
)
scoreboard["risk_adjusted"] = scoreboard["return_3m"] / scoreboard["volatility"].replace(0, np.nan)

best_momentum = scoreboard.sort_values("return_3m", ascending=False).iloc[0]
best_risk = scoreboard.sort_values("risk_adjusted", ascending=False).iloc[0]
best_ai = scoreboard.sort_values("sentiment_score", ascending=False).iloc[0]

c1, c2, c3 = st.columns(3)
c1.metric("Best momentum", best_momentum["ticker"], f"{best_momentum['return_3m']:.2f}% 3M")
c2.metric("Best risk-adjusted", best_risk["ticker"], f"{best_risk['risk_adjusted']:.2f}")
c3.metric("Highest AI sentiment", best_ai["ticker"], f"{best_ai['sentiment_score']:.0f}/100")

st.subheader("Scoreboard")
st.dataframe(scoreboard, use_container_width=True)

def chart_price_trend() -> go.Figure:
    fig = go.Figure()
    for ticker in tickers:
        df = prices[prices["ticker"] == ticker].sort_values("date")
        indexed = df["close"] / df["close"].iloc[0] * 100
        fig.add_trace(go.Scatter(x=df["date"], y=indexed, name=ticker, line=dict(color=PALETTE[ticker])))
    fig.update_layout(height=320, title="01 Price trend - indexed to 100", margin=dict(l=20, r=20, t=45, b=20))
    return fig


def chart_drawdown() -> go.Figure:
    fig = go.Figure()
    for ticker in tickers:
        df = prices[prices["ticker"] == ticker].sort_values("date")
        close = df["close"]
        drawdown = (close / close.cummax() - 1) * 100
        fig.add_trace(go.Scatter(x=df["date"], y=drawdown, name=ticker, line=dict(color=PALETTE[ticker]), fill="tozeroy"))
    fig.update_layout(height=260, title="02 Drawdown", yaxis_ticksuffix="%", margin=dict(l=20, r=20, t=45, b=20))
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str) -> go.Figure:
    fig = go.Figure(go.Bar(x=df[x], y=df[y], marker_color=[PALETTE[t] for t in df[x]]))
    fig.update_layout(height=280, title=title, margin=dict(l=20, r=20, t=45, b=20))
    return fig


st.plotly_chart(chart_price_trend(), use_container_width=True)
st.plotly_chart(chart_drawdown(), use_container_width=True)

left, right = st.columns(2)
with left:
    return_long = scoreboard.melt(
        id_vars="ticker",
        value_vars=["return_1m", "return_3m", "return_6m"],
        var_name="period",
        value_name="return_pct",
    )
    fig = go.Figure()
    for ticker in tickers:
        df = return_long[return_long["ticker"] == ticker]
        fig.add_trace(go.Bar(x=df["period"], y=df["return_pct"], name=ticker, marker_color=PALETTE[ticker]))
    fig.update_layout(height=300, title="03 Return comparison", barmode="group", yaxis_ticksuffix="%")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.plotly_chart(bar_chart(scoreboard, "ticker", "volatility", "04 Volatility"), use_container_width=True)

left, right = st.columns(2)
with left:
    tech_long = technical.melt(
        id_vars="ticker",
        value_vars=["rsi_score", "macd_score", "ma_score"],
        var_name="indicator",
        value_name="score",
    )
    fig = go.Figure()
    for ticker in tickers:
        df = tech_long[tech_long["ticker"] == ticker]
        fig.add_trace(go.Bar(x=df["indicator"], y=df["score"], name=ticker, marker_color=PALETTE[ticker]))
    fig.update_layout(height=300, title="05 Technical score", barmode="group", yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.plotly_chart(bar_chart(scoreboard, "ticker", "prediction_score", "06 ML up-probability"), use_container_width=True)

left, right = st.columns(2)
with left:
    st.plotly_chart(bar_chart(scoreboard, "ticker", "sentiment_score", "07 Sentiment score"), use_container_width=True)

with right:
    fig = go.Figure()
    for row in scoreboard.to_dict("records"):
        fig.add_trace(
            go.Scatter(
                x=[row["volatility"]],
                y=[row["return_3m"]],
                mode="markers+text",
                name=row["ticker"],
                text=[row["ticker"]],
                textposition="top center",
                marker=dict(size=16, color=PALETTE[row["ticker"]]),
            )
        )
    fig.update_layout(
        height=300,
        title="08 Risk vs return",
        xaxis_title="Risk: annualized volatility (%)",
        yaxis_title="Return: 3M (%)",
    )
    st.plotly_chart(fig, use_container_width=True)

with st.expander("Snowflake demo tables"):
    st.write("These are the DataFrames that map to Snowflake tables in the cloud version.")
    for name, table in tables.items():
        st.write(f"**{name}**")
        st.dataframe(table.head(20), use_container_width=True)

disclaimer()

