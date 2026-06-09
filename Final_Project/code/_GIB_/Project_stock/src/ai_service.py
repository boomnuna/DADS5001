from __future__ import annotations

import pandas as pd
import streamlit as st


NEWS = {
    "NVDA": [
        "NVIDIA demand remains supported by AI data center spending.",
        "Investors are watching supply constraints and margin pressure.",
    ],
    "GOOGL": [
        "Alphabet continues to expand cloud and AI search capabilities.",
        "Advertising growth is improving but regulatory pressure remains a risk.",
    ],
    "MSFT": [
        "Microsoft cloud revenue remains resilient with AI product integration.",
        "Enterprise software demand supports recurring revenue visibility.",
    ],
}


@st.cache_data(show_spinner=False)
def run_demo_ai_analysis(technical: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    merged = technical.merge(predictions, on="ticker", how="left")
    rows = []
    for row in merged.to_dict("records"):
        sentiment_score = _sentiment_score(row["ticker"])
        combined = (
            row["technical_score"] * 0.35
            + row["prediction_score"] * 0.35
            + sentiment_score * 0.30
        )
        recommendation = "Buy" if combined >= 68 else "Sell" if combined < 45 else "Hold"
        sentiment = "Positive" if sentiment_score >= 65 else "Negative" if sentiment_score < 45 else "Neutral"
        rows.append(
            {
                "ticker": row["ticker"],
                "news_headlines": NEWS.get(row["ticker"], ["No demo news available."]),
                "ai_summary": _summary(row["ticker"]),
                "sentiment_label": sentiment,
                "sentiment_score": sentiment_score,
                "impact_revenue": _impact_text(row["ticker"], "revenue"),
                "impact_profit": _impact_text(row["ticker"], "profit"),
                "impact_competition": _impact_text(row["ticker"], "competition"),
                "impact_growth": _impact_text(row["ticker"], "growth"),
                "combined_score": round(combined, 1),
                "recommendation": recommendation,
                "reason": _reason(row["technical_signal"], row["prediction_score"], sentiment),
            }
        )
    return pd.DataFrame(rows)


def _sentiment_score(ticker: str) -> int:
    return {"NVDA": 72, "GOOGL": 61, "MSFT": 68}.get(ticker, 55)


def _summary(ticker: str) -> str:
    summaries = {
        "NVDA": "AI infrastructure demand remains the main growth driver, but valuation and supply risk should be monitored.",
        "GOOGL": "Cloud and AI search support the growth story, while ads cyclicality and regulation create uncertainty.",
        "MSFT": "Cloud, enterprise software, and AI integration provide stable fundamentals with moderate upside.",
    }
    return summaries.get(ticker, "The latest news is mixed and should be combined with technical and ML signals.")


def _impact_text(ticker: str, dimension: str) -> str:
    table = {
        "revenue": "Likely supportive if product demand continues.",
        "profit": "Margin impact depends on infrastructure cost and pricing power.",
        "competition": "Competition is high, especially in AI and cloud markets.",
        "growth": "Medium to high growth potential, but market expectations are already elevated.",
    }
    return table[dimension]


def _reason(technical_signal: str, prediction_score: float, sentiment: str) -> str:
    return (
        f"Technical signal is {technical_signal}, ML up-probability is {prediction_score:.1f}%, "
        f"and news sentiment is {sentiment}."
    )

