import streamlit as st

st.set_page_config(
    page_title="AI Stock Analyzer",
    page_icon="📈",
    layout="wide"
)

st.title("📈 AI Stock Decision Support")

st.markdown("""
### Welcome

This project helps investors analyze stocks using:

- Technical Analysis
- Machine Learning Prediction
- AI News Analysis
- Analytics Dashboard

Please select a page from the sidebar.
            

MongoDB ใช้เก็บข้อมูลผู้ใช้งาน (Watchlist, Search History) เพราะเป็นข้อมูลแบบ Semi-Structured 
ที่เปลี่ยนแปลงได้บ่อยและมีความยืดหยุ่นสูง (user แต่ละคนอาจมีจำนวนหุ้นที่สนใจไม่เทากัน)

ส่วน Snowflake ใช้เก็บข้อมูลวิเคราะห์หุ้น (Stock Price, Prediction, Sentiment)
เพื่อรองรับการวิเคราะห์และ Dashboard.
            
flow connect
ีuser - select id - load stock - select stock - save watchlist (mongodb) - read watchlist(ticker) - query ticker for analytic
เชื่อม MongoDB กับ Snowflake ผ่าน Watchlist ของuser โดย MongoDB ทำหน้าที่เก็บว่าผู้ใช้สนใจหุ้นตัวไหน
ส่วน Non-AI, AI และ Dashboard จะอ่าน Watchlist จาก MongoDB แล้วนำ Ticker ไป Query 
ข้อมูลวิเคราะห์จาก Snowflake
""")