import streamlit as st
import pandas as pd
from pymongo import MongoClient
import os

AIRBNB_RED   = "#FF385C"
AIRBNB_DARK  = "#222222"
AIRBNB_GRAY  = "#717171"
AIRBNB_LIGHT = "#F7F7F7"

BOROUGH_COLORS = {
    "Manhattan":     "#FF385C",
    "Brooklyn":      "#00A699",
    "Queens":        "#FC642D",
    "Bronx":         "#7B61FF",
    "Staten Island": "#FFB400",
}

ROOM_COLORS = ["#FF385C", "#00A699", "#FC642D", "#7B61FF"]

GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Circular+Std:wght@400;500;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', sans-serif;
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background: {AIRBNB_DARK} !important;
    border-right: none !important;
}}
[data-testid="stSidebar"] * {{
    color: #fff !important;
}}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stSlider label {{
    color: #aaa !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
[data-testid="stSidebar"] [data-baseweb="tag"] {{
    background: {AIRBNB_RED} !important;
    border-radius: 20px !important;
}}
[data-testid="stSidebar"] .stSlider [data-testid="stThumbValue"] {{
    color: #fff !important;
}}

/* Main area */
.main {{ background: #FAFAFA; }}

/* Metric cards */
[data-testid="metric-container"] {{
    background: #fff;
    border: 1px solid #EBEBEB;
    border-radius: 16px;
    padding: 20px 24px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}}
[data-testid="metric-container"]:hover {{
    box-shadow: 0 6px 24px rgba(0,0,0,0.1);
}}
[data-testid="metric-container"] label {{
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {AIRBNB_GRAY} !important;
}}
[data-testid="metric-container"] [data-testid="metric-value"] {{
    font-size: 28px !important;
    font-weight: 700 !important;
    color: {AIRBNB_DARK} !important;
}}

/* Page title */
.page-hero {{
    background: linear-gradient(135deg, {AIRBNB_RED} 0%, #E31C5F 100%);
    border-radius: 20px;
    padding: 32px 36px;
    margin-bottom: 28px;
    color: white;
}}
.page-hero h1 {{
    font-size: 32px;
    font-weight: 700;
    margin: 0 0 6px 0;
    color: white;
}}
.page-hero p {{
    font-size: 15px;
    opacity: 0.85;
    margin: 0;
    color: white;
}}

/* Chart card */
.chart-card {{
    background: white;
    border-radius: 16px;
    border: 1px solid #EBEBEB;
    padding: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}}

/* Divider */
hr {{ border-color: #EBEBEB !important; margin: 24px 0 !important; }}

/* Dataframe */
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}

/* Hide streamlit branding */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
header {{ visibility: hidden; }}
</style>
"""

def apply_style():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

def hero(title: str, subtitle: str, emoji: str = "🏠"):
    st.markdown(f"""
    <div class="page-hero">
        <h1>{emoji} {title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ── MongoDB ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_mongo_client():
    uri = st.secrets["MONGO_URI"]
    return MongoClient(uri, serverSelectionTimeoutMS=5000)

@st.cache_data(ttl=300, show_spinner="⏳ Loading data from MongoDB…")
def load_data():
    try:
        client = get_mongo_client()
        db  = client[st.secrets.get("MONGO_DB", "dataset_airbnb")]
        col = db[st.secrets.get("MONGO_COLLECTION", "dads_dataset")]
        cursor = col.find({}, {"_id": 0})
        df = pd.DataFrame(list(cursor))
        return _clean(df)
    except Exception as e:
        st.warning(f"⚠️ MongoDB unavailable — using local CSV. ({e})")
        return _load_csv()

def _load_csv():
    path = os.path.join(os.path.dirname(__file__), "Airbnb_Open_Data.csv")
    if not os.path.exists(path):
        st.error("CSV not found. Please check your setup.")
        st.stop()
    return _clean(pd.read_csv(path))

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    for c in ["price", "service fee"]:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(r"[\$,\s]", "", regex=True).replace("nan", None),
                errors="coerce"
            )
    if "neighbourhood group" in df.columns:
        df["neighbourhood group"] = (
            df["neighbourhood group"].astype(str).str.strip()
            .replace({"brookln": "Brooklyn", "manhatan": "Manhattan"})
        )
    for c in ["minimum nights","number of reviews","review rate number","availability 365","Construction year"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["price"])
    df = df[df["price"].between(10, 5000)]
    return df.reset_index(drop=True)

# ── Sidebar filters (shared) ──────────────────────────────────────────────────
def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("""
    <div style='padding:24px 0 8px 0; text-align:center;'>
        <div style='font-size:28px'>🏠</div>
        <div style='font-size:18px;font-weight:700;color:#fff;letter-spacing:-0.5px;'>Airbnb NYC</div>
        <div style='font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:1px;margin-top:2px;'>Dashboard</div>
    </div>
    <hr style='border-color:#444;margin:12px 0 20px 0;'/>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<p style='color:#aaa;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Borough</p>", unsafe_allow_html=True)
    boroughs = sorted(df["neighbourhood group"].dropna().unique())
    sel_boroughs = st.sidebar.multiselect("Borough", boroughs, default=boroughs, label_visibility="collapsed")

    st.sidebar.markdown("<p style='color:#aaa;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;margin-top:16px;'>Room Type</p>", unsafe_allow_html=True)
    room_types = sorted(df["room type"].dropna().unique())
    sel_rooms = st.sidebar.multiselect("Room Type", room_types, default=room_types, label_visibility="collapsed")

    st.sidebar.markdown("<p style='color:#aaa;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;margin-top:16px;'>Price per Night</p>", unsafe_allow_html=True)
    pmin, pmax = int(df["price"].min()), int(df["price"].max())
    sel_price = st.sidebar.slider("Price", pmin, pmax, (pmin, min(pmax, 500)), label_visibility="collapsed")

    filtered = df[
        df["neighbourhood group"].isin(sel_boroughs) &
        df["room type"].isin(sel_rooms) &
        df["price"].between(*sel_price)
    ]

    if "cancellation_policy" in df.columns:
        st.sidebar.markdown("<p style='color:#aaa;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;margin-top:16px;'>Cancellation</p>", unsafe_allow_html=True)
        policies = sorted(df["cancellation_policy"].dropna().unique())
        sel_policy = st.sidebar.multiselect("Policy", policies, default=policies, label_visibility="collapsed")
        filtered = filtered[filtered["cancellation_policy"].isin(sel_policy)]

    st.sidebar.markdown(f"""
    <div style='margin-top:24px;padding:14px 16px;background:rgba(255,56,92,0.15);border-radius:12px;border:1px solid rgba(255,56,92,0.3);'>
        <div style='color:#FF385C;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;'>Filtered listings</div>
        <div style='color:#fff;font-size:24px;font-weight:700;margin-top:4px;'>{len(filtered):,}</div>
    </div>
    """, unsafe_allow_html=True)

    return filtered
