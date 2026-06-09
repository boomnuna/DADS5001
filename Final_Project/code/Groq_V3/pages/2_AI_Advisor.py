"""
pages/2_🤖_AI_Advisor.py
AI Advisor — Non-AI vs AI + AI สรุปสถานะพอร์ต (วันนี้ + เมื่อวาน + เลือกวัน)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

from utils.data_fetcher import get_current_price, get_price_history, compute_technicals, get_news
from utils.ai_advisor import analyze_stock_ai, summarize_news_ai, predict_price_ai, _call_ai
from utils.db_mongo import load_portfolio
from utils.db_snowflake import load_portfolio_history

st.set_page_config(page_title="AI Advisor — SmartInvest", layout="wide", page_icon="🤖")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .section-header { font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;
    letter-spacing:0.12em;margin:20px 0 10px;border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px; }
  .ai-badge { background:linear-gradient(90deg,#7C3AED22,#00D4FF22);border:1px solid #7C3AED66;
    color:#a78bfa;padding:4px 14px;border-radius:20px;font-size:0.8rem;font-weight:600; }
  .nonai-badge { background:#111827;border:1px solid #374151;
    color:#94a3b8;padding:4px 14px;border-radius:20px;font-size:0.8rem;font-weight:600; }
  .ai-result { background:linear-gradient(135deg,#0f0f1a,#111827);
    border:1px solid rgba(124,58,237,0.3);border-radius:12px;padding:20px;
    border-left:3px solid #7C3AED;white-space:pre-wrap; }
</style>
""", unsafe_allow_html=True)

