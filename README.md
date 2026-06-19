# 📈 AI Stock Decision Support System

> **DADS5001 Final Project** — AI-powered stock analysis tool for retail investors  
> Built with Streamlit, DuckDB, Pandas, MongoDB, Snowflake, and Groq AI

---

## 🎯 Objective

ระบบช่วยสนับสนุนการตัดสินใจลงทุนสำหรับนักลงทุนรายย่อย โดยใช้เครื่องมือด้าน Data Analytics และ Data Science เพื่อ:

- วิเคราะห์หุ้นด้วย Technical Indicators (RSI, MACD, Moving Average)
- วิเคราะห์ sentiment จากข่าวล่าสุดด้วย AI (Groq Llama 3.3)
- สรุปคำแนะนำ **Buy / Hold / Sell** พร้อม Confidence Score
- แสดงภาพรวมตลาดและ sector screening แบบ real-time

---

## ❗ Issues & Motivation

นักลงทุนรายย่อยมักเผชิญปัญหาเหล่านี้:

| ปัญหา | รายละเอียด |
|---|---|
| 📰 ข้อมูลกระจัดกระจาย | ต้องเปิดหลาย website เพื่อดูข่าว ราคา และ indicators |
| 🤯 วิเคราะห์เองไม่เป็น | ไม่รู้ว่า RSI, MACD หมายความว่าอะไร |
| ⏰ ไม่มีเวลาติดตาม | ตลาดเปลี่ยนเร็ว กว่าจะรู้ข่าวก็สายไปแล้ว |

App นี้รวมทุกอย่างไว้ในที่เดียว และให้ AI ช่วยสรุปให้อ่านง่าย

---

## 🗺️ App Structure (Multi-page Streamlit)

```
Main.py                  ← Hero page + System Status + Tech Stack
pages/
├── 1_Market_Overview.py ← S&P500, Nasdaq, Dow Jones, VIX + YTD Chart
├── 2_Analysis.py        ← Technical Analysis + AI Analysis + Sector Screening
├── 3_Stock_Selection.py ← เลือกหุ้น + DuckDB Summary + Price Chart
└── 4_Dashboard.py       ← Best Picks + Scoreboard + Risk vs Return
```

---

## 🔧 Solution (Methodology)

### Non-AI Mode — Technical Analysis

คำแนะนำมาจาก Technical Indicators ล้วนๆ ไม่ใช้ AI:

```
Tech Score = mean(RSI Score + MACD Score + MA Score)

RSI Score  : RSI 45-65 = 70 / 35-45 หรือ 65-75 = 55 / อื่นๆ = 35
MACD Score : MACD > Signal line = 70 / MACD < Signal line = 35
MA Score   : ราคา > MA20 > MA50 = 75 / อื่นๆ = 45

Buy  : Tech Score ≥ 65
Hold : Tech Score 45-64
Sell : Tech Score < 45
```

### AI Mode — Combined Analysis

รวม Technical กับ AI Sentiment จากข่าวล่าสุด:

```
Combined Score = Technical Score (60%) + AI Sentiment Score (40%)

Buy  : Combined Score ≥ 68
Hold : Combined Score 45-67
Sell : Combined Score < 45
```

AI ใช้ **Groq (Llama 3.3-70B)** วิเคราะห์ข่าวจาก Yahoo Finance แล้วให้ Sentiment Score 0-100

---

## 🛠️ Tech Stack & Requirements

| Tool | หน้าที่ | Requirement |
|---|---|---|
| **Streamlit** | Multi-page Web App | ✅ Multi-pages |
| **DuckDB** | In-memory SQL query บน DataFrame | ✅ DuckDB |
| **Pandas** | Data manipulation & processing | ✅ Pandas |
| **MongoDB Atlas** | เก็บ Watchlist, Analysis History | ✅ Cloud Storage |
| **Snowflake** | เก็บ Technical Metrics, AI Sentiment | ✅ Cloud Storage |
| **yfinance** | ดึงราคาหุ้นและข่าว Real-time | - |
| **Groq AI** | LLM วิเคราะห์ sentiment ข่าว | ✅ AI Mode |
| **Plotly** | Interactive charts | ✅ Visualization |

### Streamlit Caching

```python
@st.cache_data(ttl=900)      # cache ข้อมูลราคาหุ้น 15 นาที
@st.cache_resource            # cache MongoDB/Snowflake/Groq connection
st.session_state              # จำหุ้นที่เลือกและผล AI ข้ามหน้า
```

---

## 📊 Database Design

**MongoDB — SMART_INVEST**
| Collection | เก็บอะไร |
|---|---|
| `watchlists` | หุ้นที่ผู้ใช้เลือกไว้ |
| `analysis_history` | ประวัติผล AI วิเคราะห์ |
| `search_history` | ประวัติการค้นหาหุ้น |

**Snowflake — SMART_INVEST.PUBLIC**
| Table | เก็บอะไร |
|---|---|
| `market_snapshots` | ดัชนีตลาดรายวัน (S&P500, Nasdaq, Dow, VIX) |
| `technical_metrics` | RSI, MA, MACD Score |
| `ai_sentiment` | Sentiment Score, Combined Score, Recommendation |

---

## 🚀 Installation & Setup

### 1. Clone repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup secrets

สร้างไฟล์ `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "your_groq_api_key"
MONGO_URI    = "your_mongodb_uri"
MONGO_DB     = "SMART_INVEST"

[snowflake]
account   = "your_account"
user      = "your_username"
password  = "your_password"
warehouse = "COMPUTE_WH"
database  = "SMART_INVEST"
schema    = "PUBLIC"
```

### 4. Run app

```bash
streamlit run Main.py
```

---

## 📦 Requirements

```
streamlit
yfinance
duckdb
pandas
numpy
plotly
pymongo
snowflake-connector-python
groq
```

---

## ⚠️ Disclaimer

App นี้เป็น **เครื่องมือช่วยตัดสินใจเพื่อการศึกษา** เท่านั้น  
ไม่ใช่คำแนะนำทางการเงิน การลงทุนมีความเสี่ยง ผู้ลงทุนควรศึกษาข้อมูลเพิ่มเติมและตัดสินใจด้วยตนเอง

---

## 👥 Team

DADS5001 — Data Analytics and Data Science  
Faculty of Information Technology, [University Name]
