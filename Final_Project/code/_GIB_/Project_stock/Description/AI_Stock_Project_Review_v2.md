# AI Stock Decision Support System - Review v2

วันที่จัดทำ: 2026-06-08

เอกสารนี้เป็นเวอร์ชันเสนอปรับปรุงต่อจากไฟล์เดิม โดยไม่ลบหรือแก้ทับเอกสารต้นฉบับ

## 1. สรุปโจทย์รายวิชา

โปรเจคต้องเป็น Data-centric app ที่มี AI add-on และควรส่งเป็น GitHub repository พร้อม demo/presentation

Requirement หลักจาก `Final project DADS5001.docx`

- Streamlit แบบ Multi-pages
- ใช้ DuckDB และ Pandas
- ใช้ external data storage บน Cloud: MongoDB และ Snowflake
- มี 2 modes: Non-AI mode และ AI mode
- ใช้ `st.cache_data`, `st.cache_resource` และ `st.session_state`
- มี Visualization ด้วย Streamlit, Plotly หรือเครื่องมือที่เหมาะสม
- Presentation ต้องอธิบาย Issues/Motivation, Objective, Methodology, Non-AI, AI integration, Visualization และ Demo video

## 2. ความเข้าใจโปรเจคปัจจุบัน

หัวข้อ `AI Stock Decision Support System` เหมาะกับโจทย์ เพราะเป็นระบบช่วยตัดสินใจจากข้อมูลหุ้น โดยแบ่งชัดเจนเป็น

- Non-AI: Technical indicators, statistical analytics, ML prediction
- AI add-on: News summary, sentiment analysis, impact analysis, recommendation
- Dashboard: เปรียบเทียบหุ้นหลายตัวจาก return, risk, prediction และ sentiment

ขอบเขตที่เหมาะสมสำหรับงานส่งคือระบบสนับสนุนการตัดสินใจเชิงการศึกษา ไม่ใช่ระบบให้คำแนะนำการลงทุนจริง ควรแสดง disclaimer ทุกหน้าที่มี recommendation

## 3. Requirement Mapping

| Requirement | สิ่งที่มีในไอเดียปัจจุบัน | ข้อเสนอให้ชัดขึ้น |
|---|---|---|
| Multi-pages Streamlit | มีร่าง 4 หน้า | ทำเป็น `app.py` + folder `pages/` หรือใช้ Streamlit navigation |
| DuckDB + Pandas | ระบุไว้ใน stack | ใช้ DuckDB query ข้อมูลราคาหลังจากโหลดด้วย Pandas |
| MongoDB | เก็บ watchlist และ search history | เพิ่ม collection schema และหน้า history/watchlist |
| Snowflake | เก็บ stock price, model output, sentiment | กำหนด table schema และ pipeline load |
| Non-AI mode | Technical + ML | ทำ toggle mode และให้หน้า Non-AI ทำงานได้แม้ไม่มี API key |
| AI mode | News + sentiment + recommendation | ทำ fallback mock/demo mode หากไม่มี key |
| Cache/session | ยังเป็นระดับไอเดีย | ใส่ให้ชัดว่า cache data/API, cache DB connections, session watchlist |
| Visualization | มี dashboard mock หน้า 4 | ใช้ mock เป็นต้นแบบ แต่เชื่อมข้อมูลจริง/จำลองจาก pipeline |

## 4. Architecture v2

Flow ที่เสนอ:

1. User เลือกหุ้นได้สูงสุด 3 ตัว
2. Streamlit เก็บ selection ใน `st.session_state`
3. โหลดข้อมูลราคาจาก Yahoo Finance หรือ mock CSV ใน demo mode
4. Pandas ทำ cleaning และ feature engineering
5. DuckDB query/aggregate ราคาหุ้นและ metrics
6. MongoDB เก็บ watchlist/search history
7. Snowflake เก็บ historical price, technical metrics, prediction, sentiment result
8. Non-AI engine คำนวณ technical indicators และ ML prediction
9. AI engine ดึงข่าว สรุป sentiment และ impact
10. Dashboard รวมคะแนนเพื่อแนะนำ Buy/Hold/Sell แบบมีเหตุผลประกอบ

## 5. Page Design v2

### Page 1: Stock Selection

หน้าสำหรับเลือกหุ้นและตั้งค่า analysis mode

- Inputs: ticker สูงสุด 3 ตัว, lookback period, analysis mode
- Outputs: current price, 1M return, volume, volatility, watchlist status
- Data actions: save watchlist ลง MongoDB, cache price data

### Page 2: Non-AI Analysis

หน้าวิเคราะห์เชิงสถิติและ ML

