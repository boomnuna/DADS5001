# AI Stock Decision Support System

Data-centric Streamlit app for stock decision support using:

- Non-AI analytics: technical indicators and baseline ML prediction
- AI add-on: news summary, sentiment, impact analysis, and recommendation
- Pandas + DuckDB for data processing
- MongoDB for user-level data
- Snowflake for analytical tables and model outputs

Default demo stocks:

- NVDA
- GOOGL
- MSFT

Demo data window:

- 2025-01-02 to 2025-06-30

The demo uses deterministic generated market data so the classroom presentation is stable and does not depend on live APIs.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Pages

1. Stock Selection
2. Non-AI Analysis
3. AI Analysis
4. Stock Analytics Dashboard

## Demo Mode

The app works without MongoDB, Snowflake, or AI API keys.

In demo mode:

- MongoDB writes are replaced by Streamlit session state.
- Snowflake tables are represented as Pandas DataFrames.
- AI analysis is deterministic and based on prepared demo headlines.

## Important Note

This project is for educational decision support only. It is not financial advice.

