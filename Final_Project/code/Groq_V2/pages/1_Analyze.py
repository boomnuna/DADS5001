"""
pages/1_🔍_Analyze.py
รวม Stock Analysis + Compare เป็น 2 tabs
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.data_fetcher import (
    get_current_price, get_price_history, compute_technicals,
    get_news, get_analyst_targets, query_duckdb, get_multi_prices
)

st.set_page_config(page_title="Analyze — SmartInvest", layout="wide", page_icon="🔍")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .section-header { font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;
    letter-spacing:0.12em;margin:20px 0 10px;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px; }
</style>
""", unsafe_allow_html=True)

tab_analysis, tab_compare = st.tabs(["📊 วิเคราะห์หุ้น", "🔀 เปรียบเทียบหุ้น"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — STOCK ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analysis:
    st.markdown("## 🔍 วิเคราะห์หุ้น")
    st.caption("ดึงข้อมูลราคาจริง, Technical Indicators และ Analyst Targets จากตลาดจริง")

    col_search, col_period, col_btn = st.columns([3, 1, 1])
    with col_search:
        symbol = st.text_input("ค้นหาหุ้น", placeholder="เช่น AAPL, TSLA, NVDA...",
                               value=st.session_state.get("analysis_symbol","AAPL"), key="sa_symbol").upper().strip()
    with col_period:
        period = st.selectbox("ช่วงเวลา", ["1mo","3mo","6mo","1y","2y","5y"], index=3, key="sa_period")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("🔍 วิเคราะห์", use_container_width=True, type="primary", key="sa_run")

    if run or symbol:
        st.session_state["analysis_symbol"] = symbol
        with st.spinner(f"กำลังดึงข้อมูล {symbol}..."):
            info   = get_current_price(symbol)
            df_raw = get_price_history(symbol, period)

        if df_raw.empty:
            st.error(f"❌ ไม่พบข้อมูลสำหรับ {symbol}")
        else:
            df = compute_technicals(df_raw)
            price = info["price"]; chg_p = info["change_pct"]

            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("💲 ราคาปัจจุบัน", f"${price:,.2f}", f"{chg_p:+.2f}%",
                      delta_color="normal" if chg_p>=0 else "inverse")
            c2.metric("📊 P/E Ratio",    f"{info['pe_ratio']:.1f}" if info["pe_ratio"] else "N/A")
            c3.metric("🎯 Target Price", f"${info['target_mean']:,.2f}" if info["target_mean"] else "N/A")
            c4.metric("⚡ Beta",         f"{info['beta']:.2f}" if info["beta"] else "N/A")
            c5.metric("🏦 Mkt Cap",      f"${info['market_cap']/1e9:.1f}B" if info["market_cap"] else "N/A")

            rec = info.get("recommendation","").upper()
            rec_color = {"STRONG BUY":"#10b981","BUY":"#34d399","HOLD":"#f59e0b","SELL":"#f87171","STRONG SELL":"#ef4444"}.get(rec,"#64748b")
            st.markdown(f'<div style="margin:4px 0 16px;"><span style="background:{rec_color}22;color:{rec_color};border:1px solid {rec_color}44;padding:4px 14px;border-radius:20px;font-size:0.8rem;font-weight:600;">Analyst: {rec or "N/A"}</span> <span style="color:#475569;font-size:0.8rem;">{info["name"]} • {info["sector"]}</span></div>', unsafe_allow_html=True)

            st.divider()
            inner1, inner2, inner3, inner4 = st.tabs(["📈 กราฟ & Technical","📋 Fundamentals","📰 ข่าว","🗄️ DuckDB SQL"])

            with inner1:
                show_ma = st.checkbox("Moving Averages", value=True, key="sa_ma")
                show_bb = st.checkbox("Bollinger Bands", value=False, key="sa_bb")
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                    row_heights=[0.55,0.25,0.2], vertical_spacing=0.03)
                fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
                    low=df["Low"], close=df["Close"],
                    increasing_line_color="#34d399", decreasing_line_color="#f87171"), row=1, col=1)
                if show_ma:
                    for ma,color,dash in [("MA20","#00D4FF","solid"),("MA50","#f59e0b","dash"),("MA200","#a78bfa","dot")]:
                        fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma,
                            line=dict(color=color,width=1.2,dash=dash), opacity=0.8), row=1, col=1)
                if show_bb:
                    fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper",
                        line=dict(color="#64748b",width=1,dash="dot"), opacity=0.5), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower",
                        line=dict(color="#64748b",width=1,dash="dot"), fill="tonexty",
                        fillcolor="rgba(100,116,139,0.06)", opacity=0.5), row=1, col=1)
                vol_colors = ["#34d399" if c>=o else "#f87171" for c,o in zip(df["Close"],df["Open"])]
                fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=vol_colors, opacity=0.6), row=2, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], line=dict(color="#7C3AED",width=1.5), name="RSI"), row=3, col=1)
                for level,color in [(70,"#f87171"),(30,"#34d399")]:
                    fig.add_hline(y=level, line_dash="dash", line_color=color, opacity=0.5, row=3, col=1)
                fig.update_layout(height=600, margin=dict(l=0,r=0,t=10,b=0),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis_rangeslider_visible=False,
                    yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,0.05)",color="#475569"),
                    yaxis2=dict(showgrid=False,color="#475569"),
                    yaxis3=dict(showgrid=False,color="#475569",title="RSI"),
                    legend=dict(font=dict(color="#94a3b8",size=11),orientation="h",y=1.02))
                st.plotly_chart(fig, use_container_width=True)
                last = df.iloc[-1]
                t1,t2,t3 = st.columns(3)
                t1.metric("RSI (14)", f"{last['RSI']:.1f}", "🔴 Overbought" if last['RSI']>70 else "🟢 Oversold" if last['RSI']<30 else "🟡 Neutral")
                t2.metric("MACD Signal", "🟢 Bullish" if last['MACD']>last['MACD_Signal'] else "🔴 Bearish")
                t3.metric("Trend (MA200)", "🟢 Uptrend" if price>last['MA200'] else "🔴 Downtrend")

            with inner2:
                fa, fb = st.columns(2)
                with fa:
                    st.markdown('<div class="section-header">📊 ข้อมูลพื้นฐาน</div>', unsafe_allow_html=True)
                    for k,v in {
                        "💲 ราคา":f"${price:,.2f}","📈 เปลี่ยนแปลง":f"{chg_p:+.2f}%",
                        "🏦 Market Cap":f"${info['market_cap']/1e9:.2f}B" if info["market_cap"] else "N/A",
                        "📊 P/E Ratio":f"{info['pe_ratio']:.2f}" if info["pe_ratio"] else "N/A",
                        "💰 EPS":f"${info['eps']:.2f}" if info["eps"] else "N/A",
                        "⚡ Beta":f"{info['beta']:.2f}" if info["beta"] else "N/A",
                        "🎯 Target":f"${info['target_mean']:,.2f}" if info["target_mean"] else "N/A",
                        "📅 52W High":f"${info['52w_high']:,.2f}" if info["52w_high"] else "N/A",
                        "📅 52W Low":f"${info['52w_low']:,.2f}" if info["52w_low"] else "N/A",
                    }.items():
                        cols = st.columns([2,1])
                        cols[0].markdown(f'<span style="color:#94a3b8;font-size:0.85rem;">{k}</span>', unsafe_allow_html=True)
                        cols[1].markdown(f'<span style="font-family:Space Mono,monospace;font-size:0.85rem;color:#e2e8f0;">{v}</span>', unsafe_allow_html=True)
                with fb:
                    st.markdown('<div class="section-header">🏢 บริษัท</div>', unsafe_allow_html=True)
                    st.markdown(f'**{info["name"]}**')
                    desc = info.get("description","")
                    if desc:
                        st.markdown(f'<div style="color:#94a3b8;font-size:0.83rem;line-height:1.6;">{desc[:600]}...</div>', unsafe_allow_html=True)
                    df_rec = get_analyst_targets(symbol)
                    if not df_rec.empty:
                        st.markdown('<div class="section-header">🎯 Analyst Recommendations</div>', unsafe_allow_html=True)
                        st.dataframe(df_rec.tail(5), use_container_width=True)

            with inner3:
                news_list = get_news(symbol)
                if news_list:
                    for item in news_list:
                        content = item.get("content", item)
                        title   = content.get("title", item.get("title",""))
                        summary = content.get("summary", item.get("summary",""))
                        url     = content.get("canonicalUrl",{}).get("url", item.get("link","#"))
                        st.markdown(f"""<div style="background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:14px;margin-bottom:10px;">
                          <a href="{url}" target="_blank" style="color:#00D4FF;font-weight:600;font-size:0.9rem;text-decoration:none;">{title}</a>
                          <div style="color:#64748b;font-size:0.82rem;margin-top:6px;">{summary[:200] if summary else ""}...</div>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.info("ไม่พบข่าวล่าสุด")

            with inner4:
                st.info("ตารางที่ใช้ได้: `price_data`")
                default_sql = "SELECT CAST(index AS DATE) AS date, ROUND(Close,2) AS close, ROUND(RSI,2) AS rsi FROM price_data WHERE RSI IS NOT NULL ORDER BY index DESC LIMIT 20"
                sql_query = st.text_area("SQL Query", value=default_sql, height=120, key="sa_sql")
                if st.button("▶️ Run Query", type="primary", key="sa_run_sql"):
                    result = query_duckdb(sql_query)
                    if not result.empty and "error" not in result.columns:
                        st.success(f"✅ {len(result)} rows")
                        st.dataframe(result, use_container_width=True)
                    else:
                        st.error("Query error")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — COMPARE
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown("## 🔀 เปรียบเทียบหุ้น")
    st.caption("เปรียบเทียบหุ้นหลายตัวพร้อมกัน (สูงสุด 5 ตัว)")

    col_in, col_period2, col_btn2 = st.columns([3, 1.2, 1])
    with col_in:
        raw = st.text_input("หุ้นที่ต้องการเปรียบเทียบ (คั่นด้วย comma)",
                            value="AAPL, TSLA, NVDA, MSFT, AMZN", key="cmp_input")
    with col_period2:
        period2 = st.selectbox("ช่วงเวลา", ["1mo","3mo","6mo","1y","2y"], index=3, key="cmp_period")
    with col_btn2:
        st.markdown("<br>", unsafe_allow_html=True)
        run2 = st.button("🔀 เปรียบเทียบ", use_container_width=True, type="primary", key="cmp_run")

    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()][:5]

    if run2 or symbols:
        with st.spinner("กำลังดึงข้อมูล..."):
            infos    = {sym: get_current_price(sym) for sym in symbols}
            price_df = get_multi_prices(symbols, period2)

        if not price_df.empty:
            st.markdown('<div class="section-header">📈 ผลตอบแทนเทียบกัน (Normalized Base=100)</div>', unsafe_allow_html=True)
            norm_df = price_df.div(price_df.iloc[0]) * 100
            colors  = ["#00D4FF","#7C3AED","#f59e0b","#10b981","#f43f5e"]
            fig = go.Figure()
            for i, sym in enumerate(symbols):
                if sym in norm_df.columns:
                    ret = norm_df[sym].iloc[-1] - 100
                    fig.add_trace(go.Scatter(x=norm_df.index, y=norm_df[sym],
                        name=f"{sym} ({ret:+.1f}%)",
                        line=dict(color=colors[i%len(colors)], width=2)))
            fig.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.2)")
            fig.update_layout(height=380, margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,0.05)",color="#475569"),
                xaxis=dict(showgrid=False,color="#475569"),
                legend=dict(font=dict(color="#94a3b8",size=12),orientation="h",y=1.08))
            st.plotly_chart(fig, use_container_width=True)

        # Fundamentals table
        st.markdown('<div class="section-header">📋 เปรียบเทียบข้อมูลพื้นฐาน</div>', unsafe_allow_html=True)
        rows = []
        for sym in symbols:
            info = infos.get(sym,{})
            rows.append({"หุ้น":sym,"ราคา ($)":info.get("price",0),
                "เปลี่ยน%":f"{info.get('change_pct',0):+.2f}%",
                "Market Cap":f"${info.get('market_cap',0)/1e9:.1f}B" if info.get("market_cap") else "N/A",
                "P/E":f"{info.get('pe_ratio'):.1f}" if info.get("pe_ratio") else "N/A",
                "Beta":f"{info.get('beta'):.2f}" if info.get("beta") else "N/A",
                "Target ($)":f"{info.get('target_mean'):.2f}" if info.get("target_mean") else "N/A",
                "Upside%":f"{(info.get('target_mean',0)/info.get('price',1)-1)*100:+.1f}%" if info.get("target_mean") and info.get("price") else "N/A",
                "Analyst":info.get("recommendation","N/A").upper()})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Radar Chart
        st.markdown('<div class="section-header">🕸️ Radar Chart</div>', unsafe_allow_html=True)
        categories = ["Upside Potential","Low P/E","Low Beta","EPS","Market Cap"]
        fig_radar  = go.Figure()
        colors_r   = ["#00D4FF","#7C3AED","#f59e0b","#10b981","#f43f5e"]
        rgba_colors= ["rgba(0,212,255,0.08)","rgba(124,58,237,0.08)","rgba(245,158,11,0.08)","rgba(16,185,129,0.08)","rgba(244,63,94,0.08)"]

        def norm(arr):
            mn,mx = min(arr),max(arr)
            return [5]*len(arr) if mx==mn else [(v-mn)/(mx-mn)*10 for v in arr]

        all_up   = [(infos[s].get("target_mean",0)/(infos[s].get("price",1) or 1)-1)*100 for s in symbols]
        all_pe   = [infos[s].get("pe_ratio") or 0 for s in symbols]
        all_beta = [infos[s].get("beta") or 1 for s in symbols]
        all_eps  = [infos[s].get("eps") or 0 for s in symbols]
        all_mc   = [infos[s].get("market_cap") or 0 for s in symbols]
        n_up,n_pe,n_beta,n_eps,n_mc = norm(all_up),norm([-p for p in all_pe]),norm([-b for b in all_beta]),norm(all_eps),norm(all_mc)

        for i,sym in enumerate(symbols):
            vals = [n_up[i],n_pe[i],n_beta[i],n_eps[i],n_mc[i]]
            fig_radar.add_trace(go.Scatterpolar(r=vals+[vals[0]], theta=categories+[categories[0]],
                name=sym, fill="toself", line_color=colors_r[i%len(colors_r)],
                fillcolor=rgba_colors[i%len(rgba_colors)], opacity=0.8))
        fig_radar.update_layout(
            polar=dict(bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True,range=[0,10],color="#475569",gridcolor="rgba(255,255,255,0.1)"),
                angularaxis=dict(color="#94a3b8")),
            height=380, margin=dict(l=20,r=20,t=20,b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(font=dict(color="#94a3b8",size=12),orientation="h",y=-0.1))
        st.plotly_chart(fig_radar, use_container_width=True)
