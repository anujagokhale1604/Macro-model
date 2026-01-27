import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro FX Policy Lab", layout="wide", page_icon="📈")

# --- GLOBAL HIGH-CONTRAST CSS (Fixed for Dark/Light Mode) ---
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; border-right: 2px solid #D1C7B7; }

    /* FORCE ALL LABELS TO JET BLACK */
    /* This targets the exact class Streamlit uses for Slider and Selectbox titles */
    .stWidgetLabel p, label p, [data-testid="stWidgetLabel"] p {
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
        -webkit-text-fill-color: #000000 !important;
    }

    /* Standard Text */
    .stMarkdown, p, span, h1, h2, h3 {
        color: #1A1C1E !important;
        font-family: 'Georgia', serif !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] p { color: #493D31 !important; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    # Primary Macro Data
    df_macro = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
    df_macro['Date'] = pd.to_datetime(df_macro['Date'])
    
    # FX Data (From your uploads)
    inr = pd.read_csv('DEXINUS.xlsx - Daily.csv', parse_dates=['observation_date'])
    gbp = pd.read_csv('DEXUSUK.xlsx - Daily.csv', parse_dates=['observation_date'])
    sgd = pd.read_csv('AEXSIUS.xlsx - Annual.csv', parse_dates=['observation_date'])
    
    return df_macro, inr, gbp, sgd

try:
    df_macro, df_inr, df_gbp, df_sgd = load_all_data()
except Exception as e:
    st.error(f"Error loading files: {e}")
    st.stop()

# --- SIDEBAR: CONTROLS ---
st.sidebar.title("📜 Policy Lab")

market = st.sidebar.selectbox("1. Select Market", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 2. External Stability (FX)")
# THESE ARE THE FX TOGGLES YOU WERE LOOKING FOR:
fx_deprec = st.sidebar.slider("Simulate FX Depreciation (%)", 0.0, 20.0, 0.0, help="Simulate a sudden drop in local currency value vs USD")
fx_beta = st.sidebar.slider("FX Pass-through (Sensitivity)", 0.0, 1.0, 0.2, help="How much the Central Bank reacts to FX volatility")

st.sidebar.divider()
st.sidebar.subheader("🏗️ 3. Model Calibration")
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

# Get latest points
latest_macro = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
latest_fx_val = m['fx_df'][m['fx_col']].iloc[-1]

# Calculation: Open Economy Taylor Rule
# Rate = Neutral + Inflation + 1.5*(Inf - Target) + 0.5*(Gap) + (FX_Deprec * FX_Beta)
base_inf = latest_macro[m['cpi']]
curr_rate = latest_macro[m['rate']]
fx_premium = fx_deprec * fx_beta
fair_value = r_star + base_inf + 1.5*(base_inf - target_inf) + 0.5*output_gap + fx_premium
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Intelligence Terminal")
st.write(f"Integrating Macroeconomic Indicators with **{m['label']}** Exchange Rate stability.")

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Current {m['label']}", f"{latest_fx_val:.2f}")
c2.metric("Headline CPI", f"{base_inf:.2f}%")
c3.metric("Taylor Fair Value", f"{fair_value:.2f}%")
c4.metric("Policy Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART ---
fig = go.Figure()
# Policy Rate (Left Axis)
fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate (%)", line=dict(color="#1A1C1E", width=3)))
# FX Rate (Right Axis)
fig.add_trace(go.Scatter(x=m['fx_df']['observation_date'], y=m['fx_df'][m['fx_col']], 
                         name=f"FX Rate ({m['label']})", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    title=f"Historical Correlation: Interest Rates vs {m['label']}",
    yaxis=dict(title="Interest Rate (%)", side="left", showgrid=True, gridcolor="#D1C7B7"),
    yaxis2=dict(title=f"Exchange Rate ({m['label']})", overlaying="y", side="right", showgrid=False),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(t=50, b=100)
)
st.plotly_chart(fig, use_container_width=True)

# --- INSIGHT BOX ---
if fx_deprec > 0:
    st.error(f"🚩 **Currency Pressure Alert:** A simulated {fx_deprec}% depreciation adds a **{fx_premium:.2f}% risk premium** to the model's fair value rate to prevent further capital outflow.")
else:
    st.info("💡 **Insight:** Central Banks in Emerging Markets often maintain a higher 'Fair Value' rate than the standard Taylor Rule suggests to protect the currency against USD volatility.")
