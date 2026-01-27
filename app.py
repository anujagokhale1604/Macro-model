import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro FX Policy Lab v2.0", layout="wide", page_icon="📈")

# --- BRUTE FORCE BLACK TEXT CSS ---
st.markdown("""
    <style>
    /* Force background */
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; border-right: 3px solid #D1C7B7; }

    /* Force all text elements in the sidebar and main body to Black */
    /* Targets labels, sliders, headers, and standard text */
    p, span, label, .stMarkdown, [data-testid="stWidgetLabel"] p, h1, h2, h3, .stSelectbox label p {
        color: #000000 !important;
        font-weight: 800 !important;
        -webkit-text-fill-color: #000000 !important;
        opacity: 1 !important;
    }

    /* Force Metric Values */
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 900 !important; }
    
    /* Make the slider track more visible */
    .stSlider [data-baseweb="slider"] { background-color: #D1C7B7 !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    # Primary Macro Data
    df_macro = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
    df_macro['Date'] = pd.to_datetime(df_macro['Date'])
    
    # FX Data (Using the filenames from your upload)
    inr = pd.read_csv('DEXINUS.xlsx - Daily.csv', parse_dates=['observation_date'])
    gbp = pd.read_csv('DEXUSUK.xlsx - Daily.csv', parse_dates=['observation_date'])
    sgd = pd.read_csv('AEXSIUS.xlsx - Annual.csv', parse_dates=['observation_date'])
    
    return df_macro, inr, gbp, sgd

try:
    df_macro, df_inr, df_gbp, df_sgd = load_all_data()
except Exception as e:
    st.error(f"⚠️ Missing Files: {e}")
    st.stop()

# --- SIDEBAR: NEW SECTIONAL CONTROLS ---
st.sidebar.title("🏛️ Policy Lab v2.0")
st.sidebar.info("If you don't see FX sliders below, please refresh your browser.")

market = st.sidebar.selectbox("1. Select Market", ["India", "UK", "Singapore"])

# --- FX TOGGLES (THE NEW ONES) ---
st.sidebar.header("🌍 2. External Stability (FX)")
fx_deprec = st.sidebar.slider("Simulate FX Depreciation (%)", 0.0, 20.0, 0.0)
fx_beta = st.sidebar.slider("FX Sensitivity (Pass-through)", 0.0, 1.0, 0.2)

# --- MACRO TOGGLES ---
st.sidebar.header("🏗️ 3. Model Calibration")
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 4.0 if market == "India" else 2.0)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, 0.0)

# --- ANALYTICS ENGINE ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx_df": df_inr, "fx_col": "DEXINUS", "label": "INR/USD"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx_df": df_gbp, "fx_col": "DEXUSUK", "label": "USD/GBP"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx_df": df_sgd, "fx_col": "AEXSIUS", "label": "SGD/USD"}
}
m = m_map[market]

# Get data points
latest_macro = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
latest_fx_val = m['fx_df'].dropna(subset=[m['fx_col']]).iloc[-1][m['fx_col']]

# Model Math
base_inf = latest_macro[m['cpi']]
curr_rate = latest_macro[m['rate']]
# Open Economy Taylor Rule: Base + (FX Shock * Beta)
fx_premium = fx_deprec * fx_beta
fair_value = r_star + base_inf + 1.5*(base_inf - target_inf) + 0.5*output_gap + fx_premium
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD UI ---
st.title(f"{market} Policy & FX Intelligence")
st.markdown(f"**Current Status:** Evaluating {m['label']} volatility and local price stability.")

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Spot {m['label']}", f"{latest_fx_val:.2f}")
c2.metric("Headline CPI", f"{base_inf:.2f}%")
c3.metric("Model Fair Value", f"{fair_value:.2f}%")
c4.metric("Action Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- DUAL AXIS CHART ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], 
                         name="Policy Rate (%)", line=dict(color="#000000", width=3)))
fig.add_trace(go.Scatter(x=m['fx_df']['observation_date'], y=m['fx_df'][m['fx_col']], 
                         name=f"FX Rate ({m['label']})", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    height=500,
    yaxis=dict(title="Interest Rate (%)", side="left", showgrid=True, gridcolor="#D1C7B7"),
    yaxis2=dict(title="Exchange Rate", overlaying="y", side="right", showgrid=False),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig, use_container_width=True)

if fx_deprec > 0:
    st.error(f"🚩 **Currency Premium:** A {fx_deprec}% depreciation adds **{fx_premium:.2f}%** to the necessary rate level.")