- Technical indicators: MA20, MA50, RSI, MACD, Bollinger Band
- ML model: Random Forest เป็น baseline ที่อธิบายง่าย
- Output: probability up/down, prediction confidence, feature importance
- Visualization: price with indicators, confusion matrix/backtest summary

### Page 3: AI Analysis

หน้า AI add-on

- News retrieval จาก News API หรือ fallback sample news
- LLM สรุปข่าวเป็น bullet สั้น
- Sentiment: Positive/Neutral/Negative พร้อม score
- Impact: revenue, profit, competition, future growth
- Recommendation: Buy/Hold/Sell โดยรวม technical + ML + sentiment

### Page 4: Stock Analytics Dashboard

ใช้ `Dashboard_mock/stock_dashboard_v2.py` เป็นฐานออกแบบได้ดี เพราะมี chart ครบและโทน dashboard ดูจริงจัง

ควรปรับเพิ่ม:

- เปลี่ยน simulated data ให้รับผลจาก pipeline กลาง
- เพิ่มแถบ final ranking เช่น `Best risk-adjusted`, `Best momentum`, `Highest AI sentiment`
- เพิ่ม note ว่าเป็น educational decision support และไม่ใช่ financial advice
- แก้ encoding ตัวอักษรพิเศษในไฟล์ Python/HTML ที่ตอนนี้แสดงเป็น mojibake เช่น `â—ˆ`, `Â·`, `Ïƒ`

## 6. Data Schema ที่เสนอ

MongoDB collections:

```json
{
  "watchlists": {
    "user_id": "demo_user",
    "tickers": ["NVDA", "AAPL", "MSFT"],
    "updated_at": "2026-06-08T00:00:00Z"
  },
  "search_history": {
    "user_id": "demo_user",
    "ticker": "NVDA",
    "searched_at": "2026-06-08T00:00:00Z"
  }
}
```

Snowflake tables:

- `STOCK_PRICES`: date, ticker, open, high, low, close, volume
- `TECHNICAL_METRICS`: date, ticker, ma20, ma50, rsi, macd, bollinger_upper, bollinger_lower
- `ML_PREDICTIONS`: run_id, run_at, ticker, probability_up, predicted_label, model_name
- `AI_SENTIMENT`: run_id, run_at, ticker, sentiment_label, sentiment_score, summary, recommendation

## 7. Methodology ที่ใช้ใน Presentation

Non-AI methodology:

- Collect historical stock prices
- Clean and transform with Pandas
- Query/aggregate with DuckDB
- Calculate technical indicators
- Train baseline ML classifier to predict next-day or next-period direction
- Evaluate with accuracy, precision/recall, confusion matrix

AI methodology:

- Retrieve latest news for selected tickers
- Summarize news with LLM
- Extract sentiment and business impact
- Combine technical score, ML probability and sentiment score
- Generate recommendation with explanation

## 8. สิ่งที่ควรระวัง

- ข้อมูลหุ้นและข่าวเปลี่ยนตลอด ควรมี demo/mock mode เพื่อให้ presentation ไม่พังถ้า API ล่ม
- หลีกเลี่ยงคำว่า investment advice แบบจริงจัง ให้ใช้ decision support / educational purpose
- ถ้าใช้ OpenAI/Gemini ควรเก็บ API key ใน Streamlit secrets หรือ `.env` และไม่ commit key
- ML prediction ไม่ควร claim ว่าแม่นยำ ควรอธิบายว่าเป็น baseline model สำหรับประกอบการวิเคราะห์
- Dashboard หน้า 4 ตอนนี้ดีมากสำหรับ mock แต่ต้องเชื่อมกับ state จากหน้า 1 และผลจากหน้า 2/3

## 9. Build Plan ที่แนะนำ

1. สร้างโครง Streamlit multipage
2. ทำ data loader + cache + demo fallback
3. ทำ DuckDB analytics layer
4. ทำ MongoDB watchlist/history
5. ทำ Snowflake connector และ schema scripts
6. ทำ Non-AI technical indicators
7. ทำ ML baseline prediction
8. ทำ AI news/sentiment/recommendation
9. นำ dashboard mock หน้า 4 มาเชื่อมข้อมูลจริง
10. เพิ่ม README, requirements, `.env.example`, demo video checklist

## 10. คำถามที่ควรตัดสินใจต่อ

- จะใช้หุ้นตลาด US เท่านั้นก่อนหรือรองรับ SET ด้วย
- Demo จะใช้ข้อมูลสดจาก Yahoo Finance หรือเตรียม sample data ไว้กัน API ล่ม
- AI provider จะใช้ OpenAI, Gemini หรือทำเป็น provider-agnostic
- Snowflake/MongoDB จะใช้ cloud จริงใน presentation หรือใช้ connection optional พร้อม mock fallback
- ML target จะทำนาย next-day direction หรือ next-week direction

