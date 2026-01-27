import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="Macro FX Terminal v3.0", layout="wide")

# This CSS forces the labels to be black and avoids the white-text bug in dark mode
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; border-right: 2px solid #D1C7B7; }
    
    /* Global Black Text Override */
    p, span, label, h1, h2, h3, .stWidgetLabel p, [data-testid="stWidgetLabel"] p {
        color: #000000 !important;
        font-weight: 800 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 900 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE SIDEBAR (Toggles are here) ---
st.sidebar.title("🏛️ Terminal v3.0")
st.sidebar.info("If you see 'v3.0', the update worked.")

# Country Selection
market = st.sidebar.selectbox("1. Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 2. External Stability (FX)")
# NEW TOGGLES
fx_shock = st.sidebar.slider("Simulate FX Shock (%)", 0.0, 20.0, 0.0, help="Simulate local currency depreciation")
fx_sensitivity = st.sidebar.slider("FX Pass-Through (Beta)", 0.0, 1.0, 0.2, help="CB sensitivity to FX volatility")

st.sidebar.divider()
st.sidebar.subheader("🏗️ 3. Domestic Calibration")
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 2.0)

# --- 3. DATA LOADING (Multi-File Handling) ---
@st.cache_data
def load_all_datasets():
    # Load separate files
    try:
        # 1. Main Macro File
        df_m = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df_m['Date'] = pd.to_datetime(df_m['Date'])
        
        # 2. FX Files (Separate CSVs)
        inr = pd.read_csv('DEXINUS.xlsx - Daily.csv', parse_dates=['observation_date'])
        gbp = pd.read_csv('DEXUSUK.xlsx - Daily.csv', parse_dates=['observation_date'])
        sgd = pd.read_csv('AEXSIUS.xlsx - Annual.csv', parse_dates=['observation_date'])
        
        return df_m, inr, gbp, sgd, True
    except Exception as e:
        return None, None, None, None, f"Error: {e}"

df_macro, df_inr, df_gbp, df_sgd, status = load_all_datasets()

# --- 4. MAIN DASHBOARD LOGIC ---
st.title(f"Global Macro Terminal: {market}")

if status is not True:
    st.error(f"⚠️ Files not found on GitHub: {status}")
    st.stop()

# Mapping
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx": df_inr, "col": "DEXINUS", "unit": "INR/USD"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx": df_gbp, "col": "DEXUSUK", "unit": "USD/GBP"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx": df_sgd, "col": "AEXSIUS", "unit": "SGD/USD"}
}
m = m_map[market]

# Analytics
latest_macro = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
latest_fx = m['fx'].dropna(subset=[m['col']]).iloc[-1]

inf = latest_macro[m['cpi']]
curr = latest_macro[m['rate']]
fx_val = latest_fx[m['col']]

# Open Economy Taylor Rule Calculation
# Fair Value = r* + Inflation + 1.5*(Inf - Target) + (FX_Shock * Beta)
fx_premium = fx_shock * fx_sensitivity
fair_value = r_star + inf + 1.5*(inf - target_inf) + fx_premium
gap = (fair_value - curr) * 100

# --- 5. VISUALS ---
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Spot {m['unit']}", f"{fx_val:.2f}")
c2.metric("Headline CPI", f"{inf:.2f}%")
c3.metric("Taylor Fair Value", f"{fair_value:.2f}%")
c4.metric("Action Gap", f"{gap:+.0f} bps", delta_color="inverse")

# Plot
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate (%)", line=dict(color="black", width=3)))
fig.add_trace(go.Scatter(x=m['fx']['observation_date'], y=m['fx'][m['col']], name=f"FX ({m['unit']})", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    yaxis=dict(title="Rate (%)", side="left"),
    yaxis2=dict(title="Exchange Rate", overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500
)
st.plotly_chart(fig, use_container_width=True)
