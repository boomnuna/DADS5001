"""
pages/1_Stock_Selection.py
เลือกหุ้น + บันทึก Watchlist ลง MongoDB + แสดง snapshot
"""

import streamlit as st
import plotly.graph_objects as go

from src.config import SUPPORTED_TICKERS, DEFAULT_TICKERS, PALETTE, DEFAULT_PALETTE_COLOR
from src.data_pipeline import load_prices, duckdb_price_summary, get_current_price
from src.storage import save_watchlist, load_watchlist, load_search_history, mongo_status

st.set_page_config(page_title="Stock Selection", page_icon="🎯", layout="wide")

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

st.markdown("## 🎯 เลือกหุ้น")
st.caption("เลือกหุ้นสูงสุด 3 ตัวสำหรับการวิเคราะห์ — ระบบจะดึงข้อมูลจริงจาก Yahoo Finance")

# ── Session init ───────────────────────────────────────────────────────────────
if "selected_tickers" not in st.session_state:
    saved = load_watchlist()
    st.session_state.selected_tickers = saved if saved else DEFAULT_TICKERS.copy()
if "analysis_mode" not in st.session_state:
    st.session_state.analysis_mode = "AI mode"

# ── Select + Mode ──────────────────────────────────────────────────────────────
col_sel, col_mode = st.columns([3, 1])
with col_sel:
    selected = st.multiselect(
        "หุ้นที่ต้องการวิเคราะห์ (สูงสุด 3 ตัว)",
        options=SUPPORTED_TICKERS,
        default=st.session_state.selected_tickers,
        max_selections=3,
    )
with col_mode:
    st.markdown("<br>", unsafe_allow_html=True)
    mode = st.radio("Analysis Mode", ["Non-AI mode", "AI mode"], horizontal=True,
                    index=1 if st.session_state.analysis_mode == "AI mode" else 0)

if not selected:
    selected = DEFAULT_TICKERS.copy()
    st.warning("กรุณาเลือกหุ้นอย่างน้อย 1 ตัว — ใช้ค่า default")

st.session_state.selected_tickers = selected
st.session_state.analysis_mode    = mode

# ── Save to MongoDB ────────────────────────────────────────────────────────────
col_save, col_status = st.columns([1, 3])
with col_save:
    if st.button("💾 บันทึก Watchlist → MongoDB", use_container_width=True, type="primary"):
        msg = save_watchlist(selected)
        st.success(msg)
with col_status:
    st.markdown(f'<div style="padding-top:8px;color:#64748b;font-size:0.82rem;">{mongo_status()}</div>',
                unsafe_allow_html=True)

st.divider()

# ── Load data ──────────────────────────────────────────────────────────────────
with st.spinner("กำลังดึงข้อมูลจาก Yahoo Finance..."):
    prices  = load_prices(tuple(selected))
    summary = duckdb_price_summary(prices)

if prices.empty:
    st.error("❌ ไม่สามารถดึงข้อมูลได้ กรุณาตรวจสอบ internet connection")
    st.stop()

# ── Current Price Cards ────────────────────────────────────────────────────────
st.markdown('<div class="section-header">💲 ราคาปัจจุบัน</div>', unsafe_allow_html=True)
cols = st.columns(len(selected))
for i, ticker in enumerate(selected):
    info   = get_current_price(ticker)
    color  = "normal" if info["change_pct"] >= 0 else "inverse"
    arrow  = "▲" if info["change_pct"] >= 0 else "▼"
    with cols[i]:
        st.metric(
            f"{arrow} {ticker}",
            f"${info['price']:,.2f}",
            f"{info['change_pct']:+.2f}%",
            delta_color=color,
        )

st.divider()

# ── DuckDB Summary Table ───────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 สรุปข้อมูล (DuckDB SQL)</div>', unsafe_allow_html=True)
if not summary.empty:
    disp = summary[["ticker","latest_close","return_1m","return_3m","return_6m","volatility","latest_volume"]].copy()
    disp.columns = ["Ticker","ราคาล่าสุด ($)","Return 1M%","Return 3M%","Return 6M%","Volatility%","Volume"]
    disp["ราคาล่าสุด ($)"] = disp["ราคาล่าสุด ($)"].map(lambda x: f"${x:,.2f}")
    disp["Volume"]         = disp["Volume"].map(lambda x: f"{int(x):,}")
    st.dataframe(disp, use_container_width=True, hide_index=True)

# ── Price Chart ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📈 กราฟราคาย้อนหลัง (Normalized Base=100)</div>', unsafe_allow_html=True)
fig = go.Figure()
for ticker in selected:
    df = prices[prices["ticker"] == ticker].sort_values("date")
    if df.empty:
        continue
    indexed = df["close"] / df["close"].iloc[0] * 100
    color   = PALETTE.get(ticker, DEFAULT_PALETTE_COLOR)
    fig.add_trace(go.Scatter(
        x=df["date"], y=indexed, name=ticker,
        line=dict(color=color, width=2),
        hovertemplate=f"{ticker}: %{{y:.1f}}<extra></extra>",
    ))
fig.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.2)")
fig.update_layout(
    height=350, margin=dict(l=0,r=0,t=10,b=0),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569", title="Indexed (Base=100)"),
    xaxis=dict(showgrid=False, color="#475569"),
    legend=dict(font=dict(color="#94a3b8", size=12), orientation="h", y=1.08),
)
st.plotly_chart(fig, use_container_width=True)

# ── Search History ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🕐 ประวัติการค้นหาจาก MongoDB</div>', unsafe_allow_html=True)
history = load_search_history(5)
if history:
    for h in history:
        tickers_str = ", ".join(h["tickers"])
        time_str    = h["time"].strftime("%d/%m/%Y %H:%M") if hasattr(h["time"], "strftime") else str(h["time"])
        st.markdown(
            f'<div style="background:#111827;border:1px solid rgba(255,255,255,0.06);'
            f'border-radius:8px;padding:8px 14px;margin-bottom:6px;'
            f'display:flex;justify-content:space-between;">'
            f'<span style="color:#e2e8f0;">📋 {tickers_str}</span>'
            f'<span style="color:#475569;font-size:0.78rem;">{time_str}</span></div>',
            unsafe_allow_html=True,
        )
else:
    st.caption("ยังไม่มีประวัติการค้นหา — กด 'บันทึก Watchlist' เพื่อเริ่มบันทึก")

st.caption("Educational demo only. This is not financial advice.")
