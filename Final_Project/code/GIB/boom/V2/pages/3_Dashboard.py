"""
pages/3_Dashboard.py
Dashboard — Scoreboard + Charts + Sector Screening + Decision Summary
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import DEFAULT_TICKERS, PALETTE, DEFAULT_PALETTE_COLOR, SECTORS
from src.data_pipeline import load_prices, duckdb_price_summary
from src.indicators import add_technical_indicators, latest_technical_scores
from src.ml_model import train_prediction_models
from src.ai_service import screen_sector, ai_sector_commentary, SECTORS as SECTOR_MAP
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
  .rec-buy  { background:#064e3b;color:#34d399;padding:3px 12px;border-radius:20px;font-weight:700;font-size:0.82rem; }
  .rec-hold { background:#451a03;color:#f59e0b;padding:3px 12px;border-radius:20px;font-weight:700;font-size:0.82rem; }
  .rec-sell { background:#450a0a;color:#f87171;padding:3px 12px;border-radius:20px;font-weight:700;font-size:0.82rem; }
  .ai-card  { background:linear-gradient(135deg,#0f0f1a,#111827);
    border:1px solid rgba(124,58,237,0.3);border-radius:12px;padding:18px;border-left:3px solid #7C3AED; }
  .decision-card { background:#111827;border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:18px;margin-bottom:8px; }
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────────────
tickers = st.session_state.get("selected_tickers", DEFAULT_TICKERS)

st.markdown("## 📊 Stock Analytics Dashboard")
st.caption(f"เปรียบเทียบ **{', '.join(tickers)}** — ผลตอบแทน, ความเสี่ยง, Technical, Pattern")

with st.spinner("กำลังโหลดข้อมูล..."):
    prices     = load_prices(tuple(tickers))
    summary    = duckdb_price_summary(prices)
    indicators = add_technical_indicators(prices)
    technical  = latest_technical_scores(indicators)
    patterns   = train_prediction_models(indicators)

if prices.empty:
    st.error("❌ ไม่มีข้อมูล — กลับไปหน้า Stock Selection")
    st.stop()

ai_result  = st.session_state.get("ai_result", pd.DataFrame())
scoreboard = (
    summary[["ticker","latest_close","return_1m","return_3m","return_6m","volatility"]]
    .merge(technical[["ticker","technical_score","technical_signal"]], on="ticker", how="left")
    .merge(patterns[["ticker","pattern_score","pattern_label"]], on="ticker", how="left")
)
if not ai_result.empty:
    scoreboard = scoreboard.merge(
        ai_result[["ticker","sentiment_label","recommendation","combined_score"]],
        on="ticker", how="left"
    )
scoreboard["risk_adjusted"] = (scoreboard["return_3m"] / scoreboard["volatility"].replace(0, np.nan)).round(2)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_overview, tab_sector, tab_decision = st.tabs(["📊 ภาพรวม", "🏭 Sector Screening", "🎯 Decision Summary"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
with tab_overview:
    # Best picks
    best_return = scoreboard.sort_values("return_3m", ascending=False).iloc[0]
    best_risk   = scoreboard.sort_values("risk_adjusted", ascending=False).iloc[0]
    best_tech   = scoreboard.sort_values("technical_score", ascending=False).iloc[0]

    st.markdown('<div class="section-header">🏆 Best Picks</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("📈 Best Momentum (3M)",   best_return["ticker"], f"{best_return['return_3m']:+.2f}%")
    c2.metric("⚖️ Best Risk-Adjusted",   best_risk["ticker"],   f"{best_risk['risk_adjusted']:.2f}")
    c3.metric("📊 Best Technical Score", best_tech["ticker"],   f"{best_tech['technical_score']:.1f}/100")

    st.divider()

    # Scoreboard table
    st.markdown('<div class="section-header">📋 Scoreboard</div>', unsafe_allow_html=True)
    cols_show = ["ticker","latest_close","return_1m","return_3m","return_6m","volatility","technical_score","technical_signal","pattern_score","risk_adjusted"]
    if "combined_score" in scoreboard.columns:
        cols_show += ["combined_score","recommendation"]
    disp = scoreboard[cols_show].copy()
    rename = ["Ticker","ราคา ($)","1M%","3M%","6M%","Volatility%","Tech Score","Signal","Pattern Score","Risk-Adj"]
    if "combined_score" in scoreboard.columns:
        rename += ["AI Score","แนะนำ"]
    disp.columns = rename
    disp["ราคา ($)"] = disp["ราคา ($)"].map(lambda x: f"${x:,.2f}")
    st.dataframe(disp, use_container_width=True, hide_index=True)

    st.divider()

    # Charts
    st.markdown('<div class="section-header">📈 Price Trend (Normalized)</div>', unsafe_allow_html=True)
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

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-header">📊 Return Comparison</div>', unsafe_allow_html=True)
        ret_long = scoreboard.melt(id_vars="ticker", value_vars=["return_1m","return_3m","return_6m"],
                                   var_name="period", value_name="return_pct")
        fig2 = go.Figure()
        for ticker in tickers:
            df = ret_long[ret_long["ticker"]==ticker]
            fig2.add_trace(go.Bar(x=df["period"], y=df["return_pct"], name=ticker,
                marker_color=PALETTE.get(ticker, DEFAULT_PALETTE_COLOR),
                text=df["return_pct"].map(lambda x: f"{x:+.1f}%"), textposition="outside"))
        fig2.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", ticksuffix="%"),
            xaxis=dict(color="#475569"), barmode="group",
            legend=dict(font=dict(color="#94a3b8",size=11), orientation="h", y=1.1))
        st.plotly_chart(fig2, use_container_width=True)

    with right:
        st.markdown('<div class="section-header">🎯 Risk vs Return</div>', unsafe_allow_html=True)
        fig3 = go.Figure()
        for _, row in scoreboard.iterrows():
            fig3.add_trace(go.Scatter(
                x=[row["volatility"]], y=[row["return_3m"]],
                mode="markers+text", name=row["ticker"],
                text=[row["ticker"]], textposition="top center",
                marker=dict(size=18, color=PALETTE.get(row["ticker"], DEFAULT_PALETTE_COLOR))))
        fig3.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.2)")
        fig3.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", title="Volatility%"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", title="Return 3M%"),
            showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    # Save to Snowflake
    st.divider()
    col_sf, col_st = st.columns([1,3])
    with col_sf:
        if st.button("☁️ บันทึก Price → Snowflake", use_container_width=True):
            ok = save_prices_to_snowflake(prices)
            st.success("✅ บันทึกแล้ว") if ok else st.warning("ตรวจสอบ Snowflake")
    with col_st:
        st.markdown(f'<div style="padding-top:8px;color:#64748b;font-size:0.82rem;">{snowflake_status()}</div>',
                    unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — SECTOR SCREENING
# ════════════════════════════════════════════════════════════════════════════
with tab_sector:
    st.markdown('<div class="section-header">🏭 Sector Screening — หุ้นที่กำลังมาแรง</div>', unsafe_allow_html=True)
    st.caption("เปรียบเทียบหุ้นในอุตสาหกรรมเดียวกัน ดูว่าตัวไหนมี momentum ดีที่สุด")

    sector_list = list(SECTOR_MAP.keys())
    col_sec, col_run = st.columns([2,1])
    with col_sec:
        selected_sector = st.selectbox("เลือกอุตสาหกรรม", sector_list, key="sector_select")
    with col_run:
        st.markdown("<br>", unsafe_allow_html=True)
        screen_btn = st.button("🔍 Scan Sector", type="primary", use_container_width=True)

    # Show tickers in sector
    sector_tickers = SECTOR_MAP.get(selected_sector, [])
    st.caption(f"หุ้นในกลุ่ม: {', '.join(sector_tickers)}")

    if screen_btn:
        with st.spinner(f"กำลัง scan {selected_sector} sector..."):
            screen_df = screen_sector(selected_sector)
        st.session_state["screen_df"]      = screen_df
        st.session_state["screen_sector"]  = selected_sector

        # AI commentary
        with st.spinner("AI กำลังสรุป sector..."):
            commentary = ai_sector_commentary(selected_sector, screen_df)
        st.session_state["sector_commentary"] = commentary

    screen_df  = st.session_state.get("screen_df", pd.DataFrame())
    commentary = st.session_state.get("sector_commentary", "")

    if not screen_df.empty:
        # Momentum ranking
        st.markdown('<div class="section-header">🚀 Momentum Ranking</div>', unsafe_allow_html=True)

        # Top 3 cards
        top3 = screen_df.head(3)
        cols = st.columns(len(top3))
        medals = ["🥇","🥈","🥉"]
        for i, (_, row) in enumerate(top3.iterrows()):
            color = PALETTE.get(row["ticker"], DEFAULT_PALETTE_COLOR)
            with cols[i]:
                st.markdown(f"""
                <div style="background:#111827;border:1px solid {color}44;border-radius:12px;
                            padding:16px;text-align:center;">
                  <div style="font-size:1.5rem;">{medals[i]}</div>
                  <div style="font-family:'Space Mono',monospace;font-size:1.1rem;
                              font-weight:700;color:{color};margin:6px 0;">{row['ticker']}</div>
                  <div style="color:#94a3b8;font-size:0.78rem;">Momentum Score</div>
                  <div style="font-family:'Space Mono',monospace;font-size:1.3rem;
                              color:#e2e8f0;">{row['momentum_score']:.1f}</div>
                  <div style="margin-top:6px;">
                    <span style="color:#34d399 if {row['return_1m']} >= 0 else #f87171;
                                 font-size:0.82rem;">1M: {row['return_1m']:+.1f}%</span>
                  </div>
                  <div style="font-size:0.78rem;color:#64748b;margin-top:4px;">{row['technical_signal']}</div>
                </div>""", unsafe_allow_html=True)

        # Full table
        st.markdown('<div class="section-header">📋 ตารางเปรียบเทียบ</div>', unsafe_allow_html=True)
        disp_screen = screen_df[["ticker","latest_close","return_1m","return_3m","volatility",
                                  "technical_score","technical_signal","pattern_score","momentum_score"]].copy()
        disp_screen.columns = ["Ticker","ราคา ($)","1M%","3M%","Volatility%","Tech Score","Signal","Pattern","Momentum"]
        disp_screen["ราคา ($)"] = disp_screen["ราคา ($)"].map(lambda x: f"${x:,.2f}")
        st.dataframe(disp_screen, use_container_width=True, hide_index=True)

        # Momentum bar chart
        fig_mom = go.Figure(go.Bar(
            x=screen_df["ticker"], y=screen_df["momentum_score"],
            marker_color=[PALETTE.get(t, DEFAULT_PALETTE_COLOR) for t in screen_df["ticker"]],
            text=screen_df["momentum_score"].map(lambda x: f"{x:.1f}"), textposition="outside",
        ))
        fig_mom.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", title="Momentum Score"),
            xaxis=dict(color="#475569"), showlegend=False)
        st.plotly_chart(fig_mom, use_container_width=True)

        # AI Commentary
        if commentary:
            st.markdown('<div class="section-header">🤖 AI สรุป Sector</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ai-card">{commentary}</div>', unsafe_allow_html=True)
    else:
        st.info("กด 'Scan Sector' เพื่อดูหุ้นที่กำลังมาแรงในอุตสาหกรรมนั้น")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — DECISION SUMMARY
# ════════════════════════════════════════════════════════════════════════════
with tab_decision:
    st.markdown('<div class="section-header">🎯 Investment Decision Summary</div>', unsafe_allow_html=True)
    st.caption("สรุปคำแนะนำจากทุกมิติ — ช่วยตัดสินใจว่าควร ซื้อ / ถือ / ขาย")

    if ai_result.empty:
        st.warning("⚠️ ยังไม่มีผล AI Analysis — ไปที่หน้า **Analysis** แล้วกด 'วิเคราะห์ด้วย AI' ก่อนครับ")
    else:
        for ticker in tickers:
            t_row = scoreboard[scoreboard["ticker"]==ticker]
            a_row = ai_result[ai_result["ticker"]==ticker]
            if t_row.empty or a_row.empty: continue
            t = t_row.iloc[0]; a = a_row.iloc[0]

            rec    = a.get("recommendation","Hold")
            color  = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)
            cls    = "rec-buy" if rec=="Buy" else "rec-hold" if rec=="Hold" else "rec-sell"
            reason = a.get("reason","")

            st.markdown(f"""
            <div class="decision-card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <div>
                  <span style="font-family:'Space Mono',monospace;font-size:1.4rem;
                               font-weight:700;color:{color};">{ticker}</span>
                  <span style="color:#64748b;font-size:0.82rem;margin-left:10px;">
                    ${t.get('latest_close',0):,.2f}
                  </span>
                </div>
                <span class="{cls}" style="font-size:1rem;padding:6px 20px;">⚡ {rec}</span>
              </div>
              <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px;">
                <div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Technical</div>
                  <div style="color:#e2e8f0;font-size:0.88rem;margin-top:4px;">{t.get('technical_signal','N/A')}</div>
                  <div style="color:#64748b;font-size:0.72rem;">{t.get('technical_score',0):.0f}/100</div>
                </div>
                <div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Pattern</div>
                  <div style="color:#e2e8f0;font-size:0.88rem;margin-top:4px;">{t.get('pattern_score',0):.0f}/100</div>
                  <div style="color:#64748b;font-size:0.72rem;">{t.get('pattern_label','N/A').split()[0]}</div>
                </div>
                <div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">AI Sentiment</div>
                  <div style="color:#e2e8f0;font-size:0.88rem;margin-top:4px;">{a.get('sentiment_label','N/A')}</div>
                  <div style="color:#64748b;font-size:0.72rem;">{a.get('sentiment_score',0):.0f}/100</div>
                </div>
                <div style="background:#0d1117;border-radius:8px;padding:10px;text-align:center;">
                  <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Combined</div>
                  <div style="color:{color};font-size:1.1rem;font-weight:700;margin-top:4px;">
                    {a.get('combined_score',0):.1f}
                  </div>
                  <div style="color:#64748b;font-size:0.72rem;">/100</div>
                </div>
              </div>
              <div style="background:#0d1117;border-radius:8px;padding:10px;
                          color:#94a3b8;font-size:0.82rem;line-height:1.6;">
                💡 {reason}
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Summary bar chart
        st.markdown('<div class="section-header">📊 Combined Score เปรียบเทียบ</div>', unsafe_allow_html=True)
        merged_dec = scoreboard.merge(ai_result[["ticker","combined_score","recommendation"]], on="ticker", how="left")
        if "recommendation" not in merged_dec.columns:
            merged_dec["recommendation"] = "Hold"
        if "combined_score" not in merged_dec.columns:
            merged_dec["combined_score"] = 50.0
        merged_dec["recommendation"] = merged_dec["recommendation"].fillna("Hold")
        merged_dec["combined_score"]  = merged_dec["combined_score"].fillna(50.0)
        colors_dec = [
            "#34d399" if r=="Buy" else "#f87171" if r=="Sell" else "#f59e0b"
            for r in merged_dec["recommendation"]
        ]
        fig_dec = go.Figure(go.Bar(
            x=merged_dec["ticker"], y=merged_dec["combined_score"],
            marker_color=colors_dec,
            text=merged_dec.apply(lambda r: f"{r['combined_score']:.1f} ({r['recommendation']})", axis=1),
            textposition="outside",
        ))
        fig_dec.add_hline(y=68, line_dash="dash", line_color="#34d399", opacity=0.5,
                          annotation_text="Buy zone (≥68)")
        fig_dec.add_hline(y=45, line_dash="dash", line_color="#f87171", opacity=0.5,
                          annotation_text="Sell zone (<45)")
        fig_dec.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569",
                       range=[0,105], title="Combined Score"),
            xaxis=dict(color="#475569"), showlegend=False)
        st.plotly_chart(fig_dec, use_container_width=True)

        st.caption("""
        **Combined Score** = Technical (35%) + Pattern (35%) + AI Sentiment (30%)
        — Score ≥ 68 = Buy zone | 45-67 = Hold | < 45 = Sell zone
        """)

st.caption("Educational demo only. This is not financial advice.")
