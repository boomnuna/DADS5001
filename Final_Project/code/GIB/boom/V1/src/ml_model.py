"""
src/ml_model.py
ML Prediction: Random Forest Classifier
ทำนายทิศทางราคาวันถัดไป (Up / Down)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st


FEATURES = ["daily_return", "rsi", "macd", "macd_signal", "ma20", "ma50", "volume"]


@st.cache_data(ttl=3600, show_spinner=False)
def train_prediction_models(indicators: pd.DataFrame) -> pd.DataFrame:
    """Train Random Forest สำหรับแต่ละ ticker"""
    if indicators.empty:
        return pd.DataFrame()

    rows = []
    for ticker, group in indicators.sort_values("date").groupby("ticker"):
        df = group.copy()
        df["target_up"] = (df["close"].shift(-1) > df["close"]).astype(int)
        model_df = df.dropna(subset=FEATURES + ["target_up"])

        if len(model_df) < 40:
            probability  = _fallback_probability(df)
            accuracy     = None
            model_name   = "Heuristic (data too short)"
        else:
            probability, accuracy, model_name = _random_forest(model_df)

        rows.append({
            "ticker":            ticker,
            "probability_up":    round(float(probability), 3),
            "prediction_score":  round(float(probability) * 100, 1),
            "predicted_label":   "Up ▲" if probability >= 0.5 else "Down ▼",
            "model_name":        model_name,
            "backtest_accuracy": accuracy,
        })

    return pd.DataFrame(rows)


def _random_forest(model_df: pd.DataFrame) -> tuple[float, float | None, str]:
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score
    except ImportError:
        return _fallback_probability(model_df), None, "Heuristic (sklearn not installed)"

    split = max(int(len(model_df) * 0.75), 30)
    train  = model_df.iloc[:split]
    test   = model_df.iloc[split:-1]
    latest = model_df.iloc[[-1]]

    clf = RandomForestClassifier(n_estimators=150, max_depth=4, random_state=42)
    clf.fit(train[FEATURES], train["target_up"])

    probability = clf.predict_proba(latest[FEATURES])[0][1]
    accuracy    = (
        round(accuracy_score(test["target_up"], clf.predict(test[FEATURES])), 3)
        if len(test) > 0 else None
    )
    return probability, accuracy, "Random Forest"


def _fallback_probability(df: pd.DataFrame) -> float:
    last  = df.dropna(subset=["rsi", "macd", "macd_signal", "ma20", "ma50"]).iloc[-1]
    score = 0.50
    score += 0.08 if last["close"] > last["ma20"] else -0.04
    score += 0.08 if last["ma20"]  > last["ma50"] else -0.04
    score += 0.08 if last["macd"]  > last["macd_signal"] else -0.05
    score += 0.04 if 45 <= last["rsi"] <= 65 else -0.03
    return float(np.clip(score, 0.15, 0.85))
