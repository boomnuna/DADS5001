import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import apply_style, hero, load_data, sidebar_filters, AIRBNB_RED, ROOM_COLORS, BOROUGH_COLORS

st.set_page_config(page_title="Airbnb NYC · Pricing", page_icon="💰", layout="wide")
apply_style()

df_full = load_data()
df = sidebar_filters(df_full)

hero("Pricing Analysis", "Dive into price trends, distributions and neighbourhood rankings", "💰")

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Avg Price",    f"${df['price'].mean():,.0f}")
k2.metric("Median Price", f"${df['price'].median():,.0f}")
k3.metric("Min Price",    f"${df['price'].min():,.0f}")
k4.metric("Max Price",    f"${df['price'].max():,.0f}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 1 ─────────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**Violin: Price Spread by Room Type**")
    fig = px.violin(
        df, x="room type", y="price", color="room type",
        box=True, points=False,
        color_discrete_sequence=ROOM_COLORS,
        labels={"price": "Price ($)", "room type": ""},
    )
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
        yaxis=dict(gridcolor="#F0F0F0"), xaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**Avg Price by Borough**")
    bp = df.groupby("neighbourhood group")["price"].mean().reset_index().sort_values("price", ascending=True)
    bp.columns = ["Borough", "Avg Price"]
    fig2 = px.bar(
        bp, x="Avg Price", y="Borough", orientation="h",
        color="Borough", color_discrete_map=BOROUGH_COLORS,
        labels={"Avg Price": "Avg Price ($)", "Borough": ""},
        text="Avg Price",
    )
    fig2.update_traces(texttemplate="$%{text:.0f}", textposition="outside")
    fig2.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, r=60), font_family="Plus Jakarta Sans",
        xaxis=dict(gridcolor="#F0F0F0", showgrid=True),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Row 2: Price histogram + heatmap ─────────────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**Price Distribution (histogram)**")
    price_cap = st.slider("Cap price at ($)", 100, 2000, 800, 50)
    fig3 = px.histogram(
        df[df["price"] <= price_cap], x="price", nbins=50,
        color_discrete_sequence=[AIRBNB_RED],
        labels={"price": "Price ($)"},
    )
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
        yaxis=dict(gridcolor="#F0F0F0"), xaxis=dict(showgrid=False),
        bargap=0.03,
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**Avg Price Heatmap: Borough × Room Type**")
    pivot = df.groupby(["neighbourhood group", "room type"])["price"].mean().unstack(fill_value=0)
    fig4 = px.imshow(
        pivot,
        color_continuous_scale=["#FFF0F0", AIRBNB_RED],
        labels=dict(color="Avg Price ($)"),
        aspect="auto",
        text_auto=".0f",
    )
    fig4.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
        xaxis_title="", yaxis_title="",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Top neighbourhoods table ──────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="chart-card">', unsafe_allow_html=True)
st.markdown("**🏘️ Top 20 Neighbourhoods by Average Price**")
top = (
    df.groupby("neighbourhood")
    .agg(listings=("price","count"), avg_price=("price","mean"),
         median_price=("price","median"), avg_reviews=("number of reviews","mean"))
    .reset_index()
    .sort_values("avg_price", ascending=False)
    .head(20)
)
top.columns = ["Neighbourhood", "Listings", "Avg Price ($)", "Median Price ($)", "Avg Reviews"]
top["Avg Price ($)"]    = top["Avg Price ($)"].round(0)
top["Median Price ($)"] = top["Median Price ($)"].round(0)
top["Avg Reviews"]      = top["Avg Reviews"].round(1)
st.dataframe(
    top, use_container_width=True, hide_index=True,
    column_config={
        "Avg Price ($)":    st.column_config.NumberColumn(format="$%.0f"),
        "Median Price ($)": st.column_config.NumberColumn(format="$%.0f"),
    }
)
st.markdown('</div>', unsafe_allow_html=True)

st.caption("Built with Streamlit · MongoDB · Plotly 🚀")
