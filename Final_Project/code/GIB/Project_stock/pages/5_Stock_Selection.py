import streamlit as st

from src.config import APP_TITLE, DEFAULT_TICKERS, SUPPORTED_TICKERS
from src.data_pipeline import duckdb_price_summary, load_demo_prices
from src.storage import save_watchlist_to_mongo, snowflake_status
from src.ui import disclaimer, setup_page

setup_page(f"{APP_TITLE} - Stock Selection")

st.title("Stock Selection")
st.caption("Choose the stocks for the full analysis flow. The class demo uses NVDA, GOOGL, and MSFT.")

selected = st.multiselect(
    "Stocks",
    options=SUPPORTED_TICKERS,
    default=st.session_state.get("selected_tickers", DEFAULT_TICKERS),
    max_selections=3,
)
if not selected:
    selected = DEFAULT_TICKERS.copy()

mode = st.radio("Analysis mode", ["Non-AI mode", "AI mode"], horizontal=True, index=1)
st.session_state.selected_tickers = selected
st.session_state.analysis_mode = mode

prices = load_demo_prices(tuple(selected))
summary = duckdb_price_summary(prices)

cols = st.columns(len(summary))
for col, row in zip(cols, summary.to_dict("records")):
    col.metric(
        row["ticker"],
        f"${row['latest_close']:.2f}",
        f"{row['return_1m']:.2f}% 1M",
    )
    col.caption(f"Volatility {row['volatility']:.1f}% | Volume {row['latest_volume']:,.0f}")

st.subheader("Data connection status")
left, right = st.columns(2)
with left:
    if st.button("Save watchlist to MongoDB"):
        st.info(save_watchlist_to_mongo(selected))
with right:
    st.info(snowflake_status())

st.subheader("DuckDB summary table")
st.dataframe(summary, use_container_width=True)

disclaimer()

