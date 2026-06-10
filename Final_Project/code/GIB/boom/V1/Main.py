"""
Main.py — AI Stock Decision Support System
หน้าแรก: แนะนำ app และ flow การใช้งาน
"""

import streamlit as st
from src.storage import setup_snowflake_tables, mongo_status, snowflake_status

st.set_page_config(
    page_title="AI Stock Decision Support",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  .hero-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(90deg, #76b900, #00A4EF, #4285F4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
  }
  .hero-sub {
    color: #94a3b8;
    font-size: 1.05rem;
    margin-top: 8px;
  }
  .flow-card {
    background: #111827;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
    height: 100%;
  }
  .flow-icon { font-size: 2rem; margin-bottom: 8px; }
  .flow-title { font-weight: 600; color: #e2e8f0; font-size: 0.95rem; margin-bottom: 6px; }
  .flow-desc  { color: #64748b; font-size: 0.82rem; line-height: 1.5; }
  .status-row {
    background: #111827;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
  }
  .section-header {
    font-size: 0.7rem; font-weight: 600; color: #00D4FF;
    text-transform: uppercase; letter-spacing: 0.12em;
    margin: 24px 0 12px; border-bottom: 1px solid rgba(0,212,255,0.2);
    padding-bottom: 6px;
  }
  [data-testid="stSidebar"] { background: #0d1117 !important; }
</style>
""", unsafe_allow_html=True)

# Setup Snowflake tables on first load
setup_snowflake_tables()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">📈 AI Stock Decision<br>Support System</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">วิเคราะห์หุ้นด้วย Technical Analysis, Machine Learning และ AI — เพื่อช่วยตัดสินใจลงทุน</div>', unsafe_allow_html=True)
st.divider()

# ── Flow ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🗺️ วิธีใช้งาน</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    <div class="flow-card">
      <div class="flow-icon">1️⃣</div>
      <div class="flow-title">เลือกหุ้น</div>
      <div class="flow-desc">เลือกหุ้นสูงสุด 3 ตัวจากรายการ<br>ระบบบันทึก Watchlist ลง MongoDB</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class="flow-card">
      <div class="flow-icon">2️⃣</div>
      <div class="flow-title">วิเคราะห์</div>
      <div class="flow-desc">Non-AI: Technical + ML<br>AI mode: Groq วิเคราะห์ข่าว + แนะนำ Buy/Hold/Sell</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div class="flow-card">
      <div class="flow-icon">3️⃣</div>
      <div class="flow-title">Dashboard</div>
      <div class="flow-desc">เปรียบเทียบผลตอบแทน ความเสี่ยง<br>และ Scoreboard รวมทุกมิติ</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── System Status ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🔌 สถานะระบบ</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.markdown(f'<div class="status-row">{mongo_status()}<br><span style="color:#475569;font-size:0.75rem;">เก็บ Watchlist & Search History</span></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="status-row">{snowflake_status()}<br><span style="color:#475569;font-size:0.75rem;">เก็บ Price, Indicators, Predictions, AI Sentiment</span></div>', unsafe_allow_html=True)

st.divider()

# ── Tech Stack ────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🛠️ Tech Stack</div>', unsafe_allow_html=True)
stack = {
    "📊 Streamlit": "Multi-page Web App",
    "📈 yfinance":  "ดึงข้อมูลราคาหุ้นจริง",
    "🦆 DuckDB":    "SQL query บน DataFrame",
    "🐼 Pandas":    "Data manipulation",
    "🌿 MongoDB":   "Watchlist & Search History",
    "❄️ Snowflake": "Price, Indicators, Predictions",
    "🤖 Groq AI":   "LLM วิเคราะห์ข่าว + แนะนำ",
    "🌲 ML":        "Random Forest ทำนายทิศทางราคา",
}
cols = st.columns(4)
for i, (k, v) in enumerate(stack.items()):
    with cols[i % 4]:
        st.markdown(f"""
        <div style="background:#111827;border:1px solid rgba(255,255,255,0.06);
                    border-radius:10px;padding:12px;margin-bottom:8px;">
          <div style="font-weight:600;color:#e2e8f0;font-size:0.88rem;">{k}</div>
          <div style="color:#64748b;font-size:0.78rem;margin-top:3px;">{v}</div>
        </div>""", unsafe_allow_html=True)

st.caption("Educational demo only. This is not financial advice.")
