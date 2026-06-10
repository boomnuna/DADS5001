"""
pages/3_Dashboard.py
Dashboard — เปรียบเทียบผลตอบแทน ความเสี่ยง Scoreboard รวมทุกมิติ
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import DEFAULT_TICKERS, PALETTE, DEFAULT_PALETTE_COLOR
from src.data_pipeline import load_prices, duckdb_price_summary
from src.indicators import add_technical_indicators, latest_technical_scores
from src.ml_model import train_prediction_models
from src.storage import save_prices_to_snowflake, snowflake_status

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  [data-testid="metric-container"] {
    background: #111827; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 14px 18px;
  }
  [data-testid="metric-container"] label { color: #64748b !important; font-size: 0.72rem !important; text-transform: uppercase; }
  [data-testid="stMetricValue"] { font-family: 'Space Mono', monospace !important; color: #e2e8f0 !important; }
  .section-header { font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;
    letter-spacing:0.12em;margin:20px 0 10px;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px; }
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────────────
tickers = st.session_state.get("selected_tickers", DEFAULT_TICKERS)

st.markdown("## 📊 Stock Analytics Dashboard")
st.caption(f"เปรียบเทียบ {', '.join(tickers)} — ผลตอบแทน, ความเสี่ยง, Technical, ML")

with st.spinner("กำลังโหลดและคำนวณ..."):
    prices     = load_prices(tuple(tickers))
    summary    = duckdb_price_summary(prices)
    indicators = add_technical_indicators(prices)
    technical  = latest_technical_scores(indicators)
    predictions= train_prediction_models(indicators)

if prices.empty:
    st.error("❌ ไม่มีข้อมูล — กลับไปหน้า Stock Selection")
    st.stop()

# ── Scoreboard ────────────────────────────────────────────────────────────────
ai_result = st.session_state.get("ai_result", pd.DataFrame())

scoreboard = (
    summary[["ticker","latest_close","return_1m","return_3m","return_6m","volatility"]]
    .merge(technical[["ticker","technical_score","technical_signal"]], on="ticker", how="left")
    .merge(predictions[["ticker","prediction_score","predicted_label"]], on="ticker", how="left")
)
if not ai_result.empty:
    scoreboard = scoreboard.merge(
        ai_result[["ticker","sentiment_score","recommendation","combined_score"]],
        on="ticker", how="left"
    )

scoreboard["risk_adjusted"] = (
    scoreboard["return_3m"] / scoreboard["volatility"].replace(0, np.nan)
).round(2)

# Safety guard — ถ้ายังไม่มี AI result ให้ใส่ค่า default
if "recommendation" not in scoreboard.columns:
    scoreboard["recommendation"] = "N/A"
if "combined_score" not in scoreboard.columns:
    scoreboard["combined_score"] = None
if "sentiment_score" not in scoreboard.columns:
    scoreboard["sentiment_score"] = None

# Best picks
best_return = scoreboard.sort_values("return_3m", ascending=False).iloc[0]
best_risk   = scoreboard.sort_values("risk_adjusted", ascending=False).iloc[0]
best_tech   = scoreboard.sort_values("technical_score", ascending=False).iloc[0]

st.markdown('<div class="section-header">🏆 Best Picks</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.metric("📈 Best Momentum (3M)",     best_return["ticker"], f"{best_return['return_3m']:+.2f}%")
c2.metric("⚖️ Best Risk-Adjusted",     best_risk["ticker"],   f"{best_risk['risk_adjusted']:.2f}")
c3.metric("📊 Best Technical Score",   best_tech["ticker"],   f"{best_tech['technical_score']:.1f}/100")

st.divider()

# ── Full Scoreboard ────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 Scoreboard รวม</div>', unsafe_allow_html=True)
cols_show = ["ticker","latest_close","return_1m","return_3m","return_6m",
             "volatility","technical_score","technical_signal","prediction_score","risk_adjusted"]
if "combined_score" in scoreboard.columns:
    cols_show += ["combined_score","recommendation"]

disp = scoreboard[cols_show].copy()
disp.columns = (
    ["Ticker","ราคา ($)","1M%","3M%","6M%","Volatility%","Tech Score","Signal","ML Score%","Risk-Adj"]
    + (["AI Score","แนะนำ"] if "combined_score" in scoreboard.columns else [])
)
disp["ราคา ($)"] = disp["ราคา ($)"].map(lambda x: f"${x:,.2f}")
st.dataframe(disp, use_container_width=True, hide_index=True)

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
# 1. Price trend normalized
st.markdown('<div class="section-header">📈 Price Trend (Normalized Base=100)</div>', unsafe_allow_html=True)
fig1 = go.Figure()
for ticker in tickers:
    df = prices[prices["ticker"]==ticker].sort_values("date")
    if df.empty: continue
    indexed = df["close"] / df["close"].iloc[0] * 100
    fig1.add_trace(go.Scatter(x=df["date"], y=indexed, name=ticker,
        line=dict(color=PALETTE.get(ticker, DEFAULT_PALETTE_COLOR), width=2),
        hovertemplate=f"{ticker}: %{{y:.1f}}<extra></extra>"))
fig1.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.2)")
fig1.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
    xaxis=dict(showgrid=False, color="#475569"),
    legend=dict(font=dict(color="#94a3b8",size=12), orientation="h", y=1.08))
st.plotly_chart(fig1, use_container_width=True)

# 2. Drawdown
st.markdown('<div class="section-header">📉 Drawdown</div>', unsafe_allow_html=True)
fig2 = go.Figure()
for ticker in tickers:
    df    = prices[prices["ticker"]==ticker].sort_values("date")
    close = df["close"]
    dd    = (close / close.cummax() - 1) * 100
    fig2.add_trace(go.Scatter(x=df["date"], y=dd, name=ticker,
        line=dict(color=PALETTE.get(ticker, DEFAULT_PALETTE_COLOR), width=1.5),
        fill="tozeroy", fillcolor=PALETTE.get(ticker, DEFAULT_PALETTE_COLOR).replace("#","rgba(").rstrip(")") + ",0.06)"))
fig2.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569",
               ticksuffix="%", title="Drawdown"),
    xaxis=dict(showgrid=False, color="#475569"),
    legend=dict(font=dict(color="#94a3b8",size=12), orientation="h", y=1.08))
st.plotly_chart(fig2, use_container_width=True)

# 3. Return comparison + Volatility side by side
left, right = st.columns(2)
with left:
    st.markdown('<div class="section-header">📊 Return Comparison</div>', unsafe_allow_html=True)
    ret_long = scoreboard.melt(id_vars="ticker", value_vars=["return_1m","return_3m","return_6m"],
                               var_name="period", value_name="return_pct")
    fig3 = go.Figure()
    for ticker in tickers:
        df = ret_long[ret_long["ticker"]==ticker]
        fig3.add_trace(go.Bar(x=df["period"], y=df["return_pct"], name=ticker,
            marker_color=PALETTE.get(ticker, DEFAULT_PALETTE_COLOR),
            text=df["return_pct"].map(lambda x: f"{x:+.1f}%"), textposition="outside"))
    fig3.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", ticksuffix="%"),
        xaxis=dict(color="#475569"), barmode="group",
        legend=dict(font=dict(color="#94a3b8",size=11), orientation="h", y=1.1))
    st.plotly_chart(fig3, use_container_width=True)

with right:
    st.markdown('<div class="section-header">⚡ Volatility</div>', unsafe_allow_html=True)
    fig4 = go.Figure(go.Bar(
        x=scoreboard["ticker"], y=scoreboard["volatility"],
        marker_color=[PALETTE.get(t, DEFAULT_PALETTE_COLOR) for t in scoreboard["ticker"]],
        text=scoreboard["volatility"].map(lambda x: f"{x:.1f}%"), textposition="outside"))
    fig4.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", ticksuffix="%"),
        xaxis=dict(color="#475569"), showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)

# 4. Risk vs Return scatter
st.markdown('<div class="section-header">🎯 Risk vs Return</div>', unsafe_allow_html=True)
fig5 = go.Figure()
for _, row in scoreboard.iterrows():
    fig5.add_trace(go.Scatter(
        x=[row["volatility"]], y=[row["return_3m"]],
        mode="markers+text", name=row["ticker"],
        text=[row["ticker"]], textposition="top center",
        marker=dict(size=18, color=PALETTE.get(row["ticker"], DEFAULT_PALETTE_COLOR)),
    ))
fig5.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)")
fig5.update_layout(height=320, margin=dict(l=0,r=0,t=10,b=0),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569",
               title="Risk: Volatility (%)"),
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569",
               title="Return 3M (%)", ticksuffix="%"),
    showlegend=False)
st.plotly_chart(fig5, use_container_width=True)

# ── Save to Snowflake ──────────────────────────────────────────────────────────
st.divider()
col_sf, col_st = st.columns([1, 3])
with col_sf:
    if st.button("☁️ บันทึก Price Data → Snowflake", use_container_width=True):
        ok = save_prices_to_snowflake(prices)
        st.success("✅ บันทึกแล้ว") if ok else st.warning("ตรวจสอบ Snowflake credentials")
with col_st:
    st.markdown(f'<div style="padding-top:8px;color:#64748b;font-size:0.82rem;">{snowflake_status()}</div>',
                unsafe_allow_html=True)

st.caption("Educational demo only. This is not financial advice.")
