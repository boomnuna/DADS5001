import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils import apply_style, hero, load_data, sidebar_filters, AIRBNB_RED, AIRBNB_GRAY, ROOM_COLORS, BOROUGH_COLORS

st.set_page_config(page_title="Airbnb NYC · Overview", page_icon="🏠", layout="wide")
apply_style()

df_full = load_data()
df = sidebar_filters(df_full)

# ── Hero ──────────────────────────────────────────────────────────────────────
hero("Airbnb NYC Dashboard", "Explore listings, prices, and trends across New York City", "🏠")

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Listings",      f"{len(df):,}")
k2.metric("Avg Price / Night",   f"${df['price'].mean():,.0f}")
k3.metric("Median Price",        f"${df['price'].median():,.0f}")
k4.metric("Avg Reviews",         f"{df['number of reviews'].mean():.1f}")
k5.metric("Avg Availability",    f"{df['availability 365'].mean():.0f} days")

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 1: Price box + Borough pie ────────────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**📊 Price Distribution by Room Type**")
    fig = px.box(
        df, x="room type", y="price", color="room type",
        color_discrete_sequence=ROOM_COLORS,
        labels={"price": "Price ($)", "room type": ""},
    )
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10),
        font_family="Plus Jakarta Sans",
        yaxis=dict(gridcolor="#F0F0F0"),
        xaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**🗺️ Listings by Borough**")
    bc = df["neighbourhood group"].value_counts().reset_index()
    bc.columns = ["Borough", "Count"]
    fig2 = px.pie(
        bc, names="Borough", values="Count", hole=0.55,
        color="Borough",
        color_discrete_map=BOROUGH_COLORS,
    )
    fig2.update_traces(textposition="outside", textinfo="percent+label")
    fig2.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10),
        font_family="Plus Jakarta Sans",
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Row 2: Grouped bar + histogram ────────────────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**💰 Avg Price by Borough & Room Type**")
    grp = df.groupby(["neighbourhood group", "room type"])["price"].mean().reset_index()
    fig3 = px.bar(
        grp, x="neighbourhood group", y="price", color="room type",
        barmode="group",
        color_discrete_sequence=ROOM_COLORS,
        labels={"price": "Avg Price ($)", "neighbourhood group": ""},
    )
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10),
        font_family="Plus Jakarta Sans",
        yaxis=dict(gridcolor="#F0F0F0"),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**📅 Availability Distribution**")
    fig4 = px.histogram(
        df, x="availability 365", nbins=40,
        color_discrete_sequence=[AIRBNB_RED],
        labels={"availability 365": "Days Available / Year"},
    )
    fig4.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10),
        font_family="Plus Jakarta Sans",
        yaxis=dict(gridcolor="#F0F0F0"),
        xaxis=dict(showgrid=False),
        bargap=0.05,
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("Built with Streamlit · MongoDB · Plotly 🚀")
