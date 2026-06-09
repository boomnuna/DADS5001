import streamlit as st


def setup_page(title: str) -> None:
    st.set_page_config(page_title=title, page_icon="STK", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        .small-note { color: #777; font-size: 0.82rem; }
        .metric-card {
            border: 1px solid #E5E2DA;
            border-radius: 8px;
            padding: 14px 16px;
            background: #FBFAF7;
        }
        .decision-buy { color: #2F6B1D; font-weight: 700; }
        .decision-hold { color: #A56A00; font-weight: 700; }
        .decision-sell { color: #A32D2D; font-weight: 700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def disclaimer() -> None:
    st.caption("Educational demo only. This is not financial advice.")

