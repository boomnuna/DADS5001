"""
STEP 2: Streamlit Dashboard
รันด้วยคำสั่ง: streamlit run 2_dashboard.py
"""

import streamlit as st
import snowflake.connector
import pandas as pd
import plotly.express as px

# ============================================================
# 🔧 อ่านค่าจาก .streamlit/secrets.toml อัตโนมัติ
# ============================================================

@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        user=st.secrets["SNOWFLAKE_USER"],
        password=st.secrets["SNOWFLAKE_PASSWORD"],
        account=st.secrets["SNOWFLAKE_ACCOUNT"],
        warehouse=st.secrets["SNOWFLAKE_WAREHOUSE"],
        database=st.secrets["SNOWFLAKE_DATABASE"],
        schema=st.secrets["SNOWFLAKE_SCHEMA"]
    )

@st.cache_data
def run_query(query):
    conn = get_connection()
    return pd.read_sql(query, conn)

# ============================================================
# Dashboard Layout
# ============================================================

st.set_page_config(page_title="Airbnb Dashboard", page_icon="🏠", layout="wide")
st.title("🏠 Airbnb Listings Dashboard")
st.markdown("ข้อมูลจาก MongoDB Atlas → Snowflake")

# --- Load data ---
df = run_query("SELECT * FROM LISTINGS")

# --- Sidebar filters ---
st.sidebar.header("🔍 Filter")

room_types = ["All"] + sorted(df["ROOM_TYPE"].dropna().unique().tolist())
selected_room = st.sidebar.selectbox("Room Type", room_types)

neighbourhoods = ["All"] + sorted(df["NEIGHBOURHOOD"].dropna().unique().tolist())
selected_neighbourhood = st.sidebar.selectbox("Neighbourhood", neighbourhoods)

price_min, price_max = int(df["PRICE"].min()), int(df["PRICE"].max())
selected_price = st.sidebar.slider("Price Range ($)", price_min, price_max, (price_min, price_max))

# --- Apply filters ---
filtered = df.copy()
if selected_room != "All":
    filtered = filtered[filtered["ROOM_TYPE"] == selected_room]
if selected_neighbourhood != "All":
    filtered = filtered[filtered["NEIGHBOURHOOD"] == selected_neighbourhood]
filtered = filtered[
    (filtered["PRICE"] >= selected_price[0]) &
    (filtered["PRICE"] <= selected_price[1])
]

# --- KPI Cards ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("📋 Total Listings", f"{len(filtered):,}")
col2.metric("💰 Avg Price", f"${filtered['PRICE'].mean():.0f}")
col3.metric("⭐ Avg Rating", f"{filtered['REVIEW_SCORE_RATING'].mean():.1f}")
col4.metric("🌟 Superhosts", f"{filtered['HOST_IS_SUPERHOST'].sum():,}")

st.divider()

# --- Charts Row 1 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Avg Price by Room Type")
    price_by_room = filtered.groupby("ROOM_TYPE")["PRICE"].mean().reset_index()
    fig1 = px.bar(price_by_room, x="ROOM_TYPE", y="PRICE",
                  color="ROOM_TYPE", text_auto=".0f")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🏘️ Listings by Room Type")
    count_by_room = filtered["ROOM_TYPE"].value_counts().reset_index()
    fig2 = px.pie(count_by_room, names="ROOM_TYPE", values="count")
    st.plotly_chart(fig2, use_container_width=True)

# --- Charts Row 2 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 Top 10 Neighbourhoods by Avg Price")
    top_neighbourhoods = (
        filtered.groupby("NEIGHBOURHOOD")["PRICE"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    fig3 = px.bar(top_neighbourhoods, x="PRICE", y="NEIGHBOURHOOD",
                  orientation="h", text_auto=".0f")
    st.plotly_chart(fig3, use_container_width=True)

with col2:
    st.subheader("⭐ Price vs Rating")
    sample = filtered.dropna(subset=["PRICE", "REVIEW_SCORE_RATING"]).sample(min(500, len(filtered)))
    fig4 = px.scatter(sample, x="REVIEW_SCORE_RATING", y="PRICE",
                      color="ROOM_TYPE", opacity=0.6)
    st.plotly_chart(fig4, use_container_width=True)

# --- Map ---
if "LATITUDE" in filtered.columns and filtered["LATITUDE"].notna().any():
    st.subheader("🗺️ Listings Map")
    map_data = filtered.dropna(subset=["LATITUDE", "LONGITUDE"])
    fig5 = px.scatter_mapbox(
        map_data, lat="LATITUDE", lon="LONGITUDE",
        color="ROOM_TYPE", size="PRICE",
        hover_name="NAME", hover_data=["PRICE", "NEIGHBOURHOOD"],
        mapbox_style="carto-positron", zoom=10, height=500
    )
    st.plotly_chart(fig5, use_container_width=True)

# --- Raw Data ---
st.subheader("📊 Raw Data")
st.dataframe(filtered.head(100), use_container_width=True)
