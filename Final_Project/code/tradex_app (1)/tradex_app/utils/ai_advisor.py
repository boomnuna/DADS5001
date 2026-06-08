"""
utils/ai_advisor.py
Google Gemini AI — วิเคราะห์หุ้น, สรุปข่าว, แนะนำการลงทุน
"""

import streamlit as st
import google.generativeai as genai
from utils.db_mongo import save_ai_analysis, load_ai_analysis


@st.cache_resource
def get_gemini_model():
    """initialize Gemini model (cache_resource)"""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 1500,
            },
        )
        return model
    except Exception as e:
        st.error(f"Gemini init error: {e}")
        return None


def analyze_stock_ai(symbol: str, stock_info: dict, news_list: list, technicals: dict) -> str:
    """
    วิเคราะห์หุ้นด้วย AI
    ตรวจสอบ MongoDB cache ก่อน → ถ้าไม่มีค่อยเรียก Gemini
    """
    # ตรวจ cache ใน MongoDB
    cached = load_ai_analysis(symbol, max_age_hours=6)
    if cached:
        return cached.get("full_analysis", "")

    model = get_gemini_model()
    if model is None:
        return "⚠️ กรุณาตั้งค่า GEMINI_API_KEY ใน .streamlit/secrets.toml"

    # สรุปข่าวสั้น ๆ
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
        response = model.generate_content(prompt)
        result = response.text

        # เก็บใน MongoDB cache
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
    model = get_gemini_model()
    if model is None or not news_list:
        return "ไม่มีข่าวหรือยังไม่ได้ตั้งค่า API Key"

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
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Error: {e}"


def predict_price_ai(symbol: str, current_price: float, technicals: dict) -> str:
    """พยากรณ์ราคาระยะสั้นด้วย AI"""
    model = get_gemini_model()
    if model is None:
        return "ยังไม่ได้ตั้งค่า API Key"

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
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Error: {e}"
