# 📈 AI Stock Decision Support System

> **DADS5001 — Final Project**  
> ระบบช่วยตัดสินใจลงทุนหุ้น ด้วย Technical Analysis + AI

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat&logo=mongodb&logoColor=white)](https://mongodb.com)
[![Snowflake](https://img.shields.io/badge/Snowflake-Cloud_DW-29B5E8?style=flat&logo=snowflake&logoColor=white)](https://snowflake.com)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3-F55036?style=flat)](https://groq.com)

---

## 🎯 Objective

พัฒนา Data Analytics Application ที่ช่วยให้ **นักลงทุนรายย่อย** สามารถวิเคราะห์หุ้นได้อย่างรวดเร็ว โดยรวม Technical Analysis และ AI Sentiment Analysis เข้าด้วยกัน เพื่อสรุปคำแนะนำ **Buy / Hold / Sell** 

**ปัญหาที่แก้:**
- ข้อมูลหุ้นกระจัดกระจายอยู่หลายแหล่ง
- นักลงทุนมือใหม่ไม่รู้วิธีที่จะอ่านค่า index ที่สำคัญยังไง
- ไม่มีเวลาติดตามข่าวตลาดทุกวัน

---

## 📋 Requirements

| Requirement | Implementation |
|---|---|
| Multi-page Streamlit App | 4 pages + Main page (app.py + pages/) |
| DuckDB + Pandas | `data_pipeline.py` — SQL summary บน DataFrame |
| External Cloud Storage | MongoDB Atlas (User Activity) + Snowflake (Analytics) |
| Non-AI vs AI Mode | Toggle บน Analysis page — unlock AI tabs เมื่อเปิด |
| Cache Data / Cache Resource / Session | `@st.cache_data`, `@st.cache_resource`, `st.session_state` |

---

## 🗺️ App Structure

```
📦 project/
├── app.py                    # Main page — Story, Flow, System Status
├── pages/
│   ├── 1_Market_Overview.py  # ภาพรวมตลาดโลก, VIX, YTD Chart
│   ├── 2_Stock_Selection.py  # เลือกหุ้น, Watchlist, Historical Data
│   ├── 3_Analysis.py         # Non-AI + AI Analysis (toggle)
│   └── 4_Dashboard.py        # Risk vs Return, Comparison, Sector Screening
└── src/
    ├── config.py             # Tickers, Sectors, Palette, Model config
    ├── data_pipeline.py      # yfinance fetch + DuckDB SQL summary
    ├── indicators.py         # RSI, MACD, MA, Bollinger Bands
    ├── ai_service.py         # Groq API — Sentiment + Sector Commentary
    └── storage.py            # MongoDB + Snowflake CRUD
```

---

## 🔄 Data Flow

```
Yahoo Finance (yfinance)
        │
        ▼
data_pipeline.py  ──→  DuckDB SQL Summary  ──→  Pandas DataFrame
        │
        ▼
indicators.py  ──→  RSI / MACD / MA / Bollinger Bands
        │
        ├── [Non-AI Mode] ──→  Technical Score  ──→  Buy / Hold / Sell
        │
        └── [AI Mode] ──→  Groq Llama 3.3  ──→  Sentiment Score
                                │
                                ▼
                    Combined Score (Tech 60% + AI 40%)
                                │
                                ▼
                    Investment Recommendation
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
        MongoDB Atlas                         Snowflake
    (Watchlist, History)         (Prices, Indicators, AI Results)
```

---

## 📄 Pages

### 🏠 Main (app.py)
- Disclaimer 
- System Status
- Tech Stack overview

### 🌍 1 — Market Overview
- ดัชนีหลัก: S&P 500, Nasdaq, Dow Jones, VIX
- YTD Performance Chart 

### 🎯 2 — Stock Selection
- เลือกหุ้นที่ต้องการดู
- Current Price
- Historical Data 

### 🔬 3 — Analysis (Non-AI + AI Mode)

- Technical Score 

**AI Mode :**
- 📰 **ข่าวตลาด** — ดึงข่าวจาก SPY/QQQ + AI สรุปข่าว
- 🤖 **AI Analysis**
- 🏭 **Sector Screening** — Scan Top 10 หุ้นในอุตสาหกรรมต่างๆ

### 📊 4 — Dashboard
- Risk vs Return
- Comparison Bar Chart
- Summary Decision Table 

---

## ⚙️ Setup

### 1. Clone & Install
```bash
git clone https://github.com/boomnuna/DADS5001.git
cd DADS5001
pip install -r requirements.txt
```

### 2. ตั้งค่า Secrets
สร้างไฟล์ `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "your_groq_api_key"

MONGO_URI = "mongodb+srv://user:password@cluster.mongodb.net/"
MONGO_DB  = "ai_stock_db"

[snowflake]
account   = "your_account"
user      = "your_user"
password  = "your_password"
warehouse = "your_warehouse"
database  = "your_database"
schema    = "your_schema"
```

### 3. Run
```bash
streamlit run app.py
```
---

## 🗄️ Database Schema

### MongoDB Collections
| Collection | Fields | ใช้ทำอะไร |
|---|---|---|
| `analysis_history` | user_id, tickers, results, analyzed_at | ประวัติการวิเคราะห์ |
| `search_history` | ประวัติการค้นหาหุ้น |
| `watchlists` | user_id, tickers, updated_at | เก็บหุ้นที่ user เลือก |

### Snowflake Tables
| Table | Key Columns | ใช้ทำอะไร |
|---|---|---|
| `technical_metrics` | ticker, metric_date, rsi, macd, ma20, ma50, technical_score | Technical Indicators รายวัน |
| `ai_sentiment` | ticker, sentiment_label, sentiment_score, combined_score | ผล AI วิเคราะห์ |
| `market_snapshots` | snapshot_date, sp500, nasdaq, vix, chg_pct | ภาพรวมตลาดรายวัน |

---

## 🛠️ Tech Stack

| Layer | Technology | ใช้ทำอะไร |
|---|---|---|
| **UI** | Streamlit (Multi-page) | Web App framework |
| **Data Source** | yfinance | ดึงราคาหุ้น Real-time จาก Yahoo Finance |
| **In-memory SQL** | DuckDB | SQL query บน Pandas DataFrame |
| **Data Processing** | Pandas, NumPy | Manipulation & Technical Indicator |
| **AI/LLM** | Groq API (Llama 3.3 70B) | Sentiment + ข่าวสรุป + Sector Commentary |
| **Visualization** | Plotly | Interactive Charts ทุกหน้า |
| **NoSQL DB** | MongoDB Atlas | Watchlist, Search History, Analysis History |
| **Cloud DW** | Snowflake | Technical Metrics, AI Sentiment, Market Snapshots |
| **Caching** | `@st.cache_data` / `@st.cache_resource` | ลด API calls |

---
