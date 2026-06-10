import streamlit as st

from src.ai_service import run_demo_ai_analysis
from src.config import APP_TITLE, DEFAULT_TICKERS
from src.data_pipeline import load_demo_prices
from src.indicators import add_technical_indicators, latest_technical_scores
from src.ml_model import train_prediction_models
from src.ui import disclaimer, setup_page

setup_page(f"{APP_TITLE} - AI Analysis")

tickers = st.session_state.get("selected_tickers", DEFAULT_TICKERS)
st.title("AI Analysis")
st.caption("Demo AI mode: news summary, sentiment, business impact, and recommendation.")

prices = load_demo_prices(tuple(tickers))
indicators = add_technical_indicators(prices)
technical = latest_technical_scores(indicators)
predictions = train_prediction_models(indicators)
ai_result = run_demo_ai_analysis(technical, predictions)

st.info(
    "This page uses deterministic demo AI for classroom reliability. "
    "A real provider such as OpenAI or Gemini can replace this layer after API keys are ready."
)

for row in ai_result.to_dict("records"):
    with st.expander(f"{row['ticker']} - {row['recommendation']} ({row['combined_score']})", expanded=True):
        st.write(row["ai_summary"])
        st.markdown("**News used in demo**")
        for headline in row["news_headlines"]:
            st.write(f"- {headline}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Sentiment", row["sentiment_label"], row["sentiment_score"])
        col2.metric("Combined score", row["combined_score"])
        col3.metric("Recommendation", row["recommendation"])

        st.markdown("**Impact analysis**")
        st.write(f"- Revenue: {row['impact_revenue']}")
        st.write(f"- Profit: {row['impact_profit']}")
        st.write(f"- Competition: {row['impact_competition']}")
        st.write(f"- Future growth: {row['impact_growth']}")
        st.caption(row["reason"])

st.subheader("AI call design")
st.markdown(
    """
    In the final version, the app can send only compact inputs to the AI:
    ticker, 3-5 news headlines, technical signal, ML probability, and sentiment task instructions.
    It should not send the full historical price table. This keeps cost and token usage low.
    """
)

disclaimer()

