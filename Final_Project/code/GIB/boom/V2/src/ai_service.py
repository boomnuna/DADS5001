"""
src/ai_service.py
AI Analysis ด้วย Groq (Llama 3.3) — วิเคราะห์หุ้น, สรุปข่าว, คำแนะนำ
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import yfinance as yf
from groq import Groq

from src.config import GROQ_MODEL


# ─── Groq Client ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_groq_client() -> Groq | None:
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key or api_key == "YOUR_GROQ_API_KEY":
            return None
        return Groq(api_key=api_key)
    except Exception as e:
        st.error(f"Groq init error: {e}")
        return None


def _call_groq(prompt: str, max_tokens: int = 1500) -> str:
    client = get_groq_client()
    if client is None:
        return "⚠️ กรุณาตั้งค่า GROQ_API_KEY ใน .streamlit/secrets.toml"
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"❌ Groq error: {e}"


# ─── ดึงข่าวจาก yfinance ──────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def get_news(ticker: str, limit: int = 5) -> list[str]:
    try:
        news = yf.Ticker(ticker).news or []
        headlines = []
        for item in news[:limit]:
            content = item.get("content", item)
            title   = content.get("title", item.get("title", ""))
            if title:
                headlines.append(title)
        return headlines
    except Exception:
        return []


# ─── AI Analysis ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def run_ai_analysis(
    technical:   pd.DataFrame,
    predictions: pd.DataFrame,
    tickers:     tuple[str, ...],
) -> pd.DataFrame:
    """
    วิเคราะห์หุ้นทุกตัวด้วย Groq AI
    คืนค่า DataFrame ที่มี: ticker, ai_summary, sentiment_label, sentiment_score,
    impact_*, recommendation, combined_score, reason, news_headlines
    """
    merged = technical.merge(predictions, on="ticker", how="left")
    rows   = []

    for row in merged.to_dict("records"):
        ticker    = row["ticker"]
        headlines = get_news(ticker)
        result    = _analyze_one(row, headlines)
        result["ticker"]          = ticker
        result["news_headlines"]  = headlines
        rows.append(result)

    return pd.DataFrame(rows)


def _analyze_one(row: dict, headlines: list[str]) -> dict:
    """เรียก Groq วิเคราะห์หุ้น 1 ตัว"""
    news_text = "\n".join([f"- {h}" for h in headlines]) if headlines else "- ไม่มีข่าวล่าสุด"

    prompt = f"""
คุณเป็น AI นักวิเคราะห์หุ้นมืออาชีพ วิเคราะห์หุ้น {row['ticker']} โดยใช้ข้อมูลต่อไปนี้:

**Technical Analysis:**
- RSI: {row.get('rsi', 'N/A')} (Score: {row.get('rsi_score', 'N/A')}/100)
- MACD Score: {row.get('macd_score', 'N/A')}/100
- MA Score: {row.get('ma_score', 'N/A')}/100
- Technical Signal: {row.get('technical_signal', 'N/A')}
- Technical Score: {row.get('technical_score', 'N/A')}/100

**ML Prediction:**
- โอกาสราคาขึ้น: {row.get('prediction_score', 'N/A')}%
- คาดการณ์: {row.get('predicted_label', 'N/A')}
- Model: {row.get('model_name', 'N/A')}

**ข่าวล่าสุด:**
{news_text}

