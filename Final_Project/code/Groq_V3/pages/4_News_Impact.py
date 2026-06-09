"""
pages/6_📰_News_Impact.py
AI วิเคราะห์ข่าวล่าสุดและประเมินผลกระทบต่อหุ้นในพอร์ต
รองรับทั้ง Groq และ Gemini — เปลี่ยนได้ที่ USE_GROQ
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import yfinance as yf
from groq import Groq

from utils.data_fetcher import get_current_price
from utils.db_mongo import load_portfolio

st.set_page_config(page_title="News Impact — SmartInvest", layout="wide", page_icon="📰")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .section-header {
    font-size:0.7rem;font-weight:600;color:#00D4FF;text-transform:uppercase;
    letter-spacing:0.12em;margin:20px 0 10px;
    border-bottom:1px solid rgba(0,212,255,0.2);padding-bottom:6px;
  }
  .impact-bullish {
    background:linear-gradient(135deg,#064e3b,#065f46);
    border:1px solid #10b981;border-radius:10px;padding:14px;margin-bottom:8px;
  }
  .impact-bearish {
    background:linear-gradient(135deg,#450a0a,#7f1d1d);
    border:1px solid #ef4444;border-radius:10px;padding:14px;margin-bottom:8px;
  }
  .impact-neutral {
    background:linear-gradient(135deg,#1c1917,#292524);
    border:1px solid #78716c;border-radius:10px;padding:14px;margin-bottom:8px;
  }
  .badge-bull { background:#065f46;color:#34d399;padding:3px 10px;border-radius:20px;font-size:0.78rem;font-weight:600; }
  .badge-bear { background:#7f1d1d;color:#f87171;padding:3px 10px;border-radius:20px;font-size:0.78rem;font-weight:600; }
  .badge-neu  { background:#292524;color:#a8a29e;padding:3px 10px;border-radius:20px;font-size:0.78rem;font-weight:600; }
  .ticker-tag {
    display:inline-block;background:#1e3a5f;color:#60a5fa;
    padding:2px 8px;border-radius:6px;font-size:0.75rem;font-weight:600;
    margin:2px;font-family:'Space Mono',monospace;
  }
</style>
""", unsafe_allow_html=True)

# ── เปลี่ยน True/False เพื่อสลับ AI ──────────────────────────────────────────
USE_GROQ = True   # True = Groq | False = Gemini

# ── AI Client ─────────────────────────────────────────────────────────────────
@st.cache_resource
def get_ai_client():
    if USE_GROQ:
        try:
            api_key = st.secrets.get("GROQ_API_KEY", "")
            if not api_key or api_key == "YOUR_GROQ_API_KEY_HERE":
                return None
            return Groq(api_key=api_key)
        except Exception as e:
            st.error(f"Groq init error: {e}")
            return None
    else:
        try:
            import google.generativeai as genai
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if not api_key:
                return None
            genai.configure(api_key=api_key)
            return genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                generation_config={"temperature": 0.3, "max_output_tokens": 2000},
            )
        except Exception as e:
            st.error(f"Gemini init error: {e}")
            return None


def call_ai(client, prompt: str, max_tokens: int = 2000) -> str:
    if USE_GROQ:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return response.choices[0].message.content
    else:
        response = client.generate_content(prompt)
        return response.text


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📰 News Impact Analyzer")
ai_label = "Groq (Llama 3.3)" if USE_GROQ else "Google Gemini"
st.caption(f"AI วิเคราะห์ข่าวล่าสุดและประเมินผลกระทบต่อหุ้นในพอร์ต — Powered by {ai_label}")

# ── Load Portfolio ─────────────────────────────────────────────────────────────
if "portfolio" not in st.session_state:
    st.session_state.portfolio = load_portfolio()

holdings = st.session_state.portfolio
if not holdings:
    st.warning("⚠️ ยังไม่มีหุ้นในพอร์ต — ไปที่หน้า Portfolio เพื่อเพิ่มหุ้นก่อนครับ")
    st.stop()

portfolio_symbols = [h["symbol"] for h in holdings]

# ── Settings ──────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    extra = st.text_input(
        "เพิ่มหุ้นนอกพอร์ตที่อยากติดตามข่าว (optional)",
        placeholder="เช่น GOOGL, META",
    )
    extra_syms = [s.strip().upper() for s in extra.split(",") if s.strip()] if extra else []
    all_symbols = list(dict.fromkeys(portfolio_symbols + extra_syms))

with col2:
    news_count = st.selectbox("จำนวนข่าวต่อหุ้น", [3, 5, 8], index=1)

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🚀 วิเคราะห์ข่าว", type="primary", use_container_width=True)

