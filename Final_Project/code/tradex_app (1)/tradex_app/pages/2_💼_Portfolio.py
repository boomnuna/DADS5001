"""
pages/2_💼_Portfolio.py
พอร์ตโฟลิโอ — จัดการหุ้น, P&L, Tax Calculator (WHT 15%)
เก็บข้อมูลใน MongoDB + Snowflake
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime

from utils.data_fetcher import get_current_price
from utils.db_mongo import load_portfolio, save_portfolio, save_trade
from utils.db_snowflake import save_portfolio_snapshot, save_trade_to_snowflake, load_trade_log

st.set_page_config(page_title="Portfolio — TradeX", layout="wide", page_icon="💼")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .section-header { font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;
    letter-spacing:0.12em;margin:20px 0 10px;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px; }
  .pnl-pos { color:#34d399;font-family:'Space Mono',monospace; }
  .pnl-neg { color:#f87171;font-family:'Space Mono',monospace; }
</style>
""", unsafe_allow_html=True)

# ── Session / Load ─────────────────────────────────────────────────────────────
if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_portfolio()
if "user_id" not in st.session_state:
    st.session_state.user_id = "default"

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 💼 พอร์ตโฟลิโอ")
st.caption("ภาพรวมและรายละเอียดหุ้นทั้งหมด — ข้อมูลราคาแบบ real-time จาก Yahoo Finance")

holdings = st.session_state.portfolio

# ── Update live prices ─────────────────────────────────────────────────────────
live_data = {}
for h in holdings:
    sym = h.get("symbol", "")
    if sym:
        info = get_current_price(sym)
        live_data[sym] = info
        h["current_price"] = info["price"]
        h["market_value"]  = info["price"] * h.get("qty", 0)

# ── Summary Metrics ───────────────────────────────────────────────────────────
total_cost  = sum(h.get("qty",0) * h.get("avg_cost",0) for h in holdings)
total_val   = sum(h.get("market_value",0) for h in holdings)
total_pnl   = total_val - total_cost
pnl_pct     = (total_pnl / total_cost * 100) if total_cost else 0

c1,c2,c3 = st.columns(3)
c1.metric("💰 มูลค่ารวม",   f"${total_val:,.2f}", f"{pnl_pct:+.2f}%")
c2.metric("💵 ต้นทุนรวม",   f"${total_cost:,.2f}")
c3.metric("📈 กำไร/ขาดทุน", f"${total_pnl:+,.2f}",
          delta_color="normal" if total_pnl >= 0 else "inverse")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📊 พอร์ตปัจจุบัน", "➕ เพิ่ม/ลบหุ้น", "💰 คำนวณภาษี WHT", "📜 ประวัติ Trades"])

