"""
pages/6_📰_News_Impact.py
AI วิเคราะห์ข่าวล่าสุดและประเมินผลกระทบต่อหุ้นในพอร์ต
- ดึงข่าวจาก yfinance
- Gemini วิเคราะห์ว่าข่าวแต่ละชิ้นกระทบหุ้นตัวไหน
- ประเมิน Bullish/Bearish และ % ที่คาดว่าจะเปลี่ยนแปลง
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import yfinance as yf

from utils.data_fetcher import get_current_price
from utils.db_mongo import load_portfolio
import google.generativeai as genai

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
  .news-card {
    background:#111827;border:1px solid rgba(255,255,255,0.07);
    border-radius:12px;padding:16px;margin-bottom:10px;
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

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📰 News Impact Analyzer")
st.caption("AI วิเคราะห์ข่าวล่าสุดและประเมินผลกระทบต่อหุ้นในพอร์ตของคุณ")

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
    # ให้เพิ่มหุ้นพิเศษนอกพอร์ตได้ด้วย
    extra = st.text_input(
        "เพิ่มหุ้นนอกพอร์ตที่อยากติดตามข่าว (optional)",
        placeholder="เช่น GOOGL, META",
    )
    extra_syms = [s.strip().upper() for s in extra.split(",") if s.strip()] if extra else []
    all_symbols = list(dict.fromkeys(portfolio_symbols + extra_syms))  # deduplicate

with col2:
    news_count = st.selectbox("จำนวนข่าวต่อหุ้น", [3, 5, 8], index=1)

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🚀 วิเคราะห์ข่าว", type="primary", use_container_width=True)

# แสดงหุ้นที่จะวิเคราะห์
st.markdown(f"""
<div style="background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:12px;margin-bottom:8px;">
  <span style="color:#64748b;font-size:0.78rem;">หุ้นที่จะวิเคราะห์:</span><br>
  {''.join(f'<span class="ticker-tag">{s}</span>' for s in all_symbols)}
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Gemini Setup ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_gemini():
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={"temperature": 0.3, "max_output_tokens": 2000},
        )
    except:
        return None


@st.cache_data(ttl=1800)
def fetch_all_news(symbols: tuple, count: int) -> list:
    """ดึงข่าวทุกหุ้นพร้อมกัน (cache 30 นาที)"""
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
    # deduplicate by title
    seen = set()
    unique = []
    for n in all_news:
        if n["title"] not in seen:
            seen.add(n["title"])
            unique.append(n)
    return unique


def analyze_news_impact(model, news_list: list, portfolio_symbols: list) -> list:
    """
    ส่ง news ทั้งหมดให้ Gemini วิเคราะห์ใน 1 request
    Return: list of {title, affected_tickers, sentiment, impact_pct, reason, confidence}
    """
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

วิเคราะห์แต่ละข่าวและตอบในรูปแบบ JSON array เท่านั้น ไม่ต้องมีคำอธิบายเพิ่ม:

[
  {{
    "news_index": 1,
    "title": "ชื่อข่าว (สั้น ไม่เกิน 80 ตัวอักษร)",
    "affected_tickers": ["AAPL", "MSFT"],
    "sentiment": "bullish",
    "impact_pct": 1.5,
    "confidence": 70,
    "reason": "เหตุผลสั้นๆ ว่าทำไมข่าวนี้กระทบหุ้นเหล่านี้ (1-2 ประโยค)"
  }}
]

กฎ:
- affected_tickers: ใส่เฉพาะหุ้นจากพอร์ต ({symbols_str}) ที่ได้รับผลกระทบจริงๆ ถ้าไม่กระทบเลยให้ใส่ []
- sentiment: "bullish", "bearish", หรือ "neutral"
- impact_pct: ตัวเลขบวก = ราคาน่าจะขึ้น, ลบ = ราคาน่าจะลง เช่น 2.5 หรือ -1.8 (ช่วง -10 ถึง 10)
- confidence: ความมั่นใจ 0-100
- ถ้าข่าวไม่เกี่ยวกับหุ้นในพอร์ตเลย ให้ affected_tickers = [] และ sentiment = "neutral"
- ตอบ JSON เท่านั้น ห้ามมี markdown หรือ backticks
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean up just in case
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        st.error(f"AI วิเคราะห์ไม่สำเร็จ: {e}")
        return []


