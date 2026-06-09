import yfinance as yf

def load_stock_data(ticker):

    df = yf.download(
        ticker,
        start="2024-01-01",
        end="2024-12-31",
        progress=False
    )

    return df

def get_stock_snapshot(df):

    current_price = float(df["Close"].iloc[-1])

    first_price = float(df["Close"].iloc[0])

    return_pct = (
        (current_price - first_price)
        / first_price
    ) * 100

    avg_volume = int(df["Volume"].mean())

    return {
        "current_price": round(current_price, 2),
        "return_pct": round(return_pct, 2),
        "avg_volume": avg_volume
    }