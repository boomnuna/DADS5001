"""
Home.py — SmartInvest
รวม Dashboard + Portfolio เป็น 2 tabs ในหน้าเดียว
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

from utils.data_fetcher import get_current_price, get_multi_prices
from utils.db_mongo import load_portfolio, load_watchlist, save_watchlist, save_portfolio, save_trade
from utils.db_snowflake import load_portfolio_history, setup_tables, save_portfolio_snapshot, save_trade_to_snowflake, load_trade_log

st.set_page_config(
    page_title="SmartInvest",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  [data-testid="metric-container"] {
    background: linear-gradient(135deg, #111827 0%, #1a2235 100%);
    border: 1px solid rgba(0, 212, 255, 0.15);
    border-radius: 12px;
    padding: 16px 20px;
  }
  [data-testid="metric-container"] label { color: #64748b !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
  [data-testid="stMetricValue"] { font-family: 'Space Mono', monospace !important; font-size: 1.5rem !important; color: #e2e8f0 !important; }
  [data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid rgba(0,212,255,0.1); }
  .section-header { font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;letter-spacing:0.12em;margin:20px 0 10px;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px; }
  .tradex-logo { font-family:'Space Mono',monospace;font-size:1.6rem;font-weight:700;background:linear-gradient(90deg,#00D4FF,#7C3AED);-webkit-background-clip:text;-webkit-text-fill-color:transparent; }
  .tradex-sub { font-size:0.72rem;color:#475569;letter-spacing:0.1em; }
</style>
""", unsafe_allow_html=True)

# ── Setup & Session ────────────────────────────────────────────────────────────
setup_tables()

if "user_id"   not in st.session_state: st.session_state.user_id = "default"
if "portfolio" not in st.session_state:
    loaded = load_portfolio()
    if not loaded:
        loaded = [
            {"symbol": "AAPL", "qty": 10, "avg_cost": 170.0},
            {"symbol": "TSLA", "qty": 5,  "avg_cost": 200.0},
            {"symbol": "NVDA", "qty": 8,  "avg_cost": 450.0},
            {"symbol": "MSFT", "qty": 6,  "avg_cost": 330.0},
            {"symbol": "AMZN", "qty": 4,  "avg_cost": 140.0},
        ]
    st.session_state.portfolio = loaded