# ─ Tab 1: Holdings ────────────────────────────────────────────────────────────
with tab1:
    if not holdings:
        st.info("ยังไม่มีหุ้นในพอร์ต — ไปที่แท็บ 'เพิ่ม/ลบหุ้น'")
    else:
        # Table
        rows = []
        for h in holdings:
            sym      = h.get("symbol","")
            qty      = h.get("qty",0)
            avg_cost = h.get("avg_cost",0)
            cur      = h.get("current_price",0)
            mkt      = h.get("market_value",0)
            pnl      = mkt - avg_cost * qty
            pnl_p    = (pnl / (avg_cost*qty) * 100) if avg_cost else 0
            rows.append({
                "หุ้น":         sym,
                "ชื่อบริษัท":   live_data.get(sym,{}).get("name","")[:25],
                "จำนวนหุ้น":    qty,
                "ต้นทุน/หุ้น":  avg_cost,
                "ราคาปัจจุบัน": cur,
                "มูลค่าตลาด":   mkt,
                "กำไร/ขาดทุน":  pnl,
                "% กำไร":       pnl_p,
                "สัดส่วน%":     (mkt/total_val*100) if total_val else 0,
            })

        df_hold = pd.DataFrame(rows)

        # Format
        fmt_df = df_hold.copy()
        fmt_df["ต้นทุน/หุ้น"]  = fmt_df["ต้นทุน/หุ้น"].map(lambda x: f"${x:,.2f}")
        fmt_df["ราคาปัจจุบัน"] = fmt_df["ราคาปัจจุบัน"].map(lambda x: f"${x:,.2f}")
        fmt_df["มูลค่าตลาด"]   = fmt_df["มูลค่าตลาด"].map(lambda x: f"${x:,.2f}")
        fmt_df["กำไร/ขาดทุน"]  = fmt_df["กำไร/ขาดทุน"].map(lambda x: f"${x:+,.2f}")
        fmt_df["% กำไร"]       = fmt_df["% กำไร"].map(lambda x: f"{x:+.2f}%")
        fmt_df["สัดส่วน%"]     = fmt_df["สัดส่วน%"].map(lambda x: f"{x:.1f}%")
        st.dataframe(fmt_df, use_container_width=True, hide_index=True)

        # Charts
        left, right = st.columns(2)
        with left:
            st.markdown('<div class="section-header">🍩 สัดส่วนพอร์ต</div>', unsafe_allow_html=True)
            colors = ["#00D4FF","#7C3AED","#f59e0b","#10b981","#f43f5e","#3b82f6","#ec4899"]
            fig = go.Figure(go.Pie(
                labels=df_hold["หุ้น"], values=df_hold["มูลค่าตลาด"],
                hole=0.6, marker_colors=colors[:len(df_hold)],
                textinfo="percent+label",
                hovertemplate="%{label}: $%{value:,.2f}<extra></extra>",
            ))
            fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0),
                paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.markdown('<div class="section-header">📊 กำไร/ขาดทุนแต่ละหุ้น</div>', unsafe_allow_html=True)
            bar_colors = ["#34d399" if p >= 0 else "#f87171" for p in df_hold["กำไร/ขาดทุน"].str.replace("$","").str.replace(",","").astype(float)]
            fig2 = go.Figure(go.Bar(
                x=df_hold["หุ้น"],
                y=df_hold["กำไร/ขาดทุน"].str.replace("$","").str.replace(",","").astype(float),
                marker_color=bar_colors,
                text=df_hold["% กำไร"], textposition="outside",
                hovertemplate="%{x}: $%{y:,.2f}<extra></extra>",
            ))
            fig2.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
                xaxis=dict(color="#475569"), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        # Save snapshot to Snowflake
        if st.button("☁️ บันทึก Snapshot วันนี้ → Snowflake"):
            df_snap = pd.DataFrame([{
                "symbol":        h["symbol"],
                "qty":           h.get("qty",0),
                "avg_cost":      h.get("avg_cost",0),
                "current_price": h.get("current_price",0),
                "market_value":  h.get("market_value",0),
                "pnl":           h.get("market_value",0) - h.get("avg_cost",0)*h.get("qty",0),
                "pnl_pct":       ((h.get("market_value",0) - h.get("avg_cost",0)*h.get("qty",0)) /
                                  (h.get("avg_cost",0)*h.get("qty",0)) * 100) if h.get("avg_cost") else 0,
            } for h in holdings])
            ok = save_portfolio_snapshot(st.session_state.user_id, df_snap)
            if ok:
                st.success("✅ บันทึกเรียบร้อย")
            else:
                st.warning("ตรวจสอบ Snowflake credentials")


