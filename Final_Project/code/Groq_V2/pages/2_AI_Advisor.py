"""
pages/3_🤖_AI_Advisor.py
Non-AI Mode vs AI Mode (Gemini) — วิเคราะห์หุ้น, สรุปข่าว, พยากรณ์ราคา
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.data_fetcher import get_current_price, get_price_history, compute_technicals, get_news
from utils.ai_advisor import analyze_stock_ai, summarize_news_ai, predict_price_ai

st.set_page_config(page_title="AI Advisor — TradeX", layout="wide", page_icon="🤖")

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
    border-left:3px solid #7C3AED; }
  .nonai-result { background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:20px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🤖 AI Advisor")
st.caption("วิเคราะห์พอร์ตและประวัติการเทรดเพื่อแนะนำหุ้นที่เหมาะสม")

# ── Mode Toggle ───────────────────────────────────────────────────────────────
col_mode, col_sym, col_btn = st.columns([1.5, 2, 1])
with col_mode:
    mode = st.radio("เลือก Mode", ["📊 Non-AI", "🤖 AI (Gemini)"], horizontal=True,
                    help="Non-AI ใช้ตัวชี้วัด Technical ล้วนๆ\nAI Mode ใช้ Gemini วิเคราะห์เชิงลึก")

with col_sym:
    symbol = st.text_input("หุ้นที่ต้องการวิเคราะห์", placeholder="เช่น AAPL, TSLA, NVDA...",
                           value="AAPL").upper().strip()
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("✨ วิเคราะห์", use_container_width=True, type="primary")

is_ai = "AI" in mode

# Mode badge
if is_ai:
    st.markdown('<span class="ai-badge">🤖 AI Mode — Powered by Google Gemini 1.5 Flash</span>', unsafe_allow_html=True)
else:
    st.markdown('<span class="nonai-badge">📊 Non-AI Mode — Rule-based Technical Analysis</span>', unsafe_allow_html=True)

st.divider()

if analyze_btn or symbol:
    # ── Load Data ─────────────────────────────────────────────────────────────
    with st.spinner(f"กำลังโหลดข้อมูล {symbol}..."):
        info   = get_current_price(symbol)
        df_raw = get_price_history(symbol, "6mo")

    if df_raw.empty:
        st.error(f"❌ ไม่พบข้อมูล {symbol}")
        st.stop()

    df   = compute_technicals(df_raw)
    last = df.iloc[-1]
    news = get_news(symbol)

    # Technical values
    rsi        = last["RSI"]
    macd       = last["MACD"]
    macd_sig   = last["MACD_Signal"]
    price      = info["price"]
    ma50       = last["MA50"]
    ma200      = last["MA200"]
    bb_upper   = last["BB_Upper"]
    bb_lower   = last["BB_Lower"]
    bb_pos     = "Upper Band" if price > bb_upper else ("Lower Band" if price < bb_lower else "Middle")

    technicals = {
        "rsi": round(rsi,2) if not pd.isna(rsi) else "N/A",
        "macd": round(macd,4) if not pd.isna(macd) else "N/A",
        "macd_signal": "Bullish" if macd > macd_sig else "Bearish",
        "macd_signal_val": round(macd_sig,4) if not pd.isna(macd_sig) else "N/A",
        "vs_ma50":  f"{'เหนือ' if price > ma50 else 'ใต้'} MA50 ({(price/ma50-1)*100:+.1f}%)" if not pd.isna(ma50) else "N/A",
        "vs_ma200": f"{'เหนือ' if price > ma200 else 'ใต้'} MA200 ({(price/ma200-1)*100:+.1f}%)" if not pd.isna(ma200) else "N/A",
        "above_ma50":  price > ma50,
        "above_ma200": price > ma200,
        "bb_position": bb_pos,
    }

    # ── Layout ────────────────────────────────────────────────────────────────
    left, right = st.columns([1.2, 1], gap="large")

    # ─ Left: Quick Technical Summary (Non-AI) ─────────────────────────────────
    with left:
        st.markdown('<div class="section-header">📊 Technical Scorecard</div>', unsafe_allow_html=True)

        # Scoring
        score = 0
        signals = []
        if not pd.isna(rsi):
            if rsi < 30:   score += 2; signals.append(("🟢", "RSI Oversold — โอกาสฟื้นตัว"))
            elif rsi > 70: score -= 2; signals.append(("🔴", "RSI Overbought — ระวังการปรับฐาน"))
            else:          signals.append(("🟡", f"RSI Neutral ({rsi:.1f})"))

        if not pd.isna(macd) and not pd.isna(macd_sig):
            if macd > macd_sig: score += 1; signals.append(("🟢", "MACD Bullish Crossover"))
            else:               score -= 1; signals.append(("🔴", "MACD Bearish — แรงขายครอบงำ"))

        if not pd.isna(ma50):
            if price > ma50:  score += 1; signals.append(("🟢", f"ราคาเหนือ MA50"))
            else:             score -= 1; signals.append(("🔴", f"ราคาต่ำกว่า MA50"))

        if not pd.isna(ma200):
            if price > ma200: score += 1; signals.append(("🟢", "อยู่ใน Long-term Uptrend (เหนือ MA200)"))
            else:             score -= 1; signals.append(("🔴", "อยู่ใน Long-term Downtrend (ใต้ MA200)"))

        # Score gauge
        score_label = "Strong Buy 🚀" if score >= 3 else \
                      "Buy 📈" if score >= 1 else \
                      "Hold ⚖️" if score == 0 else \
                      "Sell 📉" if score >= -2 else "Strong Sell 🚨"
        score_color = "#34d399" if score >= 2 else "#10b981" if score >= 1 else \
                      "#f59e0b" if score == 0 else "#f87171"

        st.markdown(f"""
        <div style="background:#111827;border:1px solid {score_color}44;border-radius:12px;
                    padding:20px;text-align:center;margin-bottom:16px;">
          <div style="color:#94a3b8;font-size:0.75rem;text-transform:uppercase;">Technical Score</div>
          <div style="font-family:'Space Mono',monospace;font-size:2.5rem;color:{score_color};
                      font-weight:700;line-height:1.2;">{score:+d}</div>
          <div style="color:{score_color};font-size:1rem;font-weight:600;">{score_label}</div>
        </div>
        """, unsafe_allow_html=True)

        for icon, msg in signals:
            st.markdown(f'<div style="padding:6px 0;font-size:0.85rem;">{icon} {msg}</div>', unsafe_allow_html=True)

        # Price targets (Non-AI rule-based)
        st.markdown('<div class="section-header">🎯 เป้าหมายราคา (Rule-based)</div>', unsafe_allow_html=True)
        analyst_target = info.get("target_mean")
        resistance     = float(last["BB_Upper"]) if not pd.isna(last["BB_Upper"]) else price * 1.05
        support        = float(last["BB_Lower"]) if not pd.isna(last["BB_Lower"]) else price * 0.95

        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("🛡️ Support",    f"${support:,.2f}")
        col_t2.metric("💲 ปัจจุบัน",   f"${price:,.2f}")
        col_t3.metric("⬆️ Resistance", f"${resistance:,.2f}")
        if analyst_target:
            st.metric("🎯 Analyst Target", f"${analyst_target:,.2f}",
                      f"{(analyst_target/price-1)*100:+.1f}% upside")

    # ─ Right: Mini Chart ──────────────────────────────────────────────────────
    with right:
        st.markdown('<div class="section-header">📈 ราคา 6 เดือน</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"], mode="lines",
            line=dict(color="#00D4FF", width=2), fill="tozeroy",
            fillcolor="rgba(0,212,255,0.06)", name="Close",
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], mode="lines",
            line=dict(color="#f59e0b", width=1.2, dash="dash"), name="MA50"))
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=0,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color="#475569"),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", color="#475569"),
            legend=dict(font=dict(color="#94a3b8",size=10), orientation="h", y=1.1),
            showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

        # News Snapshot
        st.markdown('<div class="section-header">📰 ข่าวล่าสุด</div>', unsafe_allow_html=True)
        for item in news[:3]:
            content = item.get("content", item)
            title   = content.get("title", item.get("title",""))
            url     = content.get("canonicalUrl",{}).get("url", item.get("link","#"))
            st.markdown(f'<div style="padding:5px 0;"><a href="{url}" target="_blank" style="color:#94a3b8;font-size:0.8rem;text-decoration:none;">📰 {title[:75]}...</a></div>', unsafe_allow_html=True)

    st.divider()

    # ── AI Analysis Section ───────────────────────────────────────────────────
    if is_ai:
        st.markdown("### 🤖 การวิเคราะห์เชิงลึกด้วย AI")

        ai_tab1, ai_tab2, ai_tab3 = st.tabs(["🔍 วิเคราะห์หุ้น", "📰 Sentiment ข่าว", "🔮 พยากรณ์ราคา"])

        with ai_tab1:
            if st.button("🚀 วิเคราะห์ด้วย Gemini AI", type="primary", use_container_width=True):
                with st.spinner("AI กำลังวิเคราะห์... (อาจใช้เวลา 10-20 วินาที)"):
                    result = analyze_stock_ai(symbol, info, news, technicals)
                st.markdown(f'<div class="ai-result">{result}</div>', unsafe_allow_html=True)
            else:
                st.info("กด 'วิเคราะห์ด้วย Gemini AI' เพื่อรับการวิเคราะห์เชิงลึก (ผลจะถูก cache ใน MongoDB 6 ชั่วโมง)")

        with ai_tab2:
            if st.button("📰 วิเคราะห์ Sentiment ข่าว", type="primary", use_container_width=True):
                with st.spinner("AI กำลังสรุปข่าว..."):
                    sentiment = summarize_news_ai(symbol, news)
                st.markdown(f'<div class="ai-result">{sentiment}</div>', unsafe_allow_html=True)

        with ai_tab3:
            if st.button("🔮 พยากรณ์ราคาระยะสั้น", type="primary", use_container_width=True):
                with st.spinner("AI กำลังประเมินทิศทางราคา..."):
                    prediction = predict_price_ai(symbol, price, technicals)
                st.markdown(f'<div class="ai-result">{prediction}</div>', unsafe_allow_html=True)

    else:
        # Non-AI: แสดงตาราง Indicator สรุป
        st.markdown("### 📊 สรุป Technical Indicators")
        summary_data = {
            "Indicator": ["RSI (14)", "MACD vs Signal", "Price vs MA20", "Price vs MA50", "Price vs MA200",
                          "Bollinger Band Position", "52W High", "52W Low"],
            "ค่า": [
                f"{rsi:.1f}" if not pd.isna(rsi) else "N/A",
                f"{macd:.4f} / {macd_sig:.4f}" if not pd.isna(macd) else "N/A",
                f"${float(last['MA20']):.2f} ({'เหนือ' if price>float(last['MA20']) else 'ใต้'})" if not pd.isna(last['MA20']) else "N/A",
                f"${float(last['MA50']):.2f} ({'เหนือ' if price>float(last['MA50']) else 'ใต้'})" if not pd.isna(last['MA50']) else "N/A",
                f"${float(last['MA200']):.2f} ({'เหนือ' if price>float(last['MA200']) else 'ใต้'})" if not pd.isna(last['MA200']) else "N/A",
                bb_pos,
                f"${info['52w_high']:,.2f}" if info["52w_high"] else "N/A",
                f"${info['52w_low']:,.2f}" if info["52w_low"] else "N/A",
            ],
            "สัญญาณ": [
                "🟢 Oversold" if not pd.isna(rsi) and rsi<30 else "🔴 Overbought" if not pd.isna(rsi) and rsi>70 else "🟡 Neutral",
                "🟢 Bullish" if not pd.isna(macd) and macd>macd_sig else "🔴 Bearish",
                "🟢" if not pd.isna(last['MA20']) and price>float(last['MA20']) else "🔴",
                "🟢" if not pd.isna(last['MA50']) and price>float(last['MA50']) else "🔴",
                "🟢" if not pd.isna(last['MA200']) and price>float(last['MA200']) else "🔴",
                "🔴" if bb_pos=="Upper Band" else "🟢" if bb_pos=="Lower Band" else "🟡",
                f"{'🟢' if info['52w_high'] and price >= info['52w_high']*0.95 else '🟡'}",
                f"{'🔴' if info['52w_low'] and price <= info['52w_low']*1.05 else '🟡'}",
            ]
        }
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        st.caption("💡 เปลี่ยนเป็น AI Mode เพื่อรับการวิเคราะห์เชิงลึกจาก Gemini AI")
