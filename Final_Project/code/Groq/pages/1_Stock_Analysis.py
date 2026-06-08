"""
pages/1_📊_Stock_Analysis.py
วิเคราะห์หุ้นรายตัว: ราคา, Technical, Fundamentals, ข่าว
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from utils.data_fetcher import (
    get_current_price, get_price_history,
    compute_technicals, get_news, get_analyst_targets, query_duckdb
)

st.set_page_config(page_title="Stock Analysis — TradeX", layout="wide", page_icon="📊")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .section-header { font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;
    letter-spacing:0.12em;margin:20px 0 10px;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px; }
  .metric-pill { background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:8px;
    padding:10px 14px;text-align:center; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🔍 วิเคราะห์หุ้น")
st.caption("ดึงข้อมูลราคาจริง, Technical Indicators และ Analyst Targets จากตลาดจริง")

# ── Search ────────────────────────────────────────────────────────────────────
col_search, col_period, col_btn = st.columns([3, 1, 1])
with col_search:
    symbol = st.text_input("ค้นหาหุ้น", placeholder="เช่น AAPL, TSLA, NVDA, MSFT...",
                           value=st.session_state.get("analysis_symbol", "AAPL")).upper().strip()
with col_period:
    period = st.selectbox("ช่วงเวลา", ["1mo","3mo","6mo","1y","2y","5y"], index=3)
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("🔍 วิเคราะห์", use_container_width=True, type="primary")

if run or symbol:
    st.session_state["analysis_symbol"] = symbol

    # ── Load Data ─────────────────────────────────────────────────────────────
    with st.spinner(f"กำลังดึงข้อมูล {symbol}..."):
        info   = get_current_price(symbol)
        df_raw = get_price_history(symbol, period)

    if df_raw.empty:
        st.error(f"❌ ไม่พบข้อมูลสำหรับ {symbol}")
        st.stop()

    df = compute_technicals(df_raw)

    # ── Quick Stats ───────────────────────────────────────────────────────────
    price    = info["price"]
    chg      = info["change"]
    chg_p    = info["change_pct"]
    color_m  = "normal" if chg >= 0 else "inverse"

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("💲 ราคาปัจจุบัน", f"${price:,.2f}", f"{chg_p:+.2f}%", delta_color=color_m)
    c2.metric("📊 P/E Ratio",  f"{info['pe_ratio']:.1f}" if info["pe_ratio"] else "N/A")
    c3.metric("🎯 Target Price", f"${info['target_mean']:,.2f}" if info["target_mean"] else "N/A")
    c4.metric("⚡ Beta",  f"{info['beta']:.2f}" if info["beta"] else "N/A")
    c5.metric("🏦 Mkt Cap", f"${info['market_cap']/1e9:.1f}B" if info["market_cap"] else "N/A")

    # ── Recommendation Badge ─────────────────────────────────────────────────
    rec = info.get("recommendation", "").upper()
    rec_color = {"STRONG BUY":"#10b981","BUY":"#34d399","HOLD":"#f59e0b",
                 "SELL":"#f87171","STRONG SELL":"#ef4444"}.get(rec, "#64748b")
    st.markdown(f"""
    <div style="margin:4px 0 16px;">
      <span style="background:{rec_color}22;color:{rec_color};border:1px solid {rec_color}44;
        padding:4px 14px;border-radius:20px;font-size:0.8rem;font-weight:600;">
        Analyst: {rec or "N/A"}
      </span>
      <span style="color:#475569;font-size:0.8rem;margin-left:10px;">
        {info['name']} • {info['sector']} • {info['industry']}
      </span>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Tab layout ────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📈 กราฟราคา & Technical", "📋 ข้อมูลพื้นฐาน", "📰 ข่าวล่าสุด", "🗄️ DuckDB SQL"])

    # ─ Tab 1: Price Chart ─────────────────────────────────────────────────────
    with tab1:
        show_ma  = st.checkbox("แสดง Moving Averages", value=True)
        show_bb  = st.checkbox("แสดง Bollinger Bands", value=False)

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.55, 0.25, 0.2],
            vertical_spacing=0.03,
        )

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"],
            increasing_line_color="#34d399", decreasing_line_color="#f87171",
            name="ราคา",
        ), row=1, col=1)

        if show_ma:
            for ma, color, dash in [("MA20","#00D4FF","solid"),("MA50","#f59e0b","dash"),("MA200","#a78bfa","dot")]:
                fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma,
                    line=dict(color=color, width=1.2, dash=dash), opacity=0.8), row=1, col=1)

        if show_bb:
            fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper",
                line=dict(color="#64748b", width=1, dash="dot"), opacity=0.5), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower",
                line=dict(color="#64748b", width=1, dash="dot"), fill="tonexty",
                fillcolor="rgba(100,116,139,0.06)", opacity=0.5), row=1, col=1)

        # Volume
        vol_colors = ["#34d399" if c >= o else "#f87171"
                      for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
            marker_color=vol_colors, opacity=0.6), row=2, col=1)

        # RSI
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
            line=dict(color="#7C3AED", width=1.5)), row=3, col=1)
        for level, color in [(70,"#f87171"),(30,"#34d399")]:
            fig.add_hline(y=level, line_dash="dash", line_color=color, opacity=0.5, row=3, col=1)

        fig.update_layout(
            height=600, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis_rangeslider_visible=False,
            legend=dict(font=dict(color="#94a3b8",size=11), orientation="h", y=1.02),
            xaxis3=dict(showgrid=False, color="#475569"),
            yaxis =dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
            yaxis2=dict(showgrid=False, color="#475569"),
            yaxis3=dict(showgrid=False, color="#475569", title="RSI"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Technical Summary
        last = df.iloc[-1]
        rsi_val  = last["RSI"]
        macd_val = last["MACD"]
        macd_sig = last["MACD_Signal"]

        rsi_label = "🔴 Overbought" if rsi_val > 70 else ("🟢 Oversold" if rsi_val < 30 else "🟡 Neutral")
        macd_label = "🟢 Bullish" if macd_val > macd_sig else "🔴 Bearish"
        trend = "🟢 Uptrend" if price > last["MA200"] else "🔴 Downtrend"

        t1, t2, t3 = st.columns(3)
        t1.metric("RSI (14)", f"{rsi_val:.1f}", rsi_label)
        t2.metric("MACD Signal", macd_label, f"{macd_val:.3f}")
        t3.metric("Trend (MA200)", trend)

    # ─ Tab 2: Fundamentals ────────────────────────────────────────────────────
    with tab2:
        fa, fb = st.columns(2)
        with fa:
            st.markdown('<div class="section-header">📊 ข้อมูลพื้นฐาน</div>', unsafe_allow_html=True)
            fundamentals = {
                "💲 ราคา": f"${price:,.2f}",
                "📈 เปลี่ยนแปลง": f"{chg_p:+.2f}%",
                "🏦 Market Cap": f"${info['market_cap']/1e9:.2f}B" if info["market_cap"] else "N/A",
                "📊 P/E Ratio": f"{info['pe_ratio']:.2f}" if info["pe_ratio"] else "N/A",
                "💰 EPS": f"${info['eps']:.2f}" if info["eps"] else "N/A",
                "⚡ Beta": f"{info['beta']:.2f}" if info["beta"] else "N/A",
                "🎯 Target Price": f"${info['target_mean']:,.2f}" if info["target_mean"] else "N/A",
                "📅 52W High": f"${info['52w_high']:,.2f}" if info["52w_high"] else "N/A",
                "📅 52W Low": f"${info['52w_low']:,.2f}" if info["52w_low"] else "N/A",
                "💹 Dividend Yield": f"{info['dividend_yield']*100:.2f}%" if info["dividend_yield"] else "N/A",
            }
            for k, v in fundamentals.items():
                cols = st.columns([2,1])
                cols[0].markdown(f'<span style="color:#94a3b8;font-size:0.85rem;">{k}</span>', unsafe_allow_html=True)
                cols[1].markdown(f'<span style="font-family:Space Mono,monospace;font-size:0.85rem;color:#e2e8f0;">{v}</span>', unsafe_allow_html=True)

        with fb:
            st.markdown('<div class="section-header">🏢 บริษัท</div>', unsafe_allow_html=True)
            st.markdown(f'**{info["name"]}**')
            st.markdown(f'🏭 {info["sector"]} / {info["industry"]}')
            desc = info.get("description", "")
            if desc:
                st.markdown(f'<div style="color:#94a3b8;font-size:0.83rem;line-height:1.6;">{desc[:600]}...</div>',
                            unsafe_allow_html=True)

            # Analyst targets
            st.markdown('<div class="section-header">🎯 Analyst Recommendations</div>', unsafe_allow_html=True)
            df_rec = get_analyst_targets(symbol)
            if not df_rec.empty:
                st.dataframe(df_rec.tail(5), use_container_width=True)

    # ─ Tab 3: News ────────────────────────────────────────────────────────────
    with tab3:
        news_list = get_news(symbol)
        if news_list:
            for item in news_list:
                content = item.get("content", item)
                title   = content.get("title", item.get("title", ""))
                summary = content.get("summary", item.get("summary", ""))
                url     = content.get("canonicalUrl", {}).get("url", item.get("link", "#"))
                pub_date = content.get("pubDate", "")

                st.markdown(f"""
                <div style="background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:10px;
                            padding:14px;margin-bottom:10px;">
                  <a href="{url}" target="_blank" style="color:#00D4FF;font-weight:600;font-size:0.9rem;text-decoration:none;">
                    {title}
                  </a>
                  <div style="color:#94a3b8;font-size:0.78rem;margin-top:4px;">{pub_date}</div>
                  <div style="color:#64748b;font-size:0.82rem;margin-top:6px;">{summary[:200]}...</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ไม่พบข่าวล่าสุด")

    # ─ Tab 4: DuckDB SQL ─────────────────────────────────────────────────────
    with tab4:
        st.markdown('<div class="section-header">🗄️ Query ข้อมูลด้วย DuckDB SQL</div>', unsafe_allow_html=True)
        st.info("ตารางที่ใช้ได้: `price_data` (โหลดข้อมูลหุ้นที่เลือกแล้ว)")

        default_sql = """SELECT
    CAST(index AS DATE) AS date,
    ROUND(Close, 2) AS close,
    ROUND(MA20, 2) AS ma20,
    ROUND(RSI, 2) AS rsi
FROM price_data
WHERE RSI IS NOT NULL
ORDER BY index DESC
LIMIT 20"""

        sql_query = st.text_area("SQL Query", value=default_sql, height=140)
        if st.button("▶️ Run Query", type="primary"):
            result = query_duckdb(sql_query)
            if not result.empty and "error" not in result.columns:
                st.success(f"✅ {len(result)} rows")
                st.dataframe(result, use_container_width=True)
            else:
                st.error(result.get("error", ["Error"])[0] if "error" in result.columns else "No results")
