import streamlit as st

from utils.data_loader import load_stock_data

st.title("📊 Non-AI Analysis")

stocks = st.session_state.get("stocks", [])

st.markdown("""
### 
- Technical indicators: MA20, MA50, RSI, MACD, Bollinger Band
- ML model: Random Forest เป็น baseline ที่อธิบายง่าย
- Output: probability up/down, prediction confidence, feature importance
- Visualization: price with indicators, confusion matrix/backtest summary


""")