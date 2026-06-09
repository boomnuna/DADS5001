"""
pages/4_⚗️_Backtest.py
Backtest — ทดสอบ strategy ย้อนหลังด้วยข้อมูลจริงจาก Yahoo Finance
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from utils.data_fetcher import run_backtest, get_price_history, compute_technicals

st.set_page_config(page_title="Backtest — TradeX", layout="wide", page_icon="⚗️")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .section-header { font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;
    letter-spacing:0.12em;margin:20px 0 10px;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px; }
</style>
""", unsafe_allow_html=True)

st.markdown("## ⚗️ Backtest Engine")
st.caption("วิเคราะห์ Pattern ราคาหุ้นจากข้อมูลจริงย้อนหลัง — คำนวณโอกาสสำเร็จและสถานภาพตลาด")

# ── Inputs ────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([2,2,1.5,1])
with col1:
    symbol   = st.text_input("Ticker", value="AAPL", placeholder="เช่น AAPL, TSLA...").upper().strip()
with col2:
    strategy = st.selectbox("Strategy", [
        "ma_crossover",
        "rsi_mean_reversion",
    ], format_func=lambda x: {
        "ma_crossover":       "📊 MA Crossover (MA20 vs MA50)",
        "rsi_mean_reversion": "📉 RSI Mean Reversion (<35 ซื้อ / >65 ขาย)",
    }[x])
with col3:
    period = st.selectbox("ช่วงเวลา", ["1y","2y","3y","5y"], index=1)
with col4:
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("▶️ Run Backtest", type="primary", use_container_width=True)

if run_btn or symbol:
    with st.spinner(f"กำลัง Backtest {symbol} — {strategy}..."):
        df = run_backtest(symbol, strategy, period)

    if df.empty:
        st.error(f"❌ ไม่สามารถ backtest {symbol} ได้")
        st.stop()

    df = df.dropna(subset=["Cum_Strategy","Cum_BuyHold"])

    # ── Performance Metrics ────────────────────────────────────────────────────
    start_val = df["Close"].iloc[0]
    end_val   = df["Close"].iloc[-1]
    strat_ret = (df["Cum_Strategy"].iloc[-1] - 1) * 100
    bh_ret    = (df["Cum_BuyHold"].iloc[-1] - 1) * 100

    strat_daily = df["Strategy"].dropna()
    sharpe = (strat_daily.mean() / strat_daily.std() * np.sqrt(252)) if strat_daily.std() > 0 else 0

    # Max Drawdown
    cum = df["Cum_Strategy"]
    roll_max = cum.cummax()
    dd       = (cum - roll_max) / roll_max
    max_dd   = dd.min() * 100

    # Win rate
    trades   = df["Signal"].diff().fillna(0)
    n_trades = (trades != 0).sum()
    wins = (strat_daily > 0).sum()
    win_rate = (wins / len(strat_daily) * 100) if len(strat_daily) > 0 else 0

    st.divider()
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("📈 Strategy Return", f"{strat_ret:+.2f}%",
              f"{strat_ret-bh_ret:+.2f}% vs B&H",
              delta_color="normal" if strat_ret >= bh_ret else "inverse")
    c2.metric("🏦 Buy & Hold",    f"{bh_ret:+.2f}%")
    c3.metric("⚡ Sharpe Ratio",  f"{sharpe:.2f}")
    c4.metric("📉 Max Drawdown",  f"{max_dd:.2f}%", delta_color="inverse")
    c5.metric("🎯 จำนวน Trades",  f"{n_trades}")

    st.divider()

    # ── Chart ──────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 ผลการทดสอบ — Cumulative Return</div>', unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=(df["Cum_Strategy"]-1)*100,
        name="Strategy", line=dict(color="#00D4FF", width=2.5),
        hovertemplate="%{y:.2f}%<extra>Strategy</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=(df["Cum_BuyHold"]-1)*100,
        name="Buy & Hold", line=dict(color="#f59e0b", width=1.8, dash="dash"),
        hovertemplate="%{y:.2f}%<extra>Buy & Hold</extra>",
    ))
    fig.add_hline(y=0, line_dash="solid", line_color="rgba(255,255,255,0.15)")
    fig.update_layout(
        height=350, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569",
                   title="Cumulative Return (%)"),
        xaxis=dict(showgrid=False, color="#475569"),
        legend=dict(font=dict(color="#94a3b8",size=12), orientation="h", y=1.08),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Signal Chart ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔔 สัญญาณ Buy/Sell บนกราฟราคา</div>', unsafe_allow_html=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        mode="lines", line=dict(color="#64748b", width=1.5),
        name="Price",
    ))

    # Buy signals
    buy_sig  = df[df["Signal"] == 1]
    sell_sig = df[df["Signal"] == -1]
    fig2.add_trace(go.Scatter(
        x=buy_sig.index, y=buy_sig["Close"],
        mode="markers", marker=dict(color="#34d399", size=7, symbol="triangle-up"),
        name="Buy Signal",
    ))
    fig2.add_trace(go.Scatter(
        x=sell_sig.index, y=sell_sig["Close"],
        mode="markers", marker=dict(color="#f87171", size=7, symbol="triangle-down"),
        name="Sell Signal",
    ))
    fig2.update_layout(
        height=300, margin=dict(l=0,r=0,t=10,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
        xaxis=dict(showgrid=False, color="#475569"),
        legend=dict(font=dict(color="#94a3b8",size=11), orientation="h", y=1.08),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Monthly Returns Heatmap ───────────────────────────────────────────────
    st.markdown('<div class="section-header">📅 Monthly Returns</div>', unsafe_allow_html=True)
    df["Month"] = df.index.to_period("M")
    monthly = df.groupby("Month")["Strategy"].sum().reset_index()
    monthly["Return%"] = (monthly["Strategy"] * 100).round(2)
    monthly["Month"]   = monthly["Month"].astype(str)
    colors_m = ["#34d399" if v >= 0 else "#f87171" for v in monthly["Return%"]]
    fig3 = go.Figure(go.Bar(
        x=monthly["Month"], y=monthly["Return%"],
        marker_color=colors_m,
        text=monthly["Return%"].map(lambda x: f"{x:+.1f}%"),
        textposition="outside",
    ))
    fig3.update_layout(
        height=280, margin=dict(l=0,r=0,t=10,b=30),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569",
                   title="Return (%)"),
        xaxis=dict(color="#475569", tickangle=-45),
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Strategy description
    st.divider()
    desc = {
        "ma_crossover":       "**MA Crossover:** ซื้อเมื่อ MA20 > MA50 (Golden Cross), ขายเมื่อ MA20 < MA50 (Death Cross)",
        "rsi_mean_reversion": "**RSI Mean Reversion:** ซื้อเมื่อ RSI < 35 (Oversold), ขายเมื่อ RSI > 65 (Overbought)",
    }
    st.info(f"📖 Strategy: {desc[strategy]}")
    st.caption("⚠️ ผล Backtest เป็นเพียงการทดสอบย้อนหลัง ไม่ได้รับประกันผลในอนาคต")
