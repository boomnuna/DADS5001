"""
pages/5_🔀_Compare.py
เปรียบเทียบหุ้นหลายตัวพร้อมกัน — ราคา, Performance, Fundamentals
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.data_fetcher import get_current_price, get_multi_prices

st.set_page_config(page_title="Compare — TradeX", layout="wide", page_icon="🔀")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .section-header { font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;
    letter-spacing:0.12em;margin:20px 0 10px;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px; }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🔀 เปรียบเทียบหุ้น")
st.caption("เปรียบเทียบข้อมูลพื้นฐานของหุ้นหลายตัวพร้อมกัน (สูงสุด 5 ตัว)")

# ── Symbol Input ───────────────────────────────────────────────────────────────
col_in, col_period, col_btn = st.columns([3, 1.2, 1])
with col_in:
    raw = st.text_input("หุ้นที่ต้องการเปรียบเทียบ (คั่นด้วย comma)",
                        value="AAPL, TSLA, NVDA, MSFT, AMZN",
                        placeholder="เช่น AAPL, MSFT, GOOGL")
with col_period:
    period = st.selectbox("ช่วงเวลา", ["1mo","3mo","6mo","1y","2y"], index=3)
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("🔀 เปรียบเทียบ", use_container_width=True, type="primary")

symbols = [s.strip().upper() for s in raw.split(",") if s.strip()][:5]

if run or symbols:
    # ── Load Fundamentals ──────────────────────────────────────────────────────
    with st.spinner("กำลังดึงข้อมูล..."):
        infos = {sym: get_current_price(sym) for sym in symbols}
        price_df = get_multi_prices(symbols, period)

    # ── Performance Chart (Normalized) ────────────────────────────────────────
    if not price_df.empty:
        st.markdown('<div class="section-header">📈 ผลตอบแทนเทียบกัน (Normalized Base=100)</div>', unsafe_allow_html=True)

        norm_df = price_df.div(price_df.iloc[0]) * 100
        colors  = ["#00D4FF","#7C3AED","#f59e0b","#10b981","#f43f5e"]

        fig = go.Figure()
        for i, sym in enumerate(symbols):
            if sym in norm_df.columns:
                final_val = norm_df[sym].iloc[-1]
                ret_pct   = final_val - 100
                fig.add_trace(go.Scatter(
                    x=norm_df.index, y=norm_df[sym],
                    name=f"{sym} ({ret_pct:+.1f}%)",
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate=f"{sym}: %{{y:.1f}}<extra></extra>",
                ))
        fig.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.2)")
        fig.update_layout(
            height=380, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", title="Normalized (Base=100)"),
            xaxis=dict(showgrid=False, color="#475569"),
            legend=dict(font=dict(color="#94a3b8",size=12), orientation="h", y=1.08),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Return Bar Chart ───────────────────────────────────────────────────
        st.markdown('<div class="section-header">📊 ผลตอบแทนรวม (%)</div>', unsafe_allow_html=True)
        ret_data = []
        for sym in symbols:
            if sym in norm_df.columns:
                ret = norm_df[sym].iloc[-1] - 100
                ret_data.append({"Symbol": sym, "Return%": round(ret,2)})
        if ret_data:
            df_ret = pd.DataFrame(ret_data).sort_values("Return%", ascending=False)
            bar_colors = ["#34d399" if v >= 0 else "#f87171" for v in df_ret["Return%"]]
            fig_bar = go.Figure(go.Bar(
                x=df_ret["Symbol"], y=df_ret["Return%"],
                marker_color=bar_colors,
                text=df_ret["Return%"].map(lambda x: f"{x:+.2f}%"),
                textposition="outside",
            ))
            fig_bar.update_layout(
                height=250, margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
                xaxis=dict(color="#475569"), showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # ── Fundamentals Table ─────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📋 เปรียบเทียบข้อมูลพื้นฐาน</div>', unsafe_allow_html=True)
    rows = []
    for sym in symbols:
        info = infos.get(sym, {})
        rows.append({
            "หุ้น":          sym,
            "ราคา ($)":     info.get("price",0),
            "เปลี่ยน%":     f"{info.get('change_pct',0):+.2f}%",
            "Market Cap":   f"${info.get('market_cap',0)/1e9:.1f}B" if info.get("market_cap") else "N/A",
            "P/E":          f"{info.get('pe_ratio'):.1f}" if info.get("pe_ratio") else "N/A",
            "EPS ($)":      f"{info.get('eps'):.2f}" if info.get("eps") else "N/A",
            "Beta":         f"{info.get('beta'):.2f}" if info.get("beta") else "N/A",
            "Target ($)":   f"{info.get('target_mean'):.2f}" if info.get("target_mean") else "N/A",
            "Upside%":      f"{(info.get('target_mean',0)/info.get('price',1)-1)*100:+.1f}%" if info.get("target_mean") and info.get("price") else "N/A",
            "Sector":       info.get("sector","N/A"),
            "Analyst":      info.get("recommendation","N/A").upper(),
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── Radar Chart ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">🕸️ Radar Chart — เปรียบเทียบมิติต่างๆ</div>', unsafe_allow_html=True)
    st.caption("(Normalized: ค่ายิ่งสูงยิ่งดี สำหรับแต่ละมิติ)")

    categories = ["Upside Potential", "Low P/E", "Low Beta", "EPS", "Market Cap"]
    fig_radar = go.Figure()
    colors_r = ["#00D4FF","#7C3AED","#f59e0b","#10b981","#f43f5e"]

    all_pe  = [infos[s].get("pe_ratio") or 0 for s in symbols]
    all_eps = [infos[s].get("eps") or 0 for s in symbols]
    all_mc  = [infos[s].get("market_cap") or 0 for s in symbols]
    all_beta= [infos[s].get("beta") or 1 for s in symbols]
    all_up  = [(infos[s].get("target_mean",0)/(infos[s].get("price",1) or 1)-1)*100 for s in symbols]

    def norm(arr):
        mn, mx = min(arr), max(arr)
        if mx == mn: return [5]*len(arr)
        return [(v-mn)/(mx-mn)*10 for v in arr]

    norm_up   = norm(all_up)
    norm_pe   = norm([-p for p in all_pe])   # invert: low PE = good
    norm_beta = norm([-b for b in all_beta])  # invert: low beta = good
    norm_eps  = norm(all_eps)
    norm_mc   = norm(all_mc)

    for i, sym in enumerate(symbols):
        vals = [norm_up[i], norm_pe[i], norm_beta[i], norm_eps[i], norm_mc[i]]
        fig_radar.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=categories + [categories[0]],
            name=sym, fill="toself",
            line_color=colors_r[i % len(colors_r)],
            fillcolor=f"rgba({int(colors_r[i % len(colors_r)][1:3], 16)}, {int(colors_r[i % len(colors_r)][3:5], 16)}, {int(colors_r[i % len(colors_r)][5:7], 16)}, 0.08)",
            opacity=0.8,
        ))

    fig_radar.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0,10], color="#475569", gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(color="#94a3b8"),
        ),
        height=380, margin=dict(l=20,r=20,t=20,b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color="#94a3b8",size=12), orientation="h", y=-0.1),
        showlegend=True,
    )
    st.plotly_chart(fig_radar, use_container_width=True)