if "watchlist" not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="tradex-logo">SmartInvest</div>', unsafe_allow_html=True)
    st.markdown('<div class="tradex-sub">AI INVESTMENT ADVISOR</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<div class="section-header">⚙️ Watchlist</div>', unsafe_allow_html=True)
    default_wl = st.session_state.watchlist or ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"]
    wl_input = st.text_area("หุ้นที่ติดตาม (คั่นด้วยจุลภาค)", value=", ".join(default_wl), height=80)
    if st.button("💾 บันทึก Watchlist", use_container_width=True):
        syms = [s.strip().upper() for s in wl_input.split(",") if s.strip()]
        st.session_state.watchlist = syms
        save_watchlist(st.session_state.user_id, syms)
        st.success("บันทึกแล้ว!")
        st.rerun()
    st.divider()
    st.markdown(f'<div style="color:#475569;font-size:0.72rem;">🕐 {datetime.now().strftime("%d %b %Y %H:%M")}</div>', unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_home, tab_port = st.tabs(["🏠 ภาพรวม", "💼 พอร์ตโฟลิโอ"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HOME DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_home:
    st.markdown("## 📊 ภาพรวมพอร์ตการลงทุน")

    holdings = st.session_state.portfolio
    total_value = sum(get_current_price(h["symbol"])["price"] * h.get("qty", 0) for h in holdings)
    total_cost  = sum(h.get("qty", 0) * h.get("avg_cost", 0) for h in holdings)
    total_pnl   = total_value - total_cost
    pnl_pct     = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 มูลค่ารวม",   f"${total_value:,.2f}", f"{pnl_pct:+.2f}%")
    c2.metric("💵 ต้นทุนรวม",   f"${total_cost:,.2f}")
    c3.metric("📈 กำไร/ขาดทุน", f"${total_pnl:+,.2f}", delta_color="normal" if total_pnl >= 0 else "inverse")
    c4.metric("🗂️ จำนวนหุ้น",  f"{len(holdings)} ตัว")

    st.divider()
    left, right = st.columns([2, 1], gap="large")

    with left:
        st.markdown('<div class="section-header">📉 กราฟมูลค่าพอร์ต</div>', unsafe_allow_html=True)
        port_hist = load_portfolio_history(st.session_state.user_id, 90)
        if port_hist.empty and holdings:
            syms  = [h["symbol"] for h in holdings]
            multi = get_multi_prices(syms, "3mo")
            if not multi.empty:
                if multi.index.tz is not None:
                    multi.index = multi.index.tz_convert(None)
                weights  = {h["symbol"]: h.get("qty", 0) for h in holdings}
                port_val = pd.Series(0.0, index=multi.index)
                for s in syms:
                    if s in multi.columns and weights.get(s, 0) > 0:
                        port_val += multi[s].fillna(0) * weights[s]
                port_val = port_val[port_val > 0]
                if not port_val.empty:
                    port_hist = pd.DataFrame({"SNAPSHOT_DATE": port_val.index, "TOTAL_VALUE": port_val.values})

        if not port_hist.empty:
            x_col = "SNAPSHOT_DATE" if "SNAPSHOT_DATE" in port_hist.columns else port_hist.columns[0]
            y_col = "TOTAL_VALUE"   if "TOTAL_VALUE"   in port_hist.columns else port_hist.columns[1]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=port_hist[x_col], y=port_hist[y_col], mode="lines",
                fill="tozeroy", line=dict(color="#00D4FF", width=2.5),
                fillcolor="rgba(0,212,255,0.08)",
                hovertemplate="$%{y:,.2f}<extra></extra>",
            ))
            fig.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False, color="#475569"),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
                showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📭 ยังไม่มีข้อมูลพอร์ต")

        # Holdings table
        st.markdown('<div class="section-header">🗂️ หุ้นในพอร์ต</div>', unsafe_allow_html=True)
        if holdings:
            rows = []
            for h in holdings:
                info     = get_current_price(h["symbol"])
                cur      = info["price"]
                qty      = h.get("qty", 0)
                avg_cost = h.get("avg_cost", 0)
                mkt      = cur * qty
                pnl      = mkt - avg_cost * qty
                pnl_p    = (pnl / (avg_cost * qty) * 100) if avg_cost else 0
                rows.append({"หุ้น": h["symbol"], "จำนวน": qty,
                    "ต้นทุน/หุ้น": f"${avg_cost:.2f}", "ราคาปัจจุบัน": f"${cur:.2f}",
                    "มูลค่า": f"${mkt:,.2f}", "กำไร/ขาดทุน": f"${pnl:+,.2f}", "% กำไร": f"{pnl_p:+.2f}%"})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with right:
        st.markdown('<div class="section-header">👁️ Watchlist</div>', unsafe_allow_html=True)
        for sym in (st.session_state.watchlist or ["AAPL","TSLA","NVDA","MSFT","AMZN"])[:8]:
            info  = get_current_price(sym)
            price = info["price"]; chg_p = info["change_pct"]
            color = "#34d399" if chg_p >= 0 else "#f87171"
            arrow = "▲" if chg_p >= 0 else "▼"
            bg    = "#064e3b" if chg_p >= 0 else "#450a0a"
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
                        background:#111827;border:1px solid rgba(255,255,255,0.06);
                        border-radius:10px;padding:10px 14px;margin-bottom:6px;">
              <div><span style="font-weight:600;color:#e2e8f0;">{sym}</span>
                   <span style="color:#475569;font-size:0.72rem;margin-left:6px;">{info['name'][:18]}</span></div>
              <div style="text-align:right;">
                <div style="font-family:'Space Mono',monospace;color:#e2e8f0;">${price:,.2f}</div>
                <span style="background:{bg};color:{color};padding:2px 7px;border-radius:5px;font-size:0.72rem;">{arrow} {chg_p:+.2f}%</span>
              </div>
            </div>""", unsafe_allow_html=True)

        if holdings:
            st.markdown('<div class="section-header">🍩 สัดส่วนพอร์ต</div>', unsafe_allow_html=True)
            labels = [h["symbol"] for h in holdings]
            values = [h.get("qty",0) * get_current_price(h["symbol"])["price"] for h in holdings]
            colors = ["#00D4FF","#7C3AED","#f59e0b","#10b981","#f43f5e","#3b82f6"]
            fig_pie = go.Figure(go.Pie(labels=labels, values=values, hole=0.6,
                marker_colors=colors[:len(labels)], textinfo="percent",
                hovertemplate="%{label}: $%{value:,.2f}<extra></extra>"))
            fig_pie.update_layout(height=220, margin=dict(l=0,r=0,t=0,b=0),
                paper_bgcolor="rgba(0,0,0,0)", showlegend=True,
                legend=dict(font=dict(color="#94a3b8", size=11), orientation="h", y=-0.15))
            st.plotly_chart(fig_pie, use_container_width=True)

    # Market Overview
    st.divider()
    st.markdown('<div class="section-header">🌍 ภาพรวมตลาด</div>', unsafe_allow_html=True)
    market_symbols = ["SPY", "QQQ", "DIA", "^VIX"]
    market_names   = {"SPY":"S&P 500 ETF","QQQ":"Nasdaq 100 ETF","DIA":"Dow Jones ETF","^VIX":"VIX Index"}
    cols = st.columns(4)
    for i, sym in enumerate(market_symbols):
        info  = get_current_price(sym)
        chg_p = info["change_pct"]
        cols[i].metric(
            f"{'▲' if chg_p>=0 else '▼'} {market_names[sym]}",
            f"${info['price']:,.2f}", f"{chg_p:+.2f}%",
            delta_color="normal" if chg_p >= 0 else "inverse")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab_port:
    st.markdown("## 💼 พอร์ตโฟลิโอ")
    st.caption("จัดการหุ้น, P&L, คำนวณภาษี WHT และประวัติการซื้อขาย")

    holdings = st.session_state.portfolio

    # Live prices
    live_data = {}
    for h in holdings:
        sym = h.get("symbol","")
        if sym:
            info = get_current_price(sym)
            live_data[sym]       = info
            h["current_price"]   = info["price"]
            h["market_value"]    = info["price"] * h.get("qty", 0)

    total_cost2 = sum(h.get("qty",0)*h.get("avg_cost",0) for h in holdings)
    total_val2  = sum(h.get("market_value",0) for h in holdings)
    total_pnl2  = total_val2 - total_cost2
    pnl_pct2    = (total_pnl2 / total_cost2 * 100) if total_cost2 else 0

    p1, p2, p3 = st.columns(3)
    p1.metric("💰 มูลค่ารวม",   f"${total_val2:,.2f}", f"{pnl_pct2:+.2f}%")
    p2.metric("💵 ต้นทุนรวม",   f"${total_cost2:,.2f}")
    p3.metric("📈 กำไร/ขาดทุน", f"${total_pnl2:+,.2f}", delta_color="normal" if total_pnl2 >= 0 else "inverse")

    st.divider()

    pt1, pt2, pt3, pt4 = st.tabs(["📊 พอร์ตปัจจุบัน", "➕ เพิ่ม/ลบหุ้น", "💰 คำนวณภาษี WHT", "📜 ประวัติ Trades"])

    # ── พอร์ตปัจจุบัน ─────────────────────────────────────────────────────────
    with pt1:
        if not holdings:
            st.info("ยังไม่มีหุ้นในพอร์ต")
        else:
            rows = []
            for h in holdings:
                sym = h.get("symbol",""); qty = h.get("qty",0); avg_cost = h.get("avg_cost",0)
                cur = h.get("current_price",0); mkt = h.get("market_value",0)
                pnl = mkt - avg_cost*qty; pnl_p = (pnl/(avg_cost*qty)*100) if avg_cost else 0
                rows.append({"หุ้น":sym,"ชื่อบริษัท":live_data.get(sym,{}).get("name","")[:25],
                    "จำนวน":qty,"ต้นทุน/หุ้น":avg_cost,"ราคาปัจจุบัน":cur,
                    "มูลค่าตลาด":mkt,"กำไร/ขาดทุน":pnl,"% กำไร":pnl_p,"สัดส่วน%":(mkt/total_val2*100) if total_val2 else 0})

            df_hold = pd.DataFrame(rows)
            fmt = df_hold.copy()
            fmt["ต้นทุน/หุ้น"]  = fmt["ต้นทุน/หุ้น"].map(lambda x: f"${x:,.2f}")
            fmt["ราคาปัจจุบัน"] = fmt["ราคาปัจจุบัน"].map(lambda x: f"${x:,.2f}")
            fmt["มูลค่าตลาด"]   = fmt["มูลค่าตลาด"].map(lambda x: f"${x:,.2f}")
            fmt["กำไร/ขาดทุน"]  = fmt["กำไร/ขาดทุน"].map(lambda x: f"${x:+,.2f}")
            fmt["% กำไร"]       = fmt["% กำไร"].map(lambda x: f"{x:+.2f}%")
            fmt["สัดส่วน%"]     = fmt["สัดส่วน%"].map(lambda x: f"{x:.1f}%")
            st.dataframe(fmt, use_container_width=True, hide_index=True)

            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown('<div class="section-header">🍩 สัดส่วนพอร์ต</div>', unsafe_allow_html=True)
                colors = ["#00D4FF","#7C3AED","#f59e0b","#10b981","#f43f5e","#3b82f6","#ec4899"]
                fig = go.Figure(go.Pie(labels=df_hold["หุ้น"], values=df_hold["มูลค่าตลาด"],
                    hole=0.6, marker_colors=colors[:len(df_hold)], textinfo="percent+label",
                    hovertemplate="%{label}: $%{value:,.2f}<extra></extra>"))
                fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0),
                    paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            with col_r:
                st.markdown('<div class="section-header">📊 กำไร/ขาดทุนแต่ละหุ้น</div>', unsafe_allow_html=True)
                bar_colors = ["#34d399" if p >= 0 else "#f87171" for p in df_hold["กำไร/ขาดทุน"]]
                fig2 = go.Figure(go.Bar(x=df_hold["หุ้น"], y=df_hold["กำไร/ขาดทุน"],
                    marker_color=bar_colors,
                    text=df_hold["% กำไร"].map(lambda x: f"{x:+.2f}%"), textposition="outside"))
                fig2.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
                    xaxis=dict(color="#475569"), showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)

            if st.button("☁️ บันทึก Snapshot วันนี้ → Snowflake"):
                df_snap = pd.DataFrame([{
                    "symbol": h["symbol"], "qty": h.get("qty",0), "avg_cost": h.get("avg_cost",0),
                    "current_price": h.get("current_price",0), "market_value": h.get("market_value",0),
                    "pnl": h.get("market_value",0)-h.get("avg_cost",0)*h.get("qty",0),
                    "pnl_pct": ((h.get("market_value",0)-h.get("avg_cost",0)*h.get("qty",0))/(h.get("avg_cost",0)*h.get("qty",0))*100) if h.get("avg_cost") else 0,
                } for h in holdings])
                ok = save_portfolio_snapshot(st.session_state.user_id, df_snap)
                st.success("✅ บันทึกเรียบร้อย") if ok else st.warning("ตรวจสอบ Snowflake credentials")

    # ── เพิ่ม/ลบหุ้น ──────────────────────────────────────────────────────────
    with pt2:
        left2, right2 = st.columns(2, gap="large")
        with left2:
            st.markdown('<div class="section-header">➕ เพิ่มหุ้น / บันทึก Trade</div>', unsafe_allow_html=True)
            trade_type = st.radio("ประเภท", ["ซื้อ 🟢","ขาย 🔴"], horizontal=True)
            t_sym   = st.text_input("Ticker", placeholder="เช่น AAPL").upper().strip()
            t_qty   = st.number_input("จำนวนหุ้น", min_value=0.01, value=10.0, step=1.0)
            t_price = st.number_input("ราคาต่อหุ้น ($)", min_value=0.01, value=100.0, step=0.01)
            t_date  = st.date_input("วันที่", value=date.today())
            st.metric("มูลค่ารวม", f"${t_qty*t_price:,.2f}")
            if st.button("✅ ยืนยัน", use_container_width=True, type="primary"):
                if not t_sym:
                    st.error("กรุณาใส่ Ticker")
                else:
                    action = "buy" if "ซื้อ" in trade_type else "sell"
                    trade_doc = {"user_id":st.session_state.user_id,"symbol":t_sym,"trade_type":action,
                        "qty":t_qty,"price":t_price,"total_value":t_qty*t_price,"trade_date":str(t_date)}
                    current = st.session_state.portfolio
                    idx = next((i for i,h in enumerate(current) if h["symbol"]==t_sym), None)
                    if action == "buy":
                        if idx is not None:
                            old = current[idx]; new_qty = old["qty"]+t_qty
                            current[idx].update({"qty":new_qty,"avg_cost":round((old["qty"]*old["avg_cost"]+t_qty*t_price)/new_qty,4)})
                        else:
                            current.append({"symbol":t_sym,"qty":t_qty,"avg_cost":t_price,"market_value":t_qty*t_price})
                    else:
                        if idx is not None:
                            current[idx]["qty"] -= t_qty
                            if current[idx]["qty"] <= 0: current.pop(idx)
                        else:
                            st.error(f"ไม่มีหุ้น {t_sym} ในพอร์ต")
                    st.session_state.portfolio = current
                    save_portfolio(st.session_state.user_id, current)
                    save_trade(trade_doc)
                    save_trade_to_snowflake(st.session_state.user_id, trade_doc)
                    st.success(f"{'ซื้อ' if action=='buy' else 'ขาย'} {t_qty} {t_sym} @ ${t_price:.2f} ✅")
                    st.rerun()

        with right2:
            st.markdown('<div class="section-header">🗑️ ลบหุ้นออกจากพอร์ต</div>', unsafe_allow_html=True)
            if holdings:
                del_sym = st.selectbox("เลือกหุ้นที่ต้องการลบ", [h["symbol"] for h in holdings])
                if st.button("🗑️ ลบออก", use_container_width=True):
                    st.session_state.portfolio = [h for h in holdings if h["symbol"] != del_sym]
                    save_portfolio(st.session_state.user_id, st.session_state.portfolio)
                    st.success(f"ลบ {del_sym} แล้ว"); st.rerun()
            else:
                st.info("พอร์ตว่าง")

    # ── ภาษี WHT ──────────────────────────────────────────────────────────────
    with pt3:
        st.markdown('<div class="section-header">💰 คำนวณภาษี WHT ปี 2026</div>', unsafe_allow_html=True)
        st.info("**WHT 15%** หักจากกำไรจากการขายหุ้น (Capital Gain)")
        wht_rate = st.slider("อัตราภาษี WHT (%)", 0, 30, 15) / 100
        if holdings:
            tax_rows = []
            for h in holdings:
                gain = (h.get("current_price",0) - h.get("avg_cost",0)) * h.get("qty",0)
                tax  = max(gain * wht_rate, 0)
                tax_rows.append({"หุ้น":h["symbol"],"จำนวน":h.get("qty",0),
                    "ต้นทุน/หุ้น":h.get("avg_cost",0),"ราคาปัจจุบัน":h.get("current_price",0),
                    "กำไร (Unrealized)":round(gain,2),
                    f"ภาษี WHT ({wht_rate*100:.0f}%)":round(tax,2),
                    "กำไรสุทธิ":round(gain-tax,2)})
            df_tax = pd.DataFrame(tax_rows)
            st.dataframe(df_tax, use_container_width=True, hide_index=True)
            t1,t2,t3 = st.columns(3)
            t1.metric("กำไรรวม", f"${df_tax['กำไร (Unrealized)'].sum():+,.2f}")
            t2.metric(f"ภาษี WHT ({wht_rate*100:.0f}%)", f"${df_tax[f'ภาษี WHT ({wht_rate*100:.0f}%)'].sum():,.2f}", delta_color="inverse")
            t3.metric("กำไรสุทธิ", f"${df_tax['กำไรสุทธิ'].sum():+,.2f}")

    # ── ประวัติ Trades ─────────────────────────────────────────────────────────
    with pt4:
        st.markdown('<div class="section-header">📜 ประวัติจาก Snowflake</div>', unsafe_allow_html=True)
        df_trades = load_trade_log(st.session_state.user_id, 50)
        if df_trades.empty:
            st.info("ยังไม่มีประวัติการซื้อขาย")
        else:
            st.dataframe(df_trades, use_container_width=True, hide_index=True)