# ── Session ────────────────────────────────────────────────────────────────────
if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_portfolio()
if "user_id" not in st.session_state:
    st.session_state.user_id = "default"

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_advisor, tab_portfolio_ai = st.tabs(["🤖 AI Advisor", "📋 AI สรุปพอร์ต"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — AI ADVISOR (เดิม)
# ══════════════════════════════════════════════════════════════════════════════
with tab_advisor:
    st.markdown("## 🤖 AI Advisor")
    st.caption("วิเคราะห์หุ้นด้วย Technical Analysis และ AI")

    col_mode, col_sym, col_btn = st.columns([1.5, 2, 1])
    with col_mode:
        mode = st.radio("เลือก Mode", ["📊 Non-AI", "🤖 AI"], horizontal=True, key="adv_mode")
    with col_sym:
        symbol = st.text_input("หุ้นที่ต้องการวิเคราะห์", placeholder="เช่น AAPL, TSLA...",
                               value="AAPL", key="adv_sym").upper().strip()
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("✨ วิเคราะห์", use_container_width=True, type="primary", key="adv_run")

    is_ai = "AI" in mode
    if is_ai:
        st.markdown('<span class="ai-badge">🤖 AI Mode — Powered by Groq (Llama 3.3)</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="nonai-badge">📊 Non-AI Mode — Rule-based Technical Analysis</span>', unsafe_allow_html=True)

    st.divider()

    if analyze_btn or symbol:
        with st.spinner(f"กำลังโหลดข้อมูล {symbol}..."):
            info   = get_current_price(symbol)
            df_raw = get_price_history(symbol, "6mo")

        if df_raw.empty:
            st.error(f"❌ ไม่พบข้อมูล {symbol}")
            st.stop()

        df   = compute_technicals(df_raw)
        last = df.iloc[-1]
        news = get_news(symbol)

        rsi      = last["RSI"]; macd = last["MACD"]; macd_sig = last["MACD_Signal"]
        price    = info["price"]; ma50 = last["MA50"]; ma200 = last["MA200"]
        bb_upper = last["BB_Upper"]; bb_lower = last["BB_Lower"]
        bb_pos   = "Upper Band" if price > bb_upper else ("Lower Band" if price < bb_lower else "Middle")

        technicals = {
            "rsi": round(rsi,2) if not pd.isna(rsi) else "N/A",
            "macd": round(macd,4) if not pd.isna(macd) else "N/A",
            "macd_signal": "Bullish" if macd > macd_sig else "Bearish",
            "macd_signal_val": round(macd_sig,4) if not pd.isna(macd_sig) else "N/A",
            "vs_ma50":  f"{'เหนือ' if price>ma50 else 'ใต้'} MA50 ({(price/ma50-1)*100:+.1f}%)" if not pd.isna(ma50) else "N/A",
            "vs_ma200": f"{'เหนือ' if price>ma200 else 'ใต้'} MA200 ({(price/ma200-1)*100:+.1f}%)" if not pd.isna(ma200) else "N/A",
            "above_ma50": price > ma50, "above_ma200": price > ma200, "bb_position": bb_pos,
        }

        left, right = st.columns([1.2, 1], gap="large")

        with left:
            st.markdown('<div class="section-header">📊 Technical Scorecard</div>', unsafe_allow_html=True)
            score = 0; signals = []
            if not pd.isna(rsi):
                if rsi < 30:   score += 2; signals.append(("🟢","RSI Oversold — โอกาสฟื้นตัว"))
                elif rsi > 70: score -= 2; signals.append(("🔴","RSI Overbought — ระวังการปรับฐาน"))
                else:          signals.append(("🟡",f"RSI Neutral ({rsi:.1f})"))
            if not pd.isna(macd) and not pd.isna(macd_sig):
                if macd > macd_sig: score += 1; signals.append(("🟢","MACD Bullish Crossover"))
                else:               score -= 1; signals.append(("🔴","MACD Bearish"))
            if not pd.isna(ma50):
                if price > ma50:  score += 1; signals.append(("🟢","ราคาเหนือ MA50"))
                else:             score -= 1; signals.append(("🔴","ราคาต่ำกว่า MA50"))
            if not pd.isna(ma200):
                if price > ma200: score += 1; signals.append(("🟢","อยู่ใน Long-term Uptrend"))
                else:             score -= 1; signals.append(("🔴","อยู่ใน Long-term Downtrend"))

            score_label = "Strong Buy 🚀" if score>=3 else "Buy 📈" if score>=1 else "Hold ⚖️" if score==0 else "Sell 📉" if score>=-2 else "Strong Sell 🚨"
            score_color = "#34d399" if score>=2 else "#10b981" if score>=1 else "#f59e0b" if score==0 else "#f87171"
            st.markdown(f"""
            <div style="background:#111827;border:1px solid {score_color}44;border-radius:12px;padding:20px;text-align:center;margin-bottom:16px;">
              <div style="color:#94a3b8;font-size:0.75rem;text-transform:uppercase;">Technical Score</div>
              <div style="font-family:'Space Mono',monospace;font-size:2.5rem;color:{score_color};font-weight:700;">{score:+d}</div>
              <div style="color:{score_color};font-size:1rem;font-weight:600;">{score_label}</div>
            </div>""", unsafe_allow_html=True)
            for icon, msg in signals:
                st.markdown(f'<div style="padding:6px 0;font-size:0.85rem;">{icon} {msg}</div>', unsafe_allow_html=True)

            resistance = float(last["BB_Upper"]) if not pd.isna(last["BB_Upper"]) else price*1.05
            support    = float(last["BB_Lower"]) if not pd.isna(last["BB_Lower"]) else price*0.95
            st.markdown('<div class="section-header">🎯 เป้าหมายราคา</div>', unsafe_allow_html=True)
            ct1,ct2,ct3 = st.columns(3)
            ct1.metric("🛡️ Support",    f"${support:,.2f}")
            ct2.metric("💲 ปัจจุบัน",   f"${price:,.2f}")
            ct3.metric("⬆️ Resistance", f"${resistance:,.2f}")

        with right:
            st.markdown('<div class="section-header">📈 ราคา 6 เดือน</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines",
                line=dict(color="#00D4FF",width=2), fill="tozeroy", fillcolor="rgba(0,212,255,0.06)"))
            fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], mode="lines",
                line=dict(color="#f59e0b",width=1.2,dash="dash"), name="MA50"))
            fig.update_layout(height=280, margin=dict(l=0,r=0,t=0,b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False,color="#475569"),
                yaxis=dict(showgrid=True,gridcolor="rgba(255,255,255,0.04)",color="#475569"),
                showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown('<div class="section-header">📰 ข่าวล่าสุด</div>', unsafe_allow_html=True)
            for item in news[:3]:
                content = item.get("content",item)
                title   = content.get("title",item.get("title",""))
                url     = content.get("canonicalUrl",{}).get("url",item.get("link","#"))
                st.markdown(f'<div style="padding:5px 0;"><a href="{url}" target="_blank" style="color:#94a3b8;font-size:0.8rem;text-decoration:none;">📰 {title[:75]}...</a></div>', unsafe_allow_html=True)

        st.divider()

        if is_ai:
            st.markdown("### 🤖 การวิเคราะห์เชิงลึกด้วย AI")
            ai_t1, ai_t2, ai_t3 = st.tabs(["🔍 วิเคราะห์หุ้น","📰 Sentiment ข่าว","🔮 พยากรณ์ราคา"])
            with ai_t1:
                if st.button("🚀 วิเคราะห์ด้วย AI", type="primary", use_container_width=True, key="ai_analyze"):
                    with st.spinner("AI กำลังวิเคราะห์..."):
                        result = analyze_stock_ai(symbol, info, news, technicals)
                    st.markdown(f'<div class="ai-result">{result}</div>', unsafe_allow_html=True)
                else:
                    st.info("กด 'วิเคราะห์ด้วย AI' เพื่อรับการวิเคราะห์เชิงลึก (cache 6 ชม.)")
            with ai_t2:
                if st.button("📰 วิเคราะห์ Sentiment", type="primary", use_container_width=True, key="ai_sentiment"):
                    with st.spinner("AI กำลังสรุปข่าว..."):
                        sentiment = summarize_news_ai(symbol, news)
                    st.markdown(f'<div class="ai-result">{sentiment}</div>', unsafe_allow_html=True)
            with ai_t3:
                if st.button("🔮 พยากรณ์ราคา", type="primary", use_container_width=True, key="ai_predict"):
                    with st.spinner("AI กำลังประเมิน..."):
                        prediction = predict_price_ai(symbol, price, technicals)
                    st.markdown(f'<div class="ai-result">{prediction}</div>', unsafe_allow_html=True)
        else:
            st.markdown("### 📊 สรุป Technical Indicators")
            summary_data = {
                "Indicator": ["RSI (14)","MACD vs Signal","Price vs MA20","Price vs MA50","Price vs MA200","Bollinger Band"],
                "ค่า": [
                    f"{rsi:.1f}" if not pd.isna(rsi) else "N/A",
                    f"{macd:.4f} / {macd_sig:.4f}" if not pd.isna(macd) else "N/A",
                    f"${float(last['MA20']):.2f} ({'เหนือ' if price>float(last['MA20']) else 'ใต้'})" if not pd.isna(last['MA20']) else "N/A",
                    f"${float(last['MA50']):.2f} ({'เหนือ' if price>float(last['MA50']) else 'ใต้'})" if not pd.isna(last['MA50']) else "N/A",
                    f"${float(last['MA200']):.2f} ({'เหนือ' if price>float(last['MA200']) else 'ใต้'})" if not pd.isna(last['MA200']) else "N/A",
                    bb_pos,
                ],
                "สัญญาณ": [
                    "🟢 Oversold" if not pd.isna(rsi) and rsi<30 else "🔴 Overbought" if not pd.isna(rsi) and rsi>70 else "🟡 Neutral",
                    "🟢 Bullish" if not pd.isna(macd) and macd>macd_sig else "🔴 Bearish",
                    "🟢" if not pd.isna(last['MA20']) and price>float(last['MA20']) else "🔴",
                    "🟢" if not pd.isna(last['MA50']) and price>float(last['MA50']) else "🔴",
                    "🟢" if not pd.isna(last['MA200']) and price>float(last['MA200']) else "🔴",
                    "🔴" if bb_pos=="Upper Band" else "🟢" if bb_pos=="Lower Band" else "🟡",
                ]
            }
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — AI สรุปพอร์ต
# ══════════════════════════════════════════════════════════════════════════════
with tab_portfolio_ai:
    st.markdown("## 📋 AI สรุปสถานะพอร์ต")
    st.caption("กด 1 ปุ่ม AI สรุปให้เลยว่าวันนี้พอร์ตของคุณเป็นยังไง")

    holdings = st.session_state.portfolio
    if not holdings:
        st.warning("ยังไม่มีหุ้นในพอร์ต — ไปที่หน้า Home เพื่อเพิ่มหุ้นก่อนครับ")
        st.stop()

    # ── เลือก mode ─────────────────────────────────────────────────────────────
    sum_mode = st.radio("ต้องการสรุป", ["📊 วันนี้","📅 เปรียบเทียบวันนี้ vs เมื่อวาน","🗓️ เลือกวันที่"],
                        horizontal=True, key="sum_mode")

    # ── ดึงราคาปัจจุบัน ────────────────────────────────────────────────────────
    today_data = []
    for h in holdings:
        sym  = h["symbol"]
        info = get_current_price(sym)
        qty  = h.get("qty", 0)
        cost = h.get("avg_cost", 0)
        cur  = info["price"]
        mkt  = cur * qty
        pnl  = mkt - cost * qty
        pnl_p= (pnl/(cost*qty)*100) if cost else 0
        today_data.append({
            "symbol": sym, "qty": qty, "avg_cost": cost,
            "current_price": cur, "market_value": mkt,
            "pnl": pnl, "pnl_pct": pnl_p,
            "change_pct": info["change_pct"],
        })

    total_val  = sum(d["market_value"] for d in today_data)
    total_cost = sum(d["qty"]*d["avg_cost"] for d in today_data)
    total_pnl  = total_val - total_cost

    # Quick metrics
    m1,m2,m3 = st.columns(3)
    m1.metric("💰 มูลค่าวันนี้",  f"${total_val:,.2f}")
    m2.metric("💵 ต้นทุนรวม",    f"${total_cost:,.2f}")
    m3.metric("📈 กำไร/ขาดทุน",  f"${total_pnl:+,.2f}",
              f"{(total_pnl/total_cost*100):+.2f}%" if total_cost else "0%",
              delta_color="normal" if total_pnl>=0 else "inverse")

    st.divider()

    # ── สร้าง prompt ตาม mode ───────────────────────────────────────────────────
    def build_portfolio_summary(data: list) -> str:
        lines = []
        for d in data:
            lines.append(
                f"- {d['symbol']}: {d['qty']} หุ้น | ราคา ${d['current_price']:.2f} "
                f"({d['change_pct']:+.2f}% วันนี้) | กำไร/ขาดทุน ${d['pnl']:+,.2f} ({d['pnl_pct']:+.2f}%)"
            )
        return "\n".join(lines)

    if sum_mode == "📊 วันนี้":
        if st.button("🤖 AI สรุปพอร์ตวันนี้", type="primary", use_container_width=True, key="sum_today"):
            portfolio_text = build_portfolio_summary(today_data)
            prompt = f"""
คุณเป็น AI ที่ปรึกษาการลงทุนมืออาชีพ วันนี้คือ {datetime.now().strftime('%d %B %Y')}

พอร์ตการลงทุนของผู้ใช้วันนี้:
{portfolio_text}

มูลค่ารวม: ${total_val:,.2f} | ต้นทุน: ${total_cost:,.2f} | กำไร/ขาดทุน: ${total_pnl:+,.2f}

กรุณาสรุปสั้นๆ ในรูปแบบ:

## 📊 สรุปภาพรวมพอร์ตวันนี้
(2-3 ประโยค)

## 🌟 หุ้นที่ทำได้ดีวันนี้
- (bullet points)

## ⚠️ หุ้นที่น่าเป็นห่วง
- (bullet points)

## 💡 คำแนะนำสั้นๆ
(1-2 ประโยค)

ตอบเป็นภาษาไทย กระชับ อ่านง่าย
"""
            with st.spinner("AI กำลังสรุปพอร์ต..."):
                result = _call_ai(prompt, max_tokens=1000)
            st.markdown(f'<div class="ai-result">{result}</div>', unsafe_allow_html=True)

    elif sum_mode == "📅 เปรียบเทียบวันนี้ vs เมื่อวาน":
        # ดึง snapshot เมื่อวานจาก Snowflake
        hist_df = load_portfolio_history(st.session_state.user_id, 7)

        if st.button("🤖 AI เปรียบเทียบวันนี้ vs เมื่อวาน", type="primary", use_container_width=True, key="sum_compare"):
            today_text = build_portfolio_summary(today_data)

            if not hist_df.empty and len(hist_df) >= 2:
                yesterday_val = float(hist_df.iloc[-2]["TOTAL_VALUE"]) if "TOTAL_VALUE" in hist_df.columns else total_val
                change_val    = total_val - yesterday_val
                change_pct    = (change_val / yesterday_val * 100) if yesterday_val else 0
                yesterday_text = f"มูลค่าเมื่อวาน: ${yesterday_val:,.2f} | เปลี่ยนแปลง: ${change_val:+,.2f} ({change_pct:+.2f}%)"
            else:
                yesterday_text = "ไม่มีข้อมูล Snapshot เมื่อวาน (กด 'บันทึก Snapshot' ในหน้า Portfolio ก่อนนะครับ)"

            prompt = f"""
คุณเป็น AI ที่ปรึกษาการลงทุน เปรียบเทียบพอร์ตวันนี้กับเมื่อวาน

พอร์ตวันนี้ ({datetime.now().strftime('%d/%m/%Y')}):
{today_text}
มูลค่ารวม: ${total_val:,.2f}

ข้อมูลเมื่อวาน:
{yesterday_text}

กรุณาวิเคราะห์ในรูปแบบ:

## 📊 เปรียบเทียบวันนี้ vs เมื่อวาน
(สรุปการเปลี่ยนแปลงโดยรวม)

## 📈 สิ่งที่ดีขึ้น
- (bullet points)

## 📉 สิ่งที่แย่ลง
- (bullet points)

## 💡 ควรทำอะไรต่อ?
(คำแนะนำสั้นๆ)

ตอบเป็นภาษาไทย กระชับ อ่านง่าย
"""
            with st.spinner("AI กำลังเปรียบเทียบ..."):
                result = _call_ai(prompt, max_tokens=1000)
            st.markdown(f'<div class="ai-result">{result}</div>', unsafe_allow_html=True)

            if hist_df.empty:
                st.info("💡 เพื่อให้การเปรียบเทียบแม่นยำขึ้น กด 'บันทึก Snapshot' ในหน้า Home → แท็บพอร์ตโฟลิโอ ทุกวันครับ")

    else:  # เลือกวันที่
        selected_date = st.date_input("เลือกวันที่", value=date.today() - timedelta(days=1),
                                      max_value=date.today(), key="sum_date")

        if st.button(f"🤖 AI สรุปพอร์ตวันที่ {selected_date}", type="primary",
                     use_container_width=True, key="sum_date_run"):
            hist_df = load_portfolio_history(st.session_state.user_id, 90)

            if not hist_df.empty:
                date_col = "SNAPSHOT_DATE" if "SNAPSHOT_DATE" in hist_df.columns else hist_df.columns[0]
                hist_df[date_col] = pd.to_datetime(hist_df[date_col]).dt.date
                day_data = hist_df[hist_df[date_col] == selected_date]

                if not day_data.empty:
                    val_col = "TOTAL_VALUE" if "TOTAL_VALUE" in day_data.columns else day_data.columns[1]
                    snap_val = float(day_data[val_col].iloc[0])
                    snap_text = f"มูลค่าพอร์ตวันที่ {selected_date}: ${snap_val:,.2f}"
                else:
                    snap_text = f"ไม่มีข้อมูล Snapshot วันที่ {selected_date}"
            else:
                snap_text = "ไม่มีข้อมูล Snapshot ใน Snowflake"

            today_text = build_portfolio_summary(today_data)
            prompt = f"""
คุณเป็น AI ที่ปรึกษาการลงทุน

ข้อมูล Snapshot วันที่ {selected_date}:
{snap_text}

พอร์ตปัจจุบัน (วันนี้ {datetime.now().strftime('%d/%m/%Y')}):
{today_text}
มูลค่ารวมวันนี้: ${total_val:,.2f}

กรุณาวิเคราะห์ในรูปแบบ:

## 📅 สรุปพอร์ต ณ วันที่ {selected_date}
(อธิบายสถานการณ์วันนั้น)

## 🔄 การเปลี่ยนแปลงจากวันนั้นถึงวันนี้
(เปรียบเทียบมูลค่าและทิศทาง)

## 💡 บทเรียนและข้อสังเกต
(1-2 ประโยค)

ตอบเป็นภาษาไทย กระชับ อ่านง่าย
"""
            with st.spinner(f"AI กำลังสรุปพอร์ตวันที่ {selected_date}..."):
                result = _call_ai(prompt, max_tokens=1000)
            st.markdown(f'<div class="ai-result">{result}</div>', unsafe_allow_html=True)

            if "ไม่มีข้อมูล Snapshot" in snap_text:
                st.info("💡 กด 'บันทึก Snapshot' ในหน้า Home → แท็บพอร์ตโฟลิโอ ทุกวันเพื่อให้มีข้อมูลย้อนหลังครับ")