# ── Main Analysis ──────────────────────────────────────────────────────────────
if analyze_btn:
    model = get_gemini()
    if model is None:
        st.error("⚠️ กรุณาตั้งค่า GEMINI_API_KEY ใน secrets.toml")
        st.stop()

    # Step 1: ดึงข่าว
    with st.spinner("📡 กำลังดึงข่าวล่าสุด..."):
        news_list = fetch_all_news(tuple(all_symbols), news_count)

    if not news_list:
        st.warning("ไม่พบข่าวล่าสุด")
        st.stop()

    st.success(f"✅ ดึงข่าวมาได้ {len(news_list)} ข่าว จาก {len(all_symbols)} หุ้น")

    # Step 2: AI วิเคราะห์
    with st.spinner("🤖 AI กำลังวิเคราะห์ผลกระทบ... (รอสักครู่)"):
        results = analyze_news_impact(model, news_list, portfolio_symbols)

    if not results:
        st.error("ไม่สามารถวิเคราะห์ได้")
        st.stop()

    # เก็บไว้ใน session
    st.session_state["news_results"] = results
    st.session_state["news_list"]    = news_list


# ── Display Results ────────────────────────────────────────────────────────────
if "news_results" in st.session_state:
    results   = st.session_state["news_results"]
    news_list = st.session_state["news_list"]

    # ── Portfolio Impact Summary ───────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 สรุปผลกระทบต่อพอร์ต</div>', unsafe_allow_html=True)

    # รวม impact ต่อหุ้นแต่ละตัว
    impact_summary = {sym: {"bull": 0, "bear": 0, "total_pct": 0, "count": 0} for sym in portfolio_symbols}
    for r in results:
        for sym in r.get("affected_tickers", []):
            if sym in impact_summary:
                impact_summary[sym]["count"] += 1
                impact_summary[sym]["total_pct"] += r.get("impact_pct", 0)
                if r.get("sentiment") == "bullish":
                    impact_summary[sym]["bull"] += 1
                elif r.get("sentiment") == "bearish":
                    impact_summary[sym]["bear"] += 1

    # Summary cards
    affected = {k: v for k, v in impact_summary.items() if v["count"] > 0}
    if affected:
        cols = st.columns(min(len(affected), 4))
        for i, (sym, data) in enumerate(affected.items()):
            avg_pct = data["total_pct"] / data["count"] if data["count"] > 0 else 0
            color   = "#34d399" if avg_pct > 0 else "#f87171" if avg_pct < 0 else "#94a3b8"
            arrow   = "▲" if avg_pct > 0 else "▼" if avg_pct < 0 else "◆"
            col_idx = i % len(cols)
            with cols[col_idx]:
                st.markdown(f"""
                <div style="background:#111827;border:1px solid {color}44;border-radius:12px;
                            padding:14px;text-align:center;margin-bottom:8px;">
                  <div style="font-family:'Space Mono',monospace;font-size:1.1rem;
                              font-weight:700;color:#e2e8f0;">{sym}</div>
                  <div style="font-size:1.4rem;font-weight:700;color:{color};">
                    {arrow} {avg_pct:+.1f}%
                  </div>
                  <div style="font-size:0.72rem;color:#64748b;margin-top:4px;">
                    {data['count']} ข่าว · 🟢{data['bull']} 🔴{data['bear']}
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # Impact Bar Chart
        st.markdown('<div class="section-header">📈 ผลกระทบคาดการณ์ต่อหุ้นในพอร์ต</div>', unsafe_allow_html=True)
        syms_aff = list(affected.keys())
        avgs     = [affected[s]["total_pct"] / affected[s]["count"] for s in syms_aff]
        bar_colors = ["#34d399" if v > 0 else "#f87171" for v in avgs]

        fig = go.Figure(go.Bar(
            x=syms_aff, y=avgs,
            marker_color=bar_colors,
            text=[f"{v:+.1f}%" for v in avgs],
            textposition="outside",
            hovertemplate="%{x}: %{y:+.2f}%<extra></extra>",
        ))
        fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)")
        fig.update_layout(
            height=280, margin=dict(l=0,r=0,t=20,b=0),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                       color="#475569", title="% Impact คาดการณ์"),
            xaxis=dict(color="#475569"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("⚠️ ตัวเลข % เป็นการประมาณการณ์จาก AI เท่านั้น ไม่ใช่การรับประกันผลตอบแทน")
    else:
        st.info("ข่าวที่ดึงมาไม่กระทบหุ้นในพอร์ตโดยตรง")

    st.divider()

    # ── News Detail Cards ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📋 รายละเอียดแต่ละข่าว</div>', unsafe_allow_html=True)

    # Filter tabs
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    with filter_col1:
        show_all      = st.button("📰 ทั้งหมด", use_container_width=True)
    with filter_col2:
        show_bullish  = st.button("🟢 Bullish", use_container_width=True)
    with filter_col3:
        show_bearish  = st.button("🔴 Bearish", use_container_width=True)
    with filter_col4:
        show_impacted = st.button("🎯 กระทบพอร์ต", use_container_width=True)

    if "news_filter" not in st.session_state:
        st.session_state.news_filter = "all"
    if show_all:      st.session_state.news_filter = "all"
    if show_bullish:  st.session_state.news_filter = "bullish"
    if show_bearish:  st.session_state.news_filter = "bearish"
    if show_impacted: st.session_state.news_filter = "impacted"

    # Map results กับ news
    result_map = {r["news_index"]: r for r in results}

    displayed = 0
    for i, news in enumerate(news_list):
        r = result_map.get(i + 1, {})
        sentiment       = r.get("sentiment", "neutral")
        affected        = r.get("affected_tickers", [])
        impact_pct      = r.get("impact_pct", 0)
        confidence      = r.get("confidence", 0)
        reason          = r.get("reason", "")

        # Filter
        filt = st.session_state.news_filter
        if filt == "bullish"  and sentiment != "bullish":  continue
        if filt == "bearish"  and sentiment != "bearish":  continue
        if filt == "impacted" and not affected:            continue

        # Card style
        if sentiment == "bullish" and affected:
            card_class = "impact-bullish"
            badge = '<span class="badge-bull">🟢 Bullish</span>'
        elif sentiment == "bearish" and affected:
            card_class = "impact-bearish"
            badge = '<span class="badge-bear">🔴 Bearish</span>'
        else:
            card_class = "impact-neutral"
            badge = '<span class="badge-neu">⚪ Neutral</span>'

        # Ticker tags
        ticker_html = "".join([f'<span class="ticker-tag">{t}</span>' for t in affected]) if affected else '<span style="color:#475569;font-size:0.78rem;">ไม่กระทบพอร์ต</span>'

        # Impact text
        if affected and impact_pct != 0:
            arrow     = "▲" if impact_pct > 0 else "▼"
            imp_color = "#34d399" if impact_pct > 0 else "#f87171"
            impact_html = f'<span style="color:{imp_color};font-family:Space Mono,monospace;font-weight:700;">{arrow} {impact_pct:+.1f}%</span> <span style="color:#64748b;font-size:0.75rem;">· ความมั่นใจ {confidence}%</span>'
        else:
            impact_html = '<span style="color:#475569;font-size:0.8rem;">—</span>'

        st.markdown(f"""
        <div class="{card_class}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div style="flex:1;">
              <a href="{news['url']}" target="_blank"
                 style="color:#e2e8f0;font-weight:600;font-size:0.9rem;text-decoration:none;line-height:1.4;">
                {news['title']}
              </a>
              <div style="margin-top:8px;">{ticker_html}</div>
              {f'<div style="color:#94a3b8;font-size:0.8rem;margin-top:8px;line-height:1.5;">{reason}</div>' if reason else ''}
            </div>
            <div style="text-align:right;min-width:120px;">
              {badge}
              <div style="margin-top:8px;">{impact_html}</div>
              <div style="color:#475569;font-size:0.7rem;margin-top:4px;">{news.get('pub_date','')[:10]}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        displayed += 1

    if displayed == 0:
        st.info("ไม่มีข่าวที่ตรงกับ filter ที่เลือก")

    # ── Summary Table ──────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-header">📑 ตารางสรุปผล</div>', unsafe_allow_html=True)

    table_rows = []
    for i, r in enumerate(results):
        affected_str = ", ".join(r.get("affected_tickers", [])) or "—"
        sent         = r.get("sentiment", "neutral")
        sent_icon    = "🟢" if sent == "bullish" else "🔴" if sent == "bearish" else "⚪"
        table_rows.append({
            "ข่าว":         r.get("title", news_list[i]["title"] if i < len(news_list) else "")[:60] + "...",
            "หุ้นที่กระทบ":  affected_str,
            "Sentiment":    f"{sent_icon} {sent.capitalize()}",
            "Impact %":     f"{r.get('impact_pct', 0):+.1f}%",
            "ความมั่นใจ":   f"{r.get('confidence', 0)}%",
        })

    if table_rows:
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

else:
    # Placeholder before analysis
    st.markdown("""
    <div style="background:#111827;border:1px solid rgba(255,255,255,0.07);border-radius:16px;
                padding:60px;text-align:center;">
      <div style="font-size:3rem;margin-bottom:16px;">📰</div>
      <div style="color:#94a3b8;font-size:1rem;margin-bottom:8px;">กด <strong style="color:#00D4FF;">วิเคราะห์ข่าว</strong> เพื่อให้ AI ประเมินผลกระทบต่อพอร์ตของคุณ</div>
      <div style="color:#475569;font-size:0.83rem;">AI จะดึงข่าวล่าสุดของหุ้นทุกตัวในพอร์ต แล้ววิเคราะห์ใน 1 request</div>
    </div>
    """, unsafe_allow_html=True)