# ─ Tab 2: Add / Remove ────────────────────────────────────────────────────────
with tab2:
    left2, right2 = st.columns([1, 1], gap="large")

    with left2:
        st.markdown('<div class="section-header">➕ เพิ่มหุ้น / บันทึก Trade</div>', unsafe_allow_html=True)
        trade_type = st.radio("ประเภท", ["ซื้อ 🟢", "ขาย 🔴"], horizontal=True)
        t_sym   = st.text_input("Ticker", placeholder="เช่น AAPL").upper().strip()
        t_qty   = st.number_input("จำนวนหุ้น", min_value=0.01, value=10.0, step=1.0)
        t_price = st.number_input("ราคาต่อหุ้น ($)", min_value=0.01, value=100.0, step=0.01)
        t_date  = st.date_input("วันที่ซื้อขาย", value=date.today())
        t_total = t_qty * t_price
        st.metric("มูลค่ารวม", f"${t_total:,.2f}")

        if st.button("✅ ยืนยัน", use_container_width=True, type="primary"):
            if not t_sym:
                st.error("กรุณาใส่ Ticker")
            else:
                action = "buy" if "ซื้อ" in trade_type else "sell"
                trade_doc = {
                    "user_id": st.session_state.user_id,
                    "symbol": t_sym, "trade_type": action,
                    "qty": t_qty, "price": t_price,
                    "total_value": t_total, "trade_date": str(t_date),
                }
                # อัปเดต Session
                current = st.session_state.portfolio
                idx = next((i for i,h in enumerate(current) if h["symbol"] == t_sym), None)

                if action == "buy":
                    if idx is not None:
                        old = current[idx]
                        new_qty  = old["qty"] + t_qty
                        new_cost = (old["qty"]*old["avg_cost"] + t_qty*t_price) / new_qty
                        current[idx].update({"qty": new_qty, "avg_cost": round(new_cost,4)})
                    else:
                        current.append({"symbol":t_sym,"qty":t_qty,"avg_cost":t_price,"market_value":t_total})
                else:
                    if idx is not None:
                        current[idx]["qty"] -= t_qty
                        if current[idx]["qty"] <= 0:
                            current.pop(idx)
                    else:
                        st.error(f"ไม่มีหุ้น {t_sym} ในพอร์ต")

                st.session_state.portfolio = current
                save_portfolio(st.session_state.user_id, current)   # → MongoDB
                save_trade(trade_doc)                                 # → MongoDB
                save_trade_to_snowflake(st.session_state.user_id, trade_doc)  # → Snowflake
                st.success(f"{'ซื้อ' if action=='buy' else 'ขาย'} {t_qty} {t_sym} @ ${t_price:.2f} ✅")
                st.rerun()

    with right2:
        st.markdown('<div class="section-header">🗑️ ลบหุ้นออกจากพอร์ต</div>', unsafe_allow_html=True)
        if holdings:
            syms = [h["symbol"] for h in holdings]
            del_sym = st.selectbox("เลือกหุ้นที่ต้องการลบ", syms)
            if st.button("🗑️ ลบออก", use_container_width=True):
                st.session_state.portfolio = [h for h in holdings if h["symbol"] != del_sym]
                save_portfolio(st.session_state.user_id, st.session_state.portfolio)
                st.success(f"ลบ {del_sym} แล้ว")
                st.rerun()
        else:
            st.info("พอร์ตว่าง")


# ─ Tab 3: Tax WHT ─────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">💰 คำนวณภาษีหัก ณ ที่จ่าย (WHT) ปี 2026</div>', unsafe_allow_html=True)
    st.info("**WHT 15%** หักจากกำไรจากการขายหุ้น (Capital Gain) สำหรับนักลงทุนต่างชาติ")

    wht_rate = st.slider("อัตราภาษี WHT (%)", 0, 30, 15) / 100

    if holdings:
        tax_rows = []
        for h in holdings:
            sym      = h["symbol"]
            qty      = h.get("qty",0)
            avg_cost = h.get("avg_cost",0)
            cur      = h.get("current_price",0)
            gain     = (cur - avg_cost) * qty
            tax      = max(gain * wht_rate, 0)
            tax_rows.append({
                "หุ้น": sym, "จำนวน": qty,
                "ต้นทุน/หุ้น": avg_cost, "ราคาปัจจุบัน": cur,
                "กำไร (Unrealized)": round(gain,2),
                f"ภาษี WHT ({wht_rate*100:.0f}%)": round(tax,2),
                "กำไรสุทธิ": round(gain - tax, 2),
            })
        df_tax = pd.DataFrame(tax_rows)
        total_gain    = df_tax["กำไร (Unrealized)"].sum()
        total_tax     = df_tax[f"ภาษี WHT ({wht_rate*100:.0f}%)"].sum()
        total_net     = df_tax["กำไรสุทธิ"].sum()

        st.dataframe(df_tax, use_container_width=True, hide_index=True)
        c1,c2,c3 = st.columns(3)
        c1.metric("กำไรรวม", f"${total_gain:+,.2f}")
        c2.metric(f"ภาษี WHT รวม ({wht_rate*100:.0f}%)", f"${total_tax:,.2f}", delta_color="inverse")
        c3.metric("กำไรสุทธิหลังหักภาษี", f"${total_net:+,.2f}")
    else:
        st.info("ไม่มีหุ้นในพอร์ต")


# ─ Tab 4: Trade History ────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">📜 ประวัติการซื้อขายจาก Snowflake</div>', unsafe_allow_html=True)
    df_trades = load_trade_log(st.session_state.user_id, 50)
    if df_trades.empty:
        st.info("ยังไม่มีประวัติการซื้อขาย หรือตรวจสอบ Snowflake connection")
    else:
        st.dataframe(df_trades, use_container_width=True, hide_index=True)
