"""
Home.py — TradeX Dashboard หน้าหลัก
ภาพรวมพอร์ต + หุ้น Watchlist + ข้อมูล Market
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ── Import utilities ──────────────────────────────────────────────────────────
from utils.data_fetcher import get_current_price, get_price_history, get_multi_prices
from utils.db_mongo import load_portfolio, load_watchlist, save_watchlist
from utils.db_snowflake import load_portfolio_history, setup_tables

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TradeX — Trading Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');

  /* Global */
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: linear-gradient(135deg, #111827 0%, #1a2235 100%);
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 12px;
    padding: 16px 20px;
  }
  [data-testid="metric-container"] label {
    color: #64748b !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  [data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace !important;
    font-size: 1.5rem !important;
    color: #e2e8f0 !important;
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid rgba(0,212,255,0.1);
  }

  /* Section headers */
  .section-header {
    font-size: 0.7rem;
    font-weight: 600;
    color: #00D4FF;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin: 24px 0 12px 0;
    border-bottom: 1px solid rgba(0,212,255,0.2);
    padding-bottom: 6px;
  }

  /* Stock badge */
  .stock-badge-up   { background:#064e3b; color:#34d399; padding:2px 8px; border-radius:6px; font-family:'Space Mono',monospace; font-size:0.78rem; }
  .stock-badge-down { background:#450a0a; color:#f87171; padding:2px 8px; border-radius:6px; font-family:'Space Mono',monospace; font-size:0.78rem; }

  /* Logo */
  .tradex-logo {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    background: linear-gradient(90deg, #00D4FF, #7C3AED);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
  }
  .tradex-sub { font-size: 0.72rem; color: #475569; letter-spacing: 0.1em; }

  /* Card */
  .info-card {
    background: #111827;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 8px;
  }
  div[data-testid="stHorizontalBlock"] { gap: 1rem; }
</style>
""", unsafe_allow_html=True)

# สร้างตาราง Snowflake ถ้ายังไม่มี
setup_tables()

# # ── Session State ─────────────────────────────────────────────────────────────
# if "user_id"   not in st.session_state: st.session_state.user_id   = "default"
# if "portfolio" not in st.session_state: st.session_state.portfolio = load_portfolio()
# if "watchlist" not in st.session_state: st.session_state.watchlist = load_watchlist()
# ── Sidebar ───────────────────────────────────────────────────────────────────
if "user_id"   not in st.session_state: st.session_state.user_id   = "default"
if "portfolio" not in st.session_state:
    loaded = load_portfolio()
    if not loaded:
        # Mock data สำหรับ demo
        # ✅ ใหม่ — ลบ market_value ออก ให้คำนวณจากราคาจริง
        loaded = [
            {"symbol": "AAPL", "qty": 10, "avg_cost": 170.0},
            {"symbol": "TSLA", "qty": 5,  "avg_cost": 200.0},
            {"symbol": "NVDA", "qty": 8,  "avg_cost": 450.0},
            {"symbol": "MSFT", "qty": 6,  "avg_cost": 330.0},
            {"symbol": "AMZN", "qty": 4,  "avg_cost": 140.0},
        ]
    st.session_state.portfolio = loaded
if "watchlist" not in st.session_state: st.session_state.watchlist = load_watchlist()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="tradex-logo">TradeX</div>', unsafe_allow_html=True)
    st.markdown('<div class="tradex-sub">TRADING ANALYTICS</div>', unsafe_allow_html=True)
    st.divider()

    st.markdown('<div class="section-header">⚙️ Watchlist</div>', unsafe_allow_html=True)
    default_watchlist = st.session_state.watchlist or ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]
    watchlist_input = st.text_area(
        "หุ้นที่ติดตาม (คั่นด้วยจุลภาค)",
        value=", ".join(default_watchlist),
        height=80,
    )
    if st.button("💾 บันทึก Watchlist", use_container_width=True):
        symbols = [s.strip().upper() for s in watchlist_input.split(",") if s.strip()]
        st.session_state.watchlist = symbols
        save_watchlist(st.session_state.user_id, symbols)
        st.success("บันทึกแล้ว!")
        st.rerun()

    st.divider()
    st.markdown(f'<div style="color:#475569;font-size:0.72rem;">🕐 {datetime.now().strftime("%d %b %Y %H:%M")}</div>', unsafe_allow_html=True)


