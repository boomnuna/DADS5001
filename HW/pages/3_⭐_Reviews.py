import streamlit as st
import pandas as pd
import plotly.express as px
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import apply_style, hero, load_data, sidebar_filters, AIRBNB_RED, ROOM_COLORS, BOROUGH_COLORS

st.set_page_config(page_title="Airbnb NYC · Reviews", page_icon="⭐", layout="wide")
apply_style()

df_full = load_data()
df = sidebar_filters(df_full)

hero("Reviews & Ratings", "Understand guest satisfaction across room types and boroughs", "⭐")

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Avg Reviews/Listing",  f"{df['number of reviews'].mean():.1f}")
k2.metric("Total Reviews",        f"{df['number of reviews'].sum():,.0f}")
k3.metric("Avg Rating Score",     f"{df['review rate number'].mean():.2f} / 5" if "review rate number" in df.columns else "N/A")
k4.metric("Instant Bookable",     f"{df['instant_bookable'].sum():,}" if "instant_bookable" in df.columns else "N/A")

st.markdown("<br>", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**⭐ Review Rate Distribution**")
    if "review rate number" in df.columns:
        rev = df["review rate number"].dropna().value_counts().sort_index().reset_index()
        rev.columns = ["Rating", "Count"]
        fig = px.bar(
            rev, x="Rating", y="Count",
            color_discrete_sequence=[AIRBNB_RED],
            labels={"Rating": "Rating (1–5)", "Count": "Number of Listings"},
            text="Count",
        )
        fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
            yaxis=dict(gridcolor="#F0F0F0"), xaxis=dict(showgrid=False),
            bargap=0.2,
        )
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**📊 Avg Reviews by Borough**")
    rev_bor = df.groupby("neighbourhood group")["number of reviews"].mean().reset_index().sort_values("number of reviews", ascending=False)
    rev_bor.columns = ["Borough", "Avg Reviews"]
    fig2 = px.bar(
        rev_bor, x="Borough", y="Avg Reviews",
        color="Borough", color_discrete_map=BOROUGH_COLORS,
        text="Avg Reviews",
    )
    fig2.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig2.update_layout(
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
        yaxis=dict(gridcolor="#F0F0F0"), xaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

c3, c4 = st.columns(2)

with c3:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**🔒 Cancellation Policy Breakdown**")
    if "cancellation_policy" in df.columns:
        canc = df["cancellation_policy"].value_counts().reset_index()
        canc.columns = ["Policy", "Count"]
        colors = {"flexible": "#00A699", "moderate": "#FC642D", "strict": "#FF385C"}
        fig3 = px.pie(
            canc, names="Policy", values="Count", hole=0.5,
            color="Policy", color_discrete_map=colors,
        )
        fig3.update_traces(textposition="outside", textinfo="percent+label")
        fig3.update_layout(
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
        )
        st.plotly_chart(fig3, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with c4:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("**💬 Reviews vs Price (scatter)**")
    sample = df.sample(min(2000, len(df)), random_state=1)
    fig4 = px.scatter(
        sample, x="price", y="number of reviews",
        color="room type",
        color_discrete_sequence=ROOM_COLORS,
        opacity=0.5,
        labels={"price": "Price ($)", "number of reviews": "# Reviews"},
        hover_name="NAME" if "NAME" in sample.columns else None,
    )
    fig4.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10), font_family="Plus Jakarta Sans",
        yaxis=dict(gridcolor="#F0F0F0"), xaxis=dict(gridcolor="#F0F0F0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("Built with Streamlit · MongoDB · Plotly 🚀")
