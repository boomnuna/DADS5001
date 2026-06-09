import plotly.graph_objects as go
import streamlit as st

from src.config import APP_TITLE, DEFAULT_TICKERS, PALETTE
from src.data_pipeline import load_demo_prices
from src.indicators import add_technical_indicators, latest_technical_scores
from src.ml_model import train_prediction_models
from src.ui import disclaimer, setup_page

setup_page(f"{APP_TITLE} - Non-AI Analysis")

tickers = st.session_state.get("selected_tickers", DEFAULT_TICKERS)
st.title("Non-AI Analysis")
st.caption("Technical indicators and baseline machine learning prediction.")

prices = load_demo_prices(tuple(tickers))
indicators = add_technical_indicators(prices)
technical = latest_technical_scores(indicators)
predictions = train_prediction_models(indicators)
result = technical.merge(predictions, on="ticker", how="left")

st.subheader("Technical + ML score")
st.dataframe(result, use_container_width=True)

st.subheader("Price with MA20 and MA50")
for ticker in tickers:
    df = indicators[indicators["ticker"] == ticker]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["close"], name="Close", line=dict(color=PALETTE[ticker])))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma20"], name="MA20", line=dict(color="#888", dash="dot")))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma50"], name="MA50", line=dict(color="#444", dash="dash")))
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20), title=ticker)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("How to explain this page")
st.markdown(
    """
    - **Technical score** combines RSI, MACD, and moving-average trend.
    - **ML prediction** uses a Random Forest classifier when scikit-learn is available.
    - The target is next-business-day direction: Up or Down.
    - This is a baseline model for decision support, not a guarantee.
    """
)

disclaimer()