ตอบในรูปแบบ JSON เท่านั้น ไม่มี markdown หรือ backticks:
{{
  "ai_summary": "สรุปภาพรวมการวิเคราะห์ 3-4 ประโยค ภาษาไทย",
  "sentiment_label": "Positive หรือ Neutral หรือ Negative",
  "sentiment_score": <ตัวเลข 0-100>,
  "impact_revenue": "ผลกระทบต่อรายได้ 1-2 ประโยค",
  "impact_profit": "ผลกระทบต่อกำไร 1-2 ประโยค",
  "impact_competition": "ผลกระทบด้านการแข่งขัน 1-2 ประโยค",
  "impact_growth": "แนวโน้มการเติบโต 1-2 ประโยค",
  "recommendation": "Buy หรือ Hold หรือ Sell",
  "reason": "เหตุผลสั้น 1-2 ประโยค"
}}
"""

    raw = _call_groq(prompt, max_tokens=1000)

    # Parse JSON
    try:
        # clean markdown fences if any
        text = raw.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
    except Exception:
        result = {
            "ai_summary":          raw[:300] if len(raw) > 10 else "ไม่สามารถวิเคราะห์ได้",
            "sentiment_label":     "Neutral",
            "sentiment_score":     50,
            "impact_revenue":      "N/A",
            "impact_profit":       "N/A",
            "impact_competition":  "N/A",
            "impact_growth":       "N/A",
            "recommendation":      "Hold",
            "reason":              "ไม่สามารถ parse ผลลัพธ์ได้",
        }

    # Combined score
    tech_score = row.get("technical_score", 50)
    pred_score = row.get("prediction_score", 50)
    sent_score = result.get("sentiment_score", 50)
    result["combined_score"] = round(tech_score * 0.35 + pred_score * 0.35 + sent_score * 0.30, 1)

    return result


# ─── Sector Screening ─────────────────────────────────────────────────────────

SECTORS = {
    "Technology": ["NVDA", "MSFT", "AAPL", "META", "GOOGL"],
    "E-Commerce / Cloud": ["AMZN", "GOOGL"],
    "EV / Clean Energy": ["TSLA"],
}

@st.cache_data(ttl=1800, show_spinner=False)
def screen_sector(sector: str) -> pd.DataFrame:
    """
    ดึงข้อมูลหุ้นในอุตสาหกรรมที่เลือก
    คืนค่า DataFrame พร้อม return, technical signal, pattern score
    """
    from src.data_pipeline import load_prices, duckdb_price_summary
    from src.indicators import add_technical_indicators, latest_technical_scores
    from src.ml_model import train_prediction_models

    tickers = SECTORS.get(sector, [])
    if not tickers:
        return pd.DataFrame()

    prices     = load_prices(tuple(tickers))
    summary    = duckdb_price_summary(prices)
    indicators = add_technical_indicators(prices)
    technical  = latest_technical_scores(indicators)
    patterns   = train_prediction_models(indicators)

    merged = (
        summary[["ticker","latest_close","return_1m","return_3m","volatility"]]
        .merge(technical[["ticker","technical_score","technical_signal","rsi"]], on="ticker")
        .merge(patterns[["ticker","pattern_score","pattern_label"]], on="ticker")
    )

    # Momentum score = รวม return + technical + pattern
    merged["momentum_score"] = (
        merged["return_1m"].clip(-20,20) / 20 * 30 +
        merged["technical_score"] / 100 * 40 +
        merged["pattern_score"] / 100 * 30
    ).round(1)

    return merged.sort_values("momentum_score", ascending=False)


@st.cache_data(ttl=3600, show_spinner=False)
def ai_sector_commentary(sector: str, screening_df: pd.DataFrame) -> str:
    """AI สรุปภาพรวม sector และหุ้นที่น่าสนใจ"""
    if screening_df.empty:
        return "ไม่มีข้อมูล"

    rows_text = "\n".join([
        f"- {r['ticker']}: Return 1M {r['return_1m']:+.1f}%, "
        f"Technical {r['technical_score']:.0f}/100, "
        f"Pattern {r['pattern_score']:.0f}/100, "
        f"Signal: {r['technical_signal']}"
        for _, r in screening_df.iterrows()
    ])

    prompt = f"""
คุณเป็น AI นักวิเคราะห์หุ้นมืออาชีพ วิเคราะห์หุ้นใน sector {sector} ต่อไปนี้:

{rows_text}

สรุปในรูปแบบ:

## 🏭 ภาพรวม {sector} Sector
(2-3 ประโยค สรุปภาพรวม)

## 🚀 หุ้นที่กำลังมาแรง
- (ระบุชื่อหุ้นและเหตุผลสั้นๆ)

## ⚠️ หุ้นที่ควรระวัง
- (ระบุชื่อหุ้นและเหตุผลสั้นๆ)

## 💡 สรุปคำแนะนำ
(1-2 ประโยค)

ตอบภาษาไทย กระชับ อ่านง่าย
"""
    return _call_groq(prompt, max_tokens=800)
