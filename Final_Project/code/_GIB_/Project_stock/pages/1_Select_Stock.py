import streamlit as st
from utils.data_loader import (
    load_stock_data,
    get_stock_snapshot
)

st.title("📈 Select Stocks")

st.write("Choose up to 3 stocks for analysis")

# --------------------
# Available Stocks
# --------------------

stock_options = [
    "NVDA",
    "GOOGL",
    "MSFT"
]

# --------------------
# Select Stocks
# --------------------

selected_stocks = st.multiselect(
    "Select Stocks",
    options=stock_options,
    default=["NVDA"]
)

# --------------------
# Validation
# --------------------

if len(selected_stocks) > 3:

    st.error("Maximum 3 stocks")

else:

    st.session_state["stocks"] = selected_stocks

    st.success("Stocks saved successfully")

# --------------------
# Display Selected Stocks
# --------------------

st.subheader("Selected Stocks")

if selected_stocks:

    for stock in selected_stocks:

        st.write(f"✅ {stock}")

else:

    st.warning("Please select at least one stock")


# ----------------------
# Stock Snapshot
# ----------------------

if selected_stocks:

    st.subheader("Stock Snapshot")

    for stock in selected_stocks:

        df = load_stock_data(stock)

        snapshot = get_stock_snapshot(df)

        st.markdown(f"### {stock}")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Current Price",
            snapshot["current_price"]
        )

        col2.metric(
            "1Y Return (%)",
            snapshot["return_pct"]
        )

        col3.metric(
            "Avg Volume",
            f"{snapshot['avg_volume']:,}"
        )

        st.divider()


        #------------------
        stocks = st.session_state.get("stocks", [])

if not stocks:

    st.warning(
        "Please select stocks first"
    )

    st.stop()

selected_stock = st.selectbox(
    "Choose Stock",
    stocks
)

df = load_stock_data(
    selected_stock
)

st.subheader(
    f"{selected_stock} Historical Data"
)

st.dataframe(
    df.head()
)

