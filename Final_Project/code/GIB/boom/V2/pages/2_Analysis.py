"""
pages/2_Analysis.py
วิเคราะห์หุ้น — Toggle Non-AI / AI mode + Decision Summary
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timezone

from src.config import DEFAULT_TICKERS, PALETTE, DEFAULT_PALETTE_COLOR
from src.data_pipeline import load_prices
from src.indicators import add_technical_indicators, latest_technical_scores
from src.ml_model import train_prediction_models
from src.ai_service import run_ai_analysis
from src.storage import (
    save_analysis_to_snowflake, snowflake_status,
    save_analysis_history, load_analysis_history
)

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
  .mode-ai   { background:linear-gradient(90deg,#7C3AED22,#00D4FF22);border:1px solid #7C3AED66;
    color:#a78bfa;padding:6px 18px;border-radius:20px;font-size:0.85rem;font-weight:600;display:inline-block; }
  .mode-nonai{ background:#111827;border:1px solid #374151;
    color:#94a3b8;padding:6px 18px;border-radius:20px;font-size:0.85rem;font-weight:600;display:inline-block; }
  .rec-buy  { background:#064e3b;color:#34d399;padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.85rem; }
  .rec-hold { background:#451a03;color:#f59e0b;padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.85rem; }
  .rec-sell { background:#450a0a;color:#f87171;padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.85rem; }
  .ai-card  { background:linear-gradient(135deg,#0f0f1a,#111827);
    border:1px solid rgba(124,58,237,0.3);border-radius:12px;padding:18px;border-left:3px solid #7C3AED; }
  .decision-card { background:#111827;border:1px solid rgba(0,212,255,0.2);
    border-radius:14px;padding:20px;margin-bottom:8px; }
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session / Data ─────────────────────────────────────────────────────────────
tickers = st.session_state.get("selected_tickers", DEFAULT_TICKERS)

# ── Header + Mode Toggle ───────────────────────────────────────────────────────
st.markdown("## 🔬 วิเคราะห์หุ้น")

col_title, col_mode = st.columns([3, 1])
with col_title:
    st.caption(f"หุ้นที่เลือก: **{', '.join(tickers)}**")
with col_mode:
    mode = st.radio(
        "Analysis Mode",
        ["📊 Non-AI", "🤖 AI"],
        horizontal=True,
        key="analysis_mode_toggle",
        index=1 if st.session_state.get("analysis_mode","AI mode")=="AI mode" else 0,
    )

is_ai = "AI" in mode
if is_ai:
    st.markdown('<span class="mode-ai">🤖 AI Mode — Groq (Llama 3.3) วิเคราะห์ข่าว + ให้คำแนะนำ</span>', unsafe_allow_html=True)
else:
    st.markdown('<span class="mode-nonai">📊 Non-AI Mode — Technical Indicators + Pattern Analysis</span>', unsafe_allow_html=True)

st.session_state.analysis_mode = "AI mode" if is_ai else "Non-AI mode"

st.divider()

# ── Load Data ──────────────────────────────────────────────────────────────────
with st.spinner("กำลังโหลดข้อมูลและคำนวณ indicators..."):
    prices     = load_prices(tuple(tickers))
    indicators = add_technical_indicators(prices)
    technical  = latest_technical_scores(indicators)
    patterns   = train_prediction_models(indicators)

if prices.empty:
    st.error("❌ ไม่มีข้อมูลหุ้น — กลับไปหน้า Stock Selection")
    st.stop()

merged_scores = technical.merge(patterns, on="ticker", how="left")


# ════════════════════════════════════════════════════════════════════════════
# NON-AI MODE
# ════════════════════════════════════════════════════════════════════════════
if not is_ai:
    st.markdown('<div class="section-header">📊 Technical + Pattern Score Summary</div>', unsafe_allow_html=True)

    disp = merged_scores[["ticker","technical_score","technical_signal","rsi","pattern_score","pattern_label"]].copy()
    disp.columns = ["Ticker","Tech Score","Signal","RSI","Pattern Score","Pattern"]
    st.dataframe(disp, use_container_width=True, hide_index=True)

    st.markdown("""
    > ⚠️ **Pattern Score** คือความแข็งแกร่งของ pattern ทางสถิติจากข้อมูลย้อนหลัง
    > **ไม่ใช่การทำนายทิศทาง** — ตลาดหุ้นมีปัจจัยอื่นอีกมากที่ model ไม่สามารถรู้ได้
    """)

    st.divider()

    for ticker in tickers:
        color  = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)
        df_ind = indicators[indicators["ticker"]==ticker].sort_values("date")
        t_row  = merged_scores[merged_scores["ticker"]==ticker].iloc[0] if not merged_scores[merged_scores["ticker"]==ticker].empty else {}

        st.markdown(f'<div class="section-header" style="color:{color};">📈 {ticker}</div>', unsafe_allow_html=True)

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Technical Score",f"{t_row.get('technical_score',0):.1f}/100")
        c2.metric("Signal",          str(t_row.get("technical_signal","N/A")))
        c3.metric("RSI",             f"{t_row.get('rsi',0):.1f}")
        c4.metric("Pattern Score",   f"{t_row.get('pattern_score',0):.1f}/100")

        # Price + MA + BB
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["close"],
            name="Close", line=dict(color=color, width=2)))
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["ma20"],
            name="MA20", line=dict(color="#888", dash="dot", width=1.2)))
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["ma50"],
            name="MA50", line=dict(color="#555", dash="dash", width=1.2)))
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["bb_upper"],
            name="BB Upper", line=dict(color="rgba(255,255,255,0.2)", dash="dot", width=1)))
        fig.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["bb_lower"],
            name="BB Lower", line=dict(color="rgba(255,255,255,0.2)", dash="dot", width=1),
            fill="tonexty", fillcolor="rgba(255,255,255,0.03)"))
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
            xaxis=dict(showgrid=False, color="#475569"),
            legend=dict(font=dict(color="#94a3b8",size=10), orientation="h", y=1.1))
        st.plotly_chart(fig, use_container_width=True)

        # RSI + MACD row
        left, right = st.columns(2)
        with left:
            fig_rsi = go.Figure()
            fig_rsi.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["rsi"],
                line=dict(color="#7C3AED", width=1.5), name="RSI"))
            for level, c in [(70,"#f87171"),(30,"#34d399")]:
                fig_rsi.add_hline(y=level, line_dash="dash", line_color=c, opacity=0.6)
            fig_rsi.update_layout(height=180, margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(range=[0,100], showgrid=False, color="#475569", title="RSI"),
                xaxis=dict(showgrid=False, color="#475569"), showlegend=False)
            st.plotly_chart(fig_rsi, use_container_width=True)

        with right:
            fig_macd = go.Figure()
            fig_macd.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["macd"],
                name="MACD", line=dict(color="#00D4FF", width=1.5)))
            fig_macd.add_trace(go.Scatter(x=df_ind["date"], y=df_ind["macd_signal"],
                name="Signal", line=dict(color="#f59e0b", width=1.2, dash="dash")))
            colors_hist = ["#34d399" if v >= 0 else "#f87171" for v in df_ind["macd_hist"].fillna(0)]
            fig_macd.add_trace(go.Bar(x=df_ind["date"], y=df_ind["macd_hist"],
                marker_color=colors_hist, opacity=0.6, name="Histogram"))
            fig_macd.update_layout(height=180, margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
                xaxis=dict(showgrid=False, color="#475569"),
                legend=dict(font=dict(color="#94a3b8",size=10), orientation="h", y=1.1),
                barmode="overlay")
            st.plotly_chart(fig_macd, use_container_width=True)

        st.divider()

    with st.expander("ℹ️ ทำความเข้าใจ Indicators"):
        st.markdown("""
        - **RSI:** < 30 = Oversold, > 70 = Overbought, 30-70 = Neutral
        - **MACD:** เส้น MACD ตัดขึ้นเหนือ Signal = Bullish momentum
        - **Bollinger Bands:** แสดง range ของราคาปกติ ราคาชน band = สัญญาณ reversal
        - **MA20/MA50:** ราคาเหนือ MA = uptrend
        - **Pattern Score:** ความแข็งแกร่งของ pattern ทางสถิติจาก Random Forest (ไม่ใช่การทำนาย)
        """)


# ════════════════════════════════════════════════════════════════════════════
# AI MODE
# ════════════════════════════════════════════════════════════════════════════
else:
    st.markdown('<div class="section-header">🤖 AI Analysis — Groq (Llama 3.3)</div>', unsafe_allow_html=True)
    st.info("AI ดึงข่าวล่าสุด + วิเคราะห์ Technical + Pattern แล้วให้คำแนะนำ Buy / Hold / Sell")

    run_btn = st.button("🚀 วิเคราะห์ด้วย AI", type="primary", use_container_width=True)

    if run_btn:
        with st.spinner("AI กำลังดึงข่าวและวิเคราะห์... (15-30 วินาที)"):
            ai_result = run_ai_analysis(technical, patterns, tuple(tickers))
        st.session_state["ai_result"] = ai_result

        # บันทึกลง MongoDB
        results_for_mongo = ai_result[["ticker","recommendation","combined_score","sentiment_label"]].to_dict("records")
        msg = save_analysis_history(tickers, results_for_mongo)
        st.success(msg)

        # บันทึกลง Snowflake
        ok = save_analysis_to_snowflake(technical, patterns, ai_result)
        if ok:
            st.success("✅ บันทึกผลลง Snowflake แล้ว")

    ai_result = st.session_state.get("ai_result", pd.DataFrame())

    if not ai_result.empty:

        # ─ Decision Summary ──────────────────────────────────────────────────
        st.markdown('<div class="section-header">🎯 Investment Decision Summary</div>', unsafe_allow_html=True)
        st.caption("สรุปจากทุกมิติ: Technical + Pattern + AI Sentiment → คำแนะนำการลงทุน")

        for ticker in tickers:
            t_row = merged_scores[merged_scores["ticker"]==ticker]
            a_row = ai_result[ai_result["ticker"]==ticker]
            if t_row.empty or a_row.empty:
                continue
            t = t_row.iloc[0]; a = a_row.iloc[0]

            rec   = a.get("recommendation","Hold")
            color = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)
            cls   = "rec-buy" if rec=="Buy" else "rec-hold" if rec=="Hold" else "rec-sell"

            tech_sig  = t.get("technical_signal","N/A")
            pat_score = t.get("pattern_score",50)
            sentiment = a.get("sentiment_label","N/A")
            combined  = a.get("combined_score",50)
            reason    = a.get("reason","")

            st.markdown(f"""
            <div class="decision-card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <span style="font-family:'Space Mono',monospace;font-size:1.2rem;font-weight:700;color:{color};">{ticker}</span>
                <span class="{cls}">⚡ {rec}</span>
              </div>
              <div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:10px;">
                <div><span style="color:#64748b;font-size:0.75rem;">TECHNICAL</span><br>
                     <span style="color:#e2e8f0;font-size:0.9rem;">{tech_sig}</span></div>
                <div><span style="color:#64748b;font-size:0.75rem;">PATTERN SCORE</span><br>
                     <span style="color:#e2e8f0;font-size:0.9rem;">{pat_score:.0f}/100</span></div>
                <div><span style="color:#64748b;font-size:0.75rem;">AI SENTIMENT</span><br>
                     <span style="color:#e2e8f0;font-size:0.9rem;">{sentiment}</span></div>
                <div><span style="color:#64748b;font-size:0.75rem;">COMBINED SCORE</span><br>
                     <span style="color:#e2e8f0;font-size:0.9rem;">{combined:.1f}/100</span></div>
              </div>
              <div style="color:#94a3b8;font-size:0.82rem;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
                💡 {reason}
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ─ Per-ticker AI detail ────────────────────────────────────────────────
        for ticker in tickers:
            a_row = ai_result[ai_result["ticker"]==ticker]
            if a_row.empty: continue
            a     = a_row.iloc[0]
            color = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)

            with st.expander(f"📊 {ticker} — รายละเอียด AI Analysis", expanded=False):
                c1,c2,c3 = st.columns(3)
                c1.metric("Sentiment",      a.get("sentiment_label","N/A"))
                c2.metric("Sentiment Score", f"{a.get('sentiment_score',0):.0f}/100")
                c3.metric("Combined Score",  f"{a.get('combined_score',0):.1f}/100")

                st.markdown('<div class="section-header">💬 AI Summary</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="ai-card">{a.get("ai_summary","")}</div>', unsafe_allow_html=True)

                st.markdown('<div class="section-header">📈 Impact Analysis</div>', unsafe_allow_html=True)
                ia1, ia2 = st.columns(2)
                with ia1:
                    st.markdown(f"**Revenue:** {a.get('impact_revenue','N/A')}")
                    st.markdown(f"**Profit:** {a.get('impact_profit','N/A')}")
                with ia2:
                    st.markdown(f"**Competition:** {a.get('impact_competition','N/A')}")
                    st.markdown(f"**Growth:** {a.get('impact_growth','N/A')}")

                headlines = a.get("news_headlines", [])
                if headlines:
                    st.markdown('<div class="section-header">📰 ข่าวที่ใช้วิเคราะห์</div>', unsafe_allow_html=True)
                    for h in headlines:
                        st.markdown(f"- {h}")

        # ─ Analysis History จาก MongoDB ──────────────────────────────────────
        st.divider()
        st.markdown('<div class="section-header">🕐 ประวัติการวิเคราะห์ (MongoDB)</div>', unsafe_allow_html=True)
        history = load_analysis_history(5)
        if history:
            for h in history:
                tickers_str = ", ".join(h.get("tickers",[]))
                time_str    = h["analyzed_at"].strftime("%d/%m/%Y %H:%M") if hasattr(h.get("analyzed_at"), "strftime") else str(h.get("analyzed_at",""))
                results     = h.get("results",[])
                recs        = " | ".join([f"{r['ticker']}: {r.get('recommendation','N/A')}" for r in results])
                st.markdown(f"""
                <div style="background:#111827;border:1px solid rgba(255,255,255,0.06);
                            border-radius:8px;padding:10px 14px;margin-bottom:6px;">
                  <div style="display:flex;justify-content:space-between;">
                    <span style="color:#e2e8f0;font-size:0.85rem;">📋 {tickers_str}</span>
                    <span style="color:#475569;font-size:0.75rem;">{time_str}</span>
                  </div>
                  <div style="color:#64748b;font-size:0.78rem;margin-top:4px;">{recs}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.caption("ยังไม่มีประวัติ — กด 'วิเคราะห์ด้วย AI' เพื่อเริ่มบันทึก")

    else:
        st.info("กด 'วิเคราะห์ด้วย AI' เพื่อรับการวิเคราะห์และคำแนะนำ")

st.caption("Educational demo only. This is not financial advice.")
