"""
pages/2_Analysis.py
วิเคราะห์หุ้น — Non-AI tab (Technical + ML) และ AI tab (Groq + News)
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from src.config import DEFAULT_TICKERS, PALETTE, DEFAULT_PALETTE_COLOR
from src.data_pipeline import load_prices
from src.indicators import add_technical_indicators, latest_technical_scores
from src.ml_model import train_prediction_models
from src.ai_service import run_ai_analysis, get_news
from src.storage import save_analysis_to_snowflake, snowflake_status

st.set_page_config(page_title="Analysis", page_icon="🔬", layout="wide")

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
  .rec-buy  { background:#064e3b;color:#34d399;padding:4px 14px;border-radius:20px;font-weight:700; }
  .rec-hold { background:#451a03;color:#f59e0b;padding:4px 14px;border-radius:20px;font-weight:700; }
  .rec-sell { background:#450a0a;color:#f87171;padding:4px 14px;border-radius:20px;font-weight:700; }
  .ai-card  { background:linear-gradient(135deg,#0f0f1a,#111827);
    border:1px solid rgba(124,58,237,0.3);border-radius:12px;padding:18px;border-left:3px solid #7C3AED; }
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session / Data ─────────────────────────────────────────────────────────────
tickers = st.session_state.get("selected_tickers", DEFAULT_TICKERS)
mode    = st.session_state.get("analysis_mode", "AI mode")

st.markdown("## 🔬 วิเคราะห์หุ้น")
st.caption(f"หุ้นที่เลือก: **{', '.join(tickers)}** | Mode: **{mode}**")

with st.spinner("กำลังโหลดข้อมูลและคำนวณ indicators..."):
    prices     = load_prices(tuple(tickers))
    indicators = add_technical_indicators(prices)
    technical  = latest_technical_scores(indicators)
    predictions= train_prediction_models(indicators)

if prices.empty:
    st.error("❌ ไม่มีข้อมูลหุ้น — กลับไปหน้า Stock Selection")
    st.stop()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_nonai, tab_ai = st.tabs(["📊 Non-AI Analysis", "🤖 AI Analysis"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — NON-AI
# ════════════════════════════════════════════════════════════════════════════
with tab_nonai:
    st.markdown('<div class="section-header">📊 Technical + ML Score</div>', unsafe_allow_html=True)

    # Summary table
    merged = technical.merge(predictions, on="ticker", how="left")
    disp   = merged[["ticker","technical_score","technical_signal","rsi",
                      "prediction_score","predicted_label","model_name"]].copy()
    disp.columns = ["Ticker","Tech Score","Signal","RSI","ML Score (%)","ML คาดการณ์","Model"]
    st.dataframe(disp, use_container_width=True, hide_index=True)

    st.divider()

    # Per-ticker detail
    for ticker in tickers:
        color = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)
        st.markdown(f'<div class="section-header" style="color:{color};">📈 {ticker}</div>', unsafe_allow_html=True)

        df_ind = indicators[indicators["ticker"] == ticker].sort_values("date")
        t_row  = technical[technical["ticker"] == ticker].iloc[0] if not technical[technical["ticker"]==ticker].empty else {}
        p_row  = predictions[predictions["ticker"]==ticker].iloc[0] if not predictions[predictions["ticker"]==ticker].empty else {}

        # Metrics
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("RSI",            f"{t_row.get('rsi',0):.1f}")
        c2.metric("Technical Score", f"{t_row.get('technical_score',0):.1f}/100")
        c3.metric("Signal",          str(t_row.get("technical_signal","N/A")))
        c4.metric("ML โอกาสขึ้น",   f"{p_row.get('prediction_score',0):.1f}%")
        c5.metric("ML คาดการณ์",    str(p_row.get("predicted_label","N/A")))

        # Price + MA chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["close"],
            name="Close", line=dict(color=color, width=2)))
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["ma20"],
            name="MA20", line=dict(color="#888", dash="dot", width=1.2)))
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["ma50"],
            name="MA50", line=dict(color="#555", dash="dash", width=1.2)))
        # Bollinger Bands
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["bb_upper"],
            name="BB Upper", line=dict(color="rgba(255,255,255,0.2)", dash="dot", width=1)))
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["bb_lower"],
            name="BB Lower", line=dict(color="rgba(255,255,255,0.2)", dash="dot", width=1),
            fill="tonexty", fillcolor="rgba(255,255,255,0.03)"))
        fig.update_layout(
            height=300, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
            xaxis=dict(showgrid=False, color="#475569"),
            legend=dict(font=dict(color="#94a3b8",size=10), orientation="h", y=1.1),
            title=dict(text=f"{ticker} — Price + Bollinger Bands", font=dict(color="#94a3b8",size=13)),
        )
        st.plotly_chart(fig, use_container_width=True)

        # RSI chart
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["rsi"],
            line=dict(color="#7C3AED", width=1.5), name="RSI"))
        for level, c in [(70,"#f87171"),(30,"#34d399"),(50,"rgba(255,255,255,0.2)")]:
            fig_rsi.add_hline(y=level, line_dash="dash", line_color=c, opacity=0.6)
        fig_rsi.update_layout(
            height=180, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(range=[0,100], showgrid=False, color="#475569", title="RSI"),
            xaxis=dict(showgrid=False, color="#475569"),
            showlegend=False,
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

        # MACD chart
        fig_macd = go.Figure()
        fig_macd.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["macd"],
            name="MACD", line=dict(color="#00D4FF", width=1.5)))
        fig_macd.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["macd_signal"],
            name="Signal", line=dict(color="#f59e0b", width=1.2, dash="dash")))
        colors_hist = ["#34d399" if v >= 0 else "#f87171" for v in df_ind["macd_hist"].fillna(0)]
        fig_macd.add_trace(go.Bar(x=df_ind["date"], y=df_ind["macd_hist"],
            name="Histogram", marker_color=colors_hist, opacity=0.6))
        fig_macd.update_layout(
            height=180, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", title="MACD"),
            xaxis=dict(showgrid=False, color="#475569"),
            legend=dict(font=dict(color="#94a3b8",size=10), orientation="h", y=1.1),
            barmode="overlay",
        )
        st.plotly_chart(fig_macd, use_container_width=True)
        st.divider()

    # Explanation
    with st.expander("ℹ️ ทำความเข้าใจ Indicators"):
        st.markdown("""
        - **RSI (Relative Strength Index):** < 30 = Oversold (โอกาสขึ้น), > 70 = Overbought (ระวังลง), 30-70 = Neutral
        - **MACD:** เส้น MACD ตัดขึ้นเหนือ Signal = Bullish, ตัดลงใต้ = Bearish
        - **Bollinger Bands:** ราคาชนขอบล่าง = oversold, ขอบบน = overbought
        - **MA20/MA50:** ราคาเหนือ MA = uptrend, ใต้ MA = downtrend
        - **ML Score:** Random Forest classifier ทำนายโอกาสราคาขึ้นวันถัดไป
        """)

    # Save to Snowflake
    st.divider()
    col_sf, col_st = st.columns([1, 3])
    with col_sf:
        if st.button("☁️ บันทึกผลลง Snowflake", use_container_width=True):
            ok = save_analysis_to_snowflake(technical, predictions, pd.DataFrame())
            st.success("✅ บันทึกแล้ว") if ok else st.warning("ตรวจสอบ Snowflake credentials")
    with col_st:
        st.markdown(f'<div style="padding-top:8px;color:#64748b;font-size:0.82rem;">{snowflake_status()}</div>',
                    unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — AI ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.markdown('<div class="section-header">🤖 AI Analysis — Powered by Groq (Llama 3.3)</div>', unsafe_allow_html=True)
    st.info("AI จะวิเคราะห์ข่าวล่าสุด + Technical + ML แล้วให้คำแนะนำ Buy / Hold / Sell")

    run_btn = st.button("🚀 วิเคราะห์ด้วย AI", type="primary", use_container_width=True)

    if run_btn:
        with st.spinner("AI กำลังวิเคราะห์... (อาจใช้เวลา 15-30 วินาที)"):
            ai_result = run_ai_analysis(technical, predictions, tuple(tickers))
        st.session_state["ai_result"] = ai_result

    ai_result = st.session_state.get("ai_result", pd.DataFrame())

    if not ai_result.empty:
        # Summary recommendation row
        st.markdown('<div class="section-header">📋 สรุปคำแนะนำ</div>', unsafe_allow_html=True)
        cols = st.columns(len(tickers))
        for i, ticker in enumerate(tickers):
            row = ai_result[ai_result["ticker"]==ticker]
            if row.empty:
                continue
            row = row.iloc[0]
            rec   = row.get("recommendation","Hold")
            score = row.get("combined_score", 50)
            cls   = "rec-buy" if rec=="Buy" else "rec-hold" if rec=="Hold" else "rec-sell"
            color = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)
            with cols[i]:
                st.markdown(f"""
                <div style="background:#111827;border:1px solid {color}44;border-radius:12px;
                            padding:16px;text-align:center;">
                  <div style="font-family:'Space Mono',monospace;font-size:1.1rem;
                              font-weight:700;color:#e2e8f0;">{ticker}</div>
                  <div style="margin:8px 0;"><span class="{cls}">{rec}</span></div>
                  <div style="color:#94a3b8;font-size:0.78rem;">Combined Score: {score}/100</div>
                </div>""", unsafe_allow_html=True)

        st.divider()

        # Per-ticker detail
        for ticker in tickers:
            row = ai_result[ai_result["ticker"]==ticker]
            if row.empty:
                continue
            row   = row.iloc[0]
            color = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)

            with st.expander(f"📊 {ticker} — รายละเอียดการวิเคราะห์", expanded=True):
                # Metrics
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Sentiment",      row.get("sentiment_label","N/A"))
                c2.metric("Sentiment Score", f"{row.get('sentiment_score',0):.0f}/100")
                c3.metric("Combined Score",  f"{row.get('combined_score',0):.1f}/100")
                c4.metric("Recommendation",  row.get("recommendation","N/A"))

                # AI Summary
                st.markdown('<div class="section-header">💬 AI Summary</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="ai-card">{row.get("ai_summary","")}</div>', unsafe_allow_html=True)

                # Impact Analysis
                st.markdown('<div class="section-header">📈 Impact Analysis</div>', unsafe_allow_html=True)
                ia1, ia2 = st.columns(2)
                with ia1:
                    st.markdown(f"**Revenue:** {row.get('impact_revenue','N/A')}")
                    st.markdown(f"**Profit:** {row.get('impact_profit','N/A')}")
                with ia2:
                    st.markdown(f"**Competition:** {row.get('impact_competition','N/A')}")
                    st.markdown(f"**Growth:** {row.get('impact_growth','N/A')}")

                # News
                headlines = row.get("news_headlines", [])
                if headlines:
                    st.markdown('<div class="section-header">📰 ข่าวที่ใช้วิเคราะห์</div>', unsafe_allow_html=True)
                    for h in headlines:
                        st.markdown(f"- {h}")

                st.caption(f"💡 {row.get('reason','')}")

        # Save to Snowflake
        st.divider()
        col_sf2, col_st2 = st.columns([1, 3])
        with col_sf2:
            if st.button("☁️ บันทึก AI Results → Snowflake", use_container_width=True):
                ok = save_analysis_to_snowflake(technical, predictions, ai_result)
                st.success("✅ บันทึกแล้ว") if ok else st.warning("ตรวจสอบ Snowflake credentials")
        with col_st2:
            st.markdown(f'<div style="padding-top:8px;color:#64748b;font-size:0.82rem;">{snowflake_status()}</div>',
                        unsafe_allow_html=True)
    else:
        st.info("กด 'วิเคราะห์ด้วย AI' เพื่อรับการวิเคราะห์จาก Groq AI")

st.caption("Educational demo only. This is not financial advice.")
