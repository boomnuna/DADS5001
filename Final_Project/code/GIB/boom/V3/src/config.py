"""
src/config.py — App configuration
"""

APP_TITLE        = "AI Stock Decision Support System"
DEFAULT_TICKERS  = ["NVDA", "GOOGL", "MSFT"]
SUPPORTED_TICKERS = ["NVDA", "GOOGL", "MSFT", "AAPL", "AMZN", "META", "TSLA"]
USER_ID          = "demo_user"

# ช่วงเวลาข้อมูลหุ้น
PRICE_PERIOD = "1y"   # yfinance period string

# Groq model
GROQ_MODEL = "llama-3.3-70b-versatile"

# สี palette ต่อหุ้น
PALETTE = {
    "NVDA":  "#76b900",
    "GOOGL": "#4285F4",
    "MSFT":  "#00A4EF",
    "AAPL":  "#A2AAAD",
    "AMZN":  "#FF9900",
    "META":  "#0866FF",
    "TSLA":  "#E31937",
}

DEFAULT_PALETTE_COLOR = "#888888"

# Sector groupings สำหรับ Sector Screening
SECTORS = {
    "Technology": ["NVDA", "MSFT", "AAPL", "META", "GOOGL"],
    "E-Commerce / Cloud": ["AMZN", "GOOGL", "MSFT"],
    "EV / Consumer": ["TSLA", "AAPL", "AMZN"],
}