# ── Main Content ──────────────────────────────────────────────────────────────
st.markdown("## 📊 ภาพรวมพอร์ตการลงทุน")

# ─ Portfolio Summary ─
holdings = st.session_state.portfolio
# ✅ ใหม่ — คำนวณจากราคาปัจจุบันจริง
total_value = sum(
    get_current_price(h["symbol"])["price"] * h.get("qty", 0)
    for h in holdings
)
total_cost   = sum(h.get("qty", 0) * h.get("avg_cost", 0) for h in holdings)
total_pnl    = total_value - total_cost
total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
n_stocks     = len(holdings)

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 มูลค่ารวม",  f"${total_value:,.2f}",  f"{total_pnl_pct:+.2f}%")
col2.metric("💵 ต้นทุนรวม",  f"${total_cost:,.2f}")
col3.metric("📈 กำไร/ขาดทุน", f"${total_pnl:+,.2f}",  delta_color="normal" if total_pnl >= 0 else "inverse")
col4.metric("🗂️ จำนวนหุ้น",  f"{n_stocks} ตัว")

st.divider()

# ─ Layout: Chart | Watchlist ─
left, right = st.columns([2, 1], gap="large")

with left:
    st.markdown('<div class="section-header">📉 กราฟมูลค่าพอร์ต</div>', unsafe_allow_html=True)

    # ดึงจาก Snowflake ถ้ามี ไม่งั้น simulate จาก portfolio
    port_hist = load_portfolio_history(st.session_state.user_id, 90)
    if port_hist.empty and holdings:
        syms = [h["symbol"] for h in holdings]
        multi = get_multi_prices(syms, "3mo")
        if not multi.empty:
            # ✅ เพิ่มบรรทัดนี้ — แก้ timezone issue
            multi.index = pd.to_datetime(multi.index).tz_localize(None)
            
            weights  = {h["symbol"]: h.get("qty", 0) for h in holdings}
            port_val = pd.Series(0.0, index=multi.index)
            for s in syms:
                if s in multi.columns and weights.get(s, 0) > 0:
                    port_val = port_val + multi[s].fillna(0) * weights[s]
            port_val = port_val[port_val > 0]
            if not port_val.empty:
                port_hist = pd.DataFrame({
                    "SNAPSHOT_DATE": port_val.index,
                    "TOTAL_VALUE":   port_val.values
                })

    if not port_hist.empty:
        fig = go.Figure()
        x_col = "SNAPSHOT_DATE" if "SNAPSHOT_DATE" in port_hist.columns else port_hist.columns[0]
        y_col = "TOTAL_VALUE"    if "TOTAL_VALUE"    in port_hist.columns else port_hist.columns[1]

        fig.add_trace(go.Scatter(
            x=port_hist[x_col], y=port_hist[y_col],
            mode="lines",
            fill="tozeroy",
            line=dict(color="#00D4FF", width=2.5),
            fillcolor="rgba(0,212,255,0.08)",
            name="มูลค่าพอร์ต",
            hovertemplate="$%{y:,.2f}<extra></extra>",
        ))
        fig.update_layout(
            height=300, margin=dict(l=0,r=0,t=10,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color="#475569"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 ยังไม่มีข้อมูลพอร์ต — ไปที่หน้า **Portfolio** เพื่อเพิ่มหุ้น")

    # ─ Holdings Table ─
    st.markdown('<div class="section-header">🗂️ หุ้นในพอร์ต</div>', unsafe_allow_html=True)
    if holdings:
        rows = []
        for h in holdings:
            sym = h.get("symbol", "")
            info = get_current_price(sym)
            cur_price = info["price"]
            qty       = h.get("qty", 0)
            avg_cost  = h.get("avg_cost", 0)
            mkt_val   = cur_price * qty
            pnl       = mkt_val - avg_cost * qty
            pnl_pct   = (pnl / (avg_cost * qty) * 100) if avg_cost else 0
            rows.append({
                "หุ้น": sym,
                "จำนวน": qty,
                "ต้นทุน/หุ้น": f"${avg_cost:.2f}",
                "ราคาปัจจุบัน": f"${cur_price:.2f}",
                "มูลค่า": f"${mkt_val:,.2f}",
                "กำไร/ขาดทุน": f"${pnl:+,.2f}",
                "% กำไร": f"{pnl_pct:+.2f}%",
            })
        df_hold = pd.DataFrame(rows)
        st.dataframe(df_hold, use_container_width=True, hide_index=True)
    else:
        st.info("ยังไม่มีหุ้นในพอร์ต")


with right:
    st.markdown('<div class="section-header">👁️ Watchlist</div>', unsafe_allow_html=True)
    watchlist = st.session_state.watchlist or ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]

    for sym in watchlist[:8]:
        info = get_current_price(sym)
        price  = info["price"]
        chg    = info["change"]
        chg_p  = info["change_pct"]
        color  = "#34d399" if chg >= 0 else "#f87171"
        arrow  = "▲" if chg >= 0 else "▼"
        bg     = "#064e3b" if chg >= 0 else "#450a0a"

        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    background:#111827;border:1px solid rgba(255,255,255,0.06);
                    border-radius:10px;padding:10px 14px;margin-bottom:6px;">
          <div>
            <span style="font-weight:600;color:#e2e8f0;font-size:0.95rem;">{sym}</span>
            <span style="color:#475569;font-size:0.72rem;margin-left:6px;">{info['name'][:18]}</span>
          </div>
          <div style="text-align:right;">
            <div style="font-family:'Space Mono',monospace;color:#e2e8f0;font-size:0.9rem;">${price:,.2f}</div>
            <span style="background:{bg};color:{color};padding:2px 7px;border-radius:5px;font-size:0.72rem;">
              {arrow} {chg_p:+.2f}%
            </span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ─ Sector Donut ─
    if holdings:
        st.markdown('<div class="section-header">🍩 สัดส่วนพอร์ต</div>', unsafe_allow_html=True)
        labels  = [h["symbol"] for h in holdings]
        values  = [h.get("qty", 0) * get_current_price(h["symbol"])["price"] for h in holdings]
        colors  = ["#00D4FF","#7C3AED","#f59e0b","#10b981","#f43f5e","#3b82f6"]
        fig_pie = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.6,
            marker_colors=colors[:len(labels)],
            textinfo="percent",
            hovertemplate="%{label}: $%{value:,.2f}<extra></extra>",
        ))
        fig_pie.update_layout(
            height=220, margin=dict(l=0,r=0,t=0,b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=True,
            legend=dict(font=dict(color="#94a3b8", size=11), orientation="h", y=-0.15),
        )
        st.plotly_chart(fig_pie, use_container_width=True)


# ─ Market Overview ─
st.divider()
st.markdown('<div class="section-header">🌍 ภาพรวมตลาด</div>', unsafe_allow_html=True)
market_symbols = ["SPY", "QQQ", "DIA", "VIX"]
market_names   = {"SPY": "S&P 500 ETF", "QQQ": "Nasdaq 100 ETF", "DIA": "Dow Jones ETF", "VIX": "VIX Index"}
cols = st.columns(4)
for i, sym in enumerate(market_symbols):
    info = get_current_price(sym)
    chg_p = info["change_pct"]
    arrow = "▲" if chg_p >= 0 else "▼"
    color = "normal" if chg_p >= 0 else "inverse"
    cols[i].metric(
        f"{arrow} {market_names.get(sym, sym)}",
        f"${info['price']:,.2f}",
        f"{chg_p:+.2f}%",
        delta_color=color,
    )
