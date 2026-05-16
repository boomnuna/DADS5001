import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import apply_style, hero, load_data, sidebar_filters, AIRBNB_RED, ROOM_COLORS, BOROUGH_COLORS

st.set_page_config(page_title="Airbnb NYC · Hosts", page_icon="👤", layout="wide")
apply_style()

df_full = load_data()
df = sidebar_filters(df_full)

hero("Host Insights", "Analyse host behaviour, listing counts and identity verification", "👤")

c1, c2, c3 = st.columns(3)

# Verified hosts
if "host_identity_verified" in df.columns:
    verified = df["host_identity_verified"].value_counts()
    verified_pct = verified.get("verified", 0) / len(df) * 100
    c1.metric("Verified Hosts", f"{verified_pct:.1f}%")
else:
    c1.metric("Verified Hosts", "N/A")

# Instant bookable
if "instant_bookable" in df.columns:
    instant_pct = df["instant_bookable"].sum() / len(df) * 100
    c2.metric("Instant Bookable", f"{instant_pct:.1f}%")
else:
    c2.metric("Instant Bookable", "N/A")

# Avg listings per host
if "calculated host listings count" in df.columns:
    avg_host = df["calculated host listings count"].mean()
    c3.metric("Avg Listings / Host", f"{avg_host:.1f}")
else:
    c3.metric("Avg Listings / Host", "N/A")

st.markdown("<br>", unsafe_allow_html=True)

c4, c5 = st.columns(2)

with c4:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**🏠 Room Type Distribution**")
    rt = df["room type"].value_counts().reset_index()
    rt.columns = ["Room Type", "Count"]
    fig = px.bar(
        rt, x="Room Type", y="Count",
        color="Room Type", color_discrete_sequence=ROOM_COLORS,
        text="Count",
    )
    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
        yaxis=dict(gridcolor="#F0F0F0"), xaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c5:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**✅ Host Identity Verified**")
    if "host_identity_verified" in df.columns:
        verified_counts = df["host_identity_verified"].value_counts().reset_index()
        verified_counts.columns = ["Status", "Count"]
        fig2 = px.pie(
            verified_counts, names="Status", values="Count", hole=0.55,
            color_discrete_sequence=[AIRBNB_RED, "#EBEBEB"],
        )
        fig2.update_traces(textposition="outside", textinfo="percent+label")
        fig2.update_layout(
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
        )
        st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Construction year
if "Construction year" in df.columns:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**🏗️ Listings by Construction Year**")
    yr = df["Construction year"].dropna()
    yr = yr[(yr >= 1900) & (yr <= 2025)]
    yr_df = yr.value_counts().sort_index().reset_index()
    yr_df.columns = ["Year", "Count"]
    fig3 = px.area(
        yr_df, x="Year", y="Count",
        color_discrete_sequence=[AIRBNB_RED],
        labels={"Year": "Construction Year", "Count": "Listings"},
    )
    fig3.update_traces(fillcolor="rgba(255,56,92,0.1)", line_color=AIRBNB_RED)
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
        yaxis=dict(gridcolor="#F0F0F0"), xaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("Built with Streamlit · MongoDB · Plotly 🚀")
