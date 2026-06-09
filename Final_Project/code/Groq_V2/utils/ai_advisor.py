"""
utils/ai_advisor.py
Groq AI (default for testing) — วิเคราะห์หุ้น, สรุปข่าว, แนะนำการลงทุน
เปลี่ยนเป็น Gemini ได้ง่ายๆ โดยแก้ USE_GROQ = False
"""

import streamlit as st
from groq import Groq
from utils.db_mongo import save_ai_analysis, load_ai_analysis

# ── เปลี่ยน True/False เพื่อสลับ AI ─────────────────────────────────────────
USE_GROQ = True   # True = Groq | False = Gemini


def _call_ai(prompt: str, max_tokens: int = 1500) -> str:
    """เรียก AI ตาม USE_GROQ flag"""
    if USE_GROQ:
        model = _get_groq()
        if model is None:
            return "⚠️ กรุณาตั้งค่า GROQ_API_KEY ใน .streamlit/secrets.toml"
        response = model.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.4,
        )
        return response.choices[0].message.content
    else:
        import google.generativeai as genai
        model = _get_gemini()
        if model is None:
            return "⚠️ กรุณาตั้งค่า GEMINI_API_KEY ใน .streamlit/secrets.toml"
        response = model.generate_content(prompt)
        return response.text


@st.cache_resource
def _get_groq():
    """สร้าง Groq client (cache_resource)"""
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key or api_key == "YOUR_GROQ_API_KEY_HERE":
            return None
        return Groq(api_key=api_key)
    except Exception as e:
        st.error(f"Groq init error: {e}")
        return None


@st.cache_resource
def _get_gemini():
    """สร้าง Gemini model (cache_resource)"""
    try:
        import google.generativeai as genai
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            return None
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={"temperature": 0.4, "max_output_tokens": 1500},
        )
    except Exception as e:
        st.error(f"Gemini init error: {e}")
        return None


# ── ฟังก์ชันเดิมทั้งหมด (ไม่ต้องแก้อะไร) ─────────────────────────────────────

def analyze_stock_ai(symbol: str, stock_info: dict, news_list: list, technicals: dict) -> str:
    """วิเคราะห์หุ้นด้วย AI — ตรวจ MongoDB cache ก่อน"""
    cached = load_ai_analysis(symbol, max_age_hours=6)
    if cached:
        return cached.get("full_analysis", "")

    news_summary = "\n".join([
        f"- {n.get('content', {}).get('title', n.get('title', ''))}"
        for n in news_list[:5]
    ])

    prompt = f"""
คุณเป็น AI นักวิเคราะห์หุ้นมืออาชีพ วิเคราะห์หุ้น {symbol} โดยใช้ข้อมูลต่อไปนี้:

**ข้อมูลพื้นฐาน:**
- ราคาปัจจุบัน: ${stock_info.get('price', 'N/A')}
- เปลี่ยนแปลง: {stock_info.get('change_pct', 0):.2f}%
- P/E Ratio: {stock_info.get('pe_ratio', 'N/A')}
- Market Cap: ${stock_info.get('market_cap', 0):,.0f}
- Beta: {stock_info.get('beta', 'N/A')}
- Sector: {stock_info.get('sector', 'N/A')}
- Analyst Target Price: ${stock_info.get('target_mean', 'N/A')}
- Analyst Recommendation: {stock_info.get('recommendation', 'N/A')}

**Technical Indicators:**
- RSI (14): {technicals.get('rsi', 'N/A')}
- MACD Signal: {technicals.get('macd_signal', 'N/A')}
- ราคา vs MA50: {technicals.get('vs_ma50', 'N/A')}
- ราคา vs MA200: {technicals.get('vs_ma200', 'N/A')}

**ข่าวล่าสุด:**
{news_summary if news_summary else "ไม่มีข่าวล่าสุด"}

กรุณาวิเคราะห์และให้ข้อมูลในรูปแบบ:

## 📊 สรุปการวิเคราะห์
(สรุป 2-3 ประโยค)

## 🔍 จุดแข็ง
- (bullet points)

## ⚠️ ความเสี่ยง
- (bullet points)

## 🎯 เป้าหมายราคา & คำแนะนำ
(ราคาเป้าหมายระยะสั้น/กลาง และ คำแนะนำ ซื้อ/ถือ/ขาย พร้อมเหตุผล)

## 💡 กลยุทธ์การเทรด
(แนะนำจุดซื้อ, stop-loss, take profit)

**หมายเหตุ:** นี่คือการวิเคราะห์เพื่อการศึกษา ไม่ใช่คำแนะนำทางการเงิน
"""
    try:
        result = _call_ai(prompt, max_tokens=1500)
        save_ai_analysis(symbol, {
            "symbol": symbol,
            "full_analysis": result,
            "stock_info": stock_info,
        })
        return result
    except Exception as e:
        return f"❌ ไม่สามารถวิเคราะห์ได้: {e}"


def summarize_news_ai(symbol: str, news_list: list) -> str:
    """สรุปข่าวและ Sentiment ด้วย AI"""
    if not news_list:
        return "ไม่มีข่าวล่าสุด"

    headlines = "\n".join([
        f"{i+1}. {n.get('content', {}).get('title', n.get('title', ''))}"
        for i, n in enumerate(news_list[:8])
    ])

    prompt = f"""
วิเคราะห์ข่าวของหุ้น {symbol} ต่อไปนี้:

{headlines}

ตอบในรูปแบบ:
**Sentiment โดยรวม:** [Bullish 🟢 / Neutral 🟡 / Bearish 🔴] (คะแนน: X/10)

**ประเด็นสำคัญ:**
- (3-4 bullet points)

**ผลกระทบต่อราคา:** (1-2 ประโยค)
"""
    try:
        return _call_ai(prompt, max_tokens=800)
    except Exception as e:
        return f"❌ Error: {e}"


def predict_price_ai(symbol: str, current_price: float, technicals: dict) -> str:
    """พยากรณ์ราคาระยะสั้นด้วย AI"""
    prompt = f"""
ประเมินทิศทางราคาหุ้น {symbol} ในระยะสั้น (1-4 สัปดาห์) 
ราคาปัจจุบัน: ${current_price}

Technicals:
- RSI: {technicals.get('rsi', 'N/A')}
- MACD: {technicals.get('macd', 'N/A')} / Signal: {technicals.get('macd_signal_val', 'N/A')}
- อยู่เหนือ MA50: {technicals.get('above_ma50', 'N/A')}
- อยู่เหนือ MA200: {technicals.get('above_ma200', 'N/A')}
- Bollinger: ราคาอยู่ที่ {technicals.get('bb_position', 'N/A')}

ตอบสั้น ๆ:
📈 ทิศทาง: [ขึ้น/ลง/Sideway]
🎯 ช่วงราคาคาดการณ์: $X - $Y
⚡ ความมั่นใจ: X%
📝 เหตุผลหลัก: (2-3 ประโยค)
"""
    try:
        return _call_ai(prompt, max_tokens=500)
    except Exception as e:
        return f"❌ Error: {e}"