st.markdown(f"""
<div style="background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:12px;margin-bottom:8px;">
  <span style="color:#64748b;font-size:0.78rem;">หุ้นที่จะวิเคราะห์:</span><br>
  {''.join(f'<span class="ticker-tag">{s}</span>' for s in all_symbols)}
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Fetch News ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def fetch_all_news(symbols: tuple, count: int) -> list:
    all_news = []
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            news = ticker.news or []
            for item in news[:count]:
                content = item.get("content", item)
                title   = content.get("title", item.get("title", ""))
                summary = content.get("summary", item.get("summary", ""))
                url     = content.get("canonicalUrl", {}).get("url", item.get("link", "#"))
                pub     = content.get("pubDate", "")
                if title:
                    all_news.append({
                        "source_ticker": sym,
                        "title": title,
                        "summary": summary[:300] if summary else "",
                        "url": url,
                        "pub_date": pub,
                    })
        except:
            pass
    seen, unique = set(), []
    for n in all_news:
        if n["title"] not in seen:
            seen.add(n["title"])
            unique.append(n)
    return unique


def analyze_news_impact(client, news_list: list, portfolio_symbols: list) -> list:
    news_text = "\n".join([
        f"{i+1}. [{n['source_ticker']}] {n['title']}"
        + (f"\n   สรุป: {n['summary']}" if n['summary'] else "")
        for i, n in enumerate(news_list[:20])
    ])
    symbols_str = ", ".join(portfolio_symbols)

    prompt = f"""
คุณเป็น AI นักวิเคราะห์หุ้นมืออาชีพ

หุ้นในพอร์ตของผู้ใช้: {symbols_str}

ข่าวล่าสุด:
{news_text}

วิเคราะห์แต่ละข่าวและตอบในรูปแบบ JSON array เท่านั้น ไม่ต้องมีคำอธิบายเพิ่ม ไม่ต้องมี markdown:

[
  {{
    "news_index": 1,
    "title": "ชื่อข่าวสั้น ไม่เกิน 80 ตัวอักษร",
    "summary_th": "สรุปเนื้อหาข่าวภาษาไทย 3-4 ประโยค ครอบคลุม: (1) เกิดอะไรขึ้น/ใครทำอะไร (2) ทำไมถึงสำคัญ (3) ผลที่ตามมาหรือแนวโน้มที่คาด",
    "affected_tickers": ["AAPL"],
    "sentiment": "bullish",
    "impact_pct": 1.5,
    "confidence": 70,
    "impact_reason": "อธิบาย 2-3 ประโยค ว่าข่าวนี้กระทบหุ้นอย่างไร เช่น รายได้ ส่วนแบ่งตลาด ความเชื่อมั่นนักลงทุน และระยะสั้น/ยาว",
    "reason": "สรุปสั้น 1 ประโยค ว่าทำไมถึง bullish/bearish/neutral"
  }}
]

กฎสำคัญ:
- summary_th: สรุปทุกข่าว ไม่ว่าจะกระทบพอร์ตหรือไม่ก็ตาม ห้ามสั้นกว่า 3 ประโยค
- impact_reason: ใส่เฉพาะข่าวที่กระทบหุ้นในพอร์ต ถ้าไม่กระทบให้ใส่ ""
- affected_tickers: ใส่เฉพาะหุ้นจาก ({symbols_str}) ที่กระทบจริงๆ ถ้าไม่กระทบใส่ []
- sentiment: "bullish", "bearish", หรือ "neutral" เท่านั้น
- impact_pct: บวก=ขึ้น, ลบ=ลง ช่วง -10 ถึง 10
- confidence: 0-100
- ตอบ JSON เท่านั้น ห้ามมี backticks หรือ markdown
"""
    try:
        text = call_ai(client, prompt, max_tokens=4000).strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        st.error(f"AI วิเคราะห์ไม่สำเร็จ: {e}")
        return []


# ── Main ───────────────────────────────────────────────────────────────────────
if analyze_btn:
    client = get_ai_client()
    if client is None:
        key_name = "GROQ_API_KEY" if USE_GROQ else "GEMINI_API_KEY"
        st.error(f"⚠️ กรุณาตั้งค่า {key_name} ใน secrets.toml")
        st.stop()

    with st.spinner("📡 กำลังดึงข่าวล่าสุด..."):
        news_list = fetch_all_news(tuple(all_symbols), news_count)

    if not news_list:
        st.warning("ไม่พบข่าวล่าสุด")
        st.stop()

    st.success(f"✅ ดึงข่าวมาได้ {len(news_list)} ข่าว จาก {len(all_symbols)} หุ้น")

    with st.spinner(f"🤖 {ai_label} กำลังวิเคราะห์ผลกระทบ..."):
        results = analyze_news_impact(client, news_list, portfolio_symbols)

    if not results:
        st.stop()

    st.session_state["news_results"] = results
    st.session_state["news_list"]    = news_list


# ── Display ────────────────────────────────────────────────────────────────────
if "news_results" in st.session_state:
    results   = st.session_state["news_results"]
    news_list = st.session_state["news_list"]

    # Summary per stock
    st.markdown('<div class="section-header">📊 สรุปผลกระทบต่อพอร์ต</div>', unsafe_allow_html=True)
    impact_summary = {sym: {"bull":0,"bear":0,"total_pct":0,"count":0} for sym in portfolio_symbols}
    for r in results:
        for sym in r.get("affected_tickers", []):
            if sym in impact_summary:
                impact_summary[sym]["count"]     += 1
                impact_summary[sym]["total_pct"] += r.get("impact_pct", 0)
                if r.get("sentiment") == "bullish": impact_summary[sym]["bull"] += 1
                elif r.get("sentiment") == "bearish": impact_summary[sym]["bear"] += 1

    affected = {k: v for k, v in impact_summary.items() if v["count"] > 0}
    if affected:
        cols = st.columns(min(len(affected), 4))
        for i, (sym, data) in enumerate(affected.items()):
            avg_pct = data["total_pct"] / data["count"] if data["count"] else 0
            color   = "#34d399" if avg_pct > 0 else "#f87171" if avg_pct < 0 else "#94a3b8"
            arrow   = "▲" if avg_pct > 0 else "▼" if avg_pct < 0 else "◆"
            with cols[i % len(cols)]:
                st.markdown(f"""
                <div style="background:#111827;border:1px solid {color}44;border-radius:12px;
                            padding:14px;text-align:center;margin-bottom:8px;">
                  <div style="font-family:'Space Mono',monospace;font-size:1.1rem;font-weight:700;color:#e2e8f0;">{sym}</div>
                  <div style="font-size:1.4rem;font-weight:700;color:{color};">{arrow} {avg_pct:+.1f}%</div>
                  <div style="font-size:0.72rem;color:#64748b;margin-top:4px;">{data['count']} ข่าว · 🟢{data['bull']} 🔴{data['bear']}</div>
                </div>
                """, unsafe_allow_html=True)

        # Bar chart
        st.markdown('<div class="section-header">📈 ผลกระทบคาดการณ์ต่อหุ้นในพอร์ต</div>', unsafe_allow_html=True)
        syms_aff = list(affected.keys())
        avgs     = [affected[s]["total_pct"]/affected[s]["count"] for s in syms_aff]
        fig = go.Figure(go.Bar(
            x=syms_aff, y=avgs,
            marker_color=["#34d399" if v > 0 else "#f87171" for v in avgs],
            text=[f"{v:+.1f}%" for v in avgs], textposition="outside",
        ))
        fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)")
        fig.update_layout(
            height=260, margin=dict(l=0,r=0,t=20,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#475569"),
            xaxis=dict(color="#475569"), showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("⚠️ ตัวเลข % เป็นการประมาณการณ์จาก AI เท่านั้น ไม่ใช่การรับประกันผลตอบแทน")
    else:
        st.info("ข่าวที่ดึงมาไม่กระทบหุ้นในพอร์ตโดยตรง")

    st.divider()

    # News cards with filter
    st.markdown('<div class="section-header">📋 รายละเอียดแต่ละข่าว</div>', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4 = st.columns(4)
    if fc1.button("📰 ทั้งหมด",     use_container_width=True): st.session_state.news_filter = "all"
    if fc2.button("🟢 Bullish",     use_container_width=True): st.session_state.news_filter = "bullish"
    if fc3.button("🔴 Bearish",     use_container_width=True): st.session_state.news_filter = "bearish"
    if fc4.button("🎯 กระทบพอร์ต", use_container_width=True): st.session_state.news_filter = "impacted"
    if "news_filter" not in st.session_state: st.session_state.news_filter = "all"

    result_map = {r["news_index"]: r for r in results}
    displayed  = 0

    for i, news in enumerate(news_list):
        r         = result_map.get(i + 1, {})
        sentiment  = r.get("sentiment", "neutral")
        affected_t = r.get("affected_tickers", [])
        impact_pct = r.get("impact_pct", 0)
        confidence = r.get("confidence", 0)
        reason     = r.get("reason", "")
        impact_reason = r.get("impact_reason", "")
        summary_th = r.get("summary_th", "")

        filt = st.session_state.news_filter
        if filt == "bullish"  and sentiment != "bullish":  continue
        if filt == "bearish"  and sentiment != "bearish":  continue
        if filt == "impacted" and not affected_t:          continue

        if sentiment == "bullish" and affected_t:
            card_class, badge = "impact-bullish", '<span class="badge-bull">🟢 Bullish</span>'
        elif sentiment == "bearish" and affected_t:
            card_class, badge = "impact-bearish", '<span class="badge-bear">🔴 Bearish</span>'
        else:
            card_class, badge = "impact-neutral", '<span class="badge-neu">⚪ Neutral</span>'

        ticker_html = "".join([f'<span class="ticker-tag">{t}</span>' for t in affected_t]) \
                      or '<span style="color:#475569;font-size:0.78rem;">ไม่กระทบพอร์ต</span>'

        if affected_t and impact_pct != 0:
            arrow     = "▲" if impact_pct > 0 else "▼"
            imp_color = "#34d399" if impact_pct > 0 else "#f87171"
            impact_html = f'<span style="color:{imp_color};font-family:Space Mono,monospace;font-weight:700;">{arrow} {impact_pct:+.1f}%</span> <span style="color:#64748b;font-size:0.75rem;">· มั่นใจ {confidence}%</span>'
        else:
            impact_html = '<span style="color:#475569;font-size:0.8rem;">—</span>'

        pub_date   = news.get('pub_date','')[:10]
        news_url   = news['url']
        news_title = news['title']

        # card header
        st.markdown(f"""
        <div class="{card_class}" style="border-radius:10px 10px 0 0;margin-bottom:0;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div style="flex:1;">
              <a href="{news_url}" target="_blank"
                 style="color:#e2e8f0;font-weight:600;font-size:0.9rem;text-decoration:none;line-height:1.4;">
                {news_title}
              </a>
              <div style="margin-top:8px;">{ticker_html}</div>
            </div>
            <div style="text-align:right;min-width:120px;">
              {badge}
              <div style="margin-top:8px;">{impact_html}</div>
              <div style="color:#475569;font-size:0.7rem;margin-top:4px;">{pub_date}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # card body — แยก render เพื่อให้ text ไม่ escape
        card_bg     = "#053d2e" if (sentiment=="bullish" and affected_t) else "#3d0a0a" if (sentiment=="bearish" and affected_t) else "#161412"
        card_border = "#10b981" if (sentiment=="bullish" and affected_t) else "#ef4444" if (sentiment=="bearish" and affected_t) else "#57534e"
        body_parts  = []
        if summary_th:
            body_parts.append(f'<div style="color:#cbd5e1;font-size:0.82rem;line-height:1.65;margin-bottom:7px;">📝 {summary_th}</div>')
        if impact_reason:
            body_parts.append(f'<div style="color:#60a5fa;font-size:0.82rem;line-height:1.65;margin-bottom:5px;">🔍 {impact_reason}</div>')
        if reason:
            body_parts.append(f'<div style="color:#94a3b8;font-size:0.75rem;line-height:1.5;">💡 {reason}</div>')

        if body_parts:
            body_html = "".join(body_parts)
            st.markdown(
                f'<div style="background:{card_bg};border:1px solid {card_border};'
                f'border-top:none;border-radius:0 0 10px 10px;'
                f'padding:10px 14px 13px;margin-bottom:10px;">'
                f'{body_html}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown('<div style="margin-bottom:10px;"></div>', unsafe_allow_html=True)

        displayed += 1

    if displayed == 0:
        st.info("ไม่มีข่าวที่ตรงกับ filter ที่เลือก")

    # Summary table
    st.divider()
    st.markdown('<div class="section-header">📑 ตารางสรุปผล</div>', unsafe_allow_html=True)
    table_rows = []
    for i, r in enumerate(results):
        sent      = r.get("sentiment","neutral")
        sent_icon = "🟢" if sent=="bullish" else "🔴" if sent=="bearish" else "⚪"
        table_rows.append({
            "ข่าว":        (r.get("title", news_list[i]["title"] if i < len(news_list) else ""))[:60] + "...",
            "หุ้นที่กระทบ": ", ".join(r.get("affected_tickers",[])) or "—",
            "Sentiment":   f"{sent_icon} {sent.capitalize()}",
            "Impact %":    f"{r.get('impact_pct',0):+.1f}%",
            "ความมั่นใจ":  f"{r.get('confidence',0)}%",
        })
    if table_rows:
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

else:
    st.markdown("""
    <div style="background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:16px;
                padding:60px;text-align:center;">
      <div style="font-size:3rem;margin-bottom:16px;">📰</div>
      <div style="color:#94a3b8;font-size:1rem;margin-bottom:8px;">
        กด <strong style="color:#00D4FF;">วิเคราะห์ข่าว</strong> เพื่อให้ AI ประเมินผลกระทบต่อพอร์ตของคุณ
      </div>
      <div style="color:#475569;font-size:0.83rem;">AI จะดึงข่าวล่าสุดของหุ้นทุกตัวในพอร์ต แล้ววิเคราะห์ใน 1 request</div>
    </div>
    """, unsafe_allow_html=True)
