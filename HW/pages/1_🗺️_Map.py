import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import apply_style, hero, load_data, sidebar_filters, ROOM_COLORS

st.set_page_config(page_title="Airbnb NYC · Map", page_icon="🗺️", layout="wide")
apply_style()

df_full = load_data()
df = sidebar_filters(df_full)

hero("Listing Map", "See where listings are located across NYC boroughs", "🗺️")

# Controls row
col_a, col_b, col_c = st.columns([1, 1, 2])
with col_a:
    max_points = st.selectbox("Max listings on map", [1000, 2000, 3000, 5000], index=1)
with col_b:
    color_by = st.selectbox("Color by", ["room type", "neighbourhood group"])
with col_c:
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(f"Showing up to {max_points:,} randomly sampled listings from {len(df):,} filtered results")

st.markdown("<br>", unsafe_allow_html=True)

map_df = df.dropna(subset=["lat", "long"]).sample(min(max_points, len(df)), random_state=42)

fig_map = px.scatter_mapbox(
    map_df,
    lat="lat", lon="long",
    color=color_by,
    size="price",
    size_max=14,
    hover_name="NAME",
    hover_data={
        "price": True,
        "neighbourhood group": True,
        "room type": True,
        "lat": False,
        "long": False,
    },
    color_discrete_sequence=ROOM_COLORS,
    zoom=10,
    height=580,
    mapbox_style="carto-positron",
    opacity=0.8,
)
fig_map.update_layout(
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    legend=dict(
        orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
        bgcolor="rgba(255,255,255,0.9)", bordercolor="#EBEBEB", borderwidth=1,
        font=dict(family="Plus Jakarta Sans"),
    ),
    font_family="Plus Jakarta Sans",
)
st.plotly_chart(fig_map, use_container_width=True)

# Stats below map
st.divider()
st.markdown("**📍 Listings per Borough (filtered)**")
cols = st.columns(5)
for i, (borough, grp) in enumerate(df.groupby("neighbourhood group")):
    with cols[i % 5]:
        avg = grp["price"].mean()
        st.metric(borough, f"{len(grp):,}", f"${avg:.0f} avg/night")

st.caption("Built with Streamlit · MongoDB · Plotly 🚀")
