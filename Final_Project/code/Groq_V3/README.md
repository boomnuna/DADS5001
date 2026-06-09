# 📈 TradeX — Trading Analytics App

> **DADS5001 Final Project** — AI-Powered Stock Investment Decision Support System

## 🎯 Overview

TradeX เป็น Streamlit app ที่ช่วยนักลงทุนตัดสินใจลงทุนในหุ้น US โดยใช้ข้อมูลจริงจาก Yahoo Finance
พร้อมระบบ AI (Google Gemini) สำหรับวิเคราะห์เชิงลึก

---

## 🛠️ Tech Stack

| Tool | การใช้งาน |
|------|-----------|
| **Streamlit** | Multi-page web app framework |
| **yfinance** | ดึงข้อมูลหุ้น US แบบ real-time (ฟรี) |
| **Pandas** | Data manipulation |
| **DuckDB** | In-memory SQL query บน DataFrame |
| **MongoDB Atlas** | เก็บ Portfolio, Trade History, AI Cache |
| **Snowflake** | เก็บ Portfolio Snapshots, Trade Log |
| **Plotly** | Interactive charts |
| **Google Gemini** | AI วิเคราะห์หุ้น, สรุปข่าว, พยากรณ์ราคา |

---

## 📋 Requirements

```
streamlit, yfinance, pandas, plotly, duckdb,
pymongo, snowflake-connector-python, google-generativeai, ta
```

---

## 🚀 Quick Start

### 1. Clone repo
```bash
git clone https://github.com/YOUR_GITHUB/tradex_app.git
cd tradex_app
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. ตั้งค่า Secrets
แก้ไขไฟล์ `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"   # จาก aistudio.google.com
MONGO_URI      = "mongodb+srv://..."      # MongoDB Atlas connection string
MONGO_DB       = "tradex_db"

[snowflake]
account   = "YOUR_ACCOUNT"
user      = "YOUR_USER"
password  = "YOUR_PASSWORD"
warehouse = "COMPUTE_WH"
database  = "TRADEX_DB"
schema    = "PUBLIC"
```

### 4. Run app
```bash
streamlit run Home.py
```

---

## 📱 หน้าต่างๆ ใน App

| หน้า | คำอธิบาย |
|------|-----------|
| 🏠 **Dashboard** | ภาพรวมพอร์ต, มูลค่า, Watchlist, Market Overview |
| 📊 **Stock Analysis** | กราฟราคา + Candlestick, Technical Indicators, Fundamentals, DuckDB SQL |
| 💼 **Portfolio** | จัดการพอร์ต, P&L, คำนวณภาษี WHT, Trade History (Snowflake) |
| 🤖 **AI Advisor** | **Non-AI Mode** (Rule-based) vs **AI Mode** (Gemini) |
| ⚗️ **Backtest** | ทดสอบ MA Crossover / RSI Strategy ย้อนหลัง |
| 🔀 **Compare** | เปรียบเทียบหุ้นหลายตัว, Radar Chart, Fundamentals Table |

---

## 🔑 วิธีสมัคร Google Gemini API (ฟรี)

1. ไปที่ [aistudio.google.com](https://aistudio.google.com)
2. Login ด้วย Google account
3. กด **"Get API Key"** → **"Create API key"**
4. Copy key ใส่ใน `secrets.toml`

**Free Tier:** 15 requests/นาที, 1,500 requests/วัน

---

## 📊 Features ที่ตอบโจทย์

- ✅ **Multi-pages** (Streamlit) — 6 หน้า
- ✅ **DuckDB + Pandas** — SQL query บน price data
- ✅ **MongoDB** — เก็บ Portfolio, Watchlist, AI Cache
- ✅ **Snowflake** — Portfolio Snapshots, Trade Log
- ✅ **Non-AI vs AI Mode** — toggle บนหน้า AI Advisor
- ✅ **Cache Data & Cache Resource & Session** — ทุกไฟล์

---

## 👥 Team
DADS5001 — Group Project
