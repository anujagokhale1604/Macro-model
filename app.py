import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Macro FX Terminal v5.0", layout="wide")

# --- 2. THEME & HIGH-CONTRAST CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; border-right: 2px solid #D1C7B7; }
    p, span, label, h1, h2, h3, [data-testid="stWidgetLabel"] p {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR: POLICY CONTROLS ---
st.sidebar.title("🏛️ Surveillance Lab")
market = st.sidebar.selectbox("1. Select Market", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 2. External Stability (FX)")
st.sidebar.caption("Work-in-Progress: FX Pass-through Integration")
# These are the toggles mentioned in your resume
fx_deprec = st.sidebar.slider("Simulate FX Shock (%)", 0.0, 20.0, 0.0)
fx_beta = st.sidebar.slider("FX Pass-through (Beta)", 0.0, 1.0, 0.2)

st.sidebar.divider()
st.sidebar.subheader("🏗️ 3. Domestic Calibration")
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 2.0 if market != "India" else 4.0)

# --- 4. DATA PIPELINE (The "Resampling" Logic) ---
@st.cache_data
def load_macro_data():
    try:
        # Loading the primary macro file
        df = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception as e:
        st.sidebar.error(f"Macro File Error: {e}")
        return None

df_macro = load_macro_data()

# --- 5. DASHBOARD ENGINE ---
st.title(f"Macro Policy Terminal: {market}")

if df_macro is not None:
    # Mapping columns
    m_map = {
        "India": {"cpi": "CPI_India", "rate": "Policy_India", "unit": "INR/USD"},
        "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "unit": "USD/GBP"},
        "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "unit": "SGD/USD"}
    }
    m = m_map[market]
    
    # Extracting latest data points
    latest_macro = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
    base_inf = latest_macro[m['cpi']]
    curr_rate = latest_macro[m['rate']]
    
    # OPEN ECONOMY TAYLOR RULE: 
    # Fair Value = r* + Inf + 1.5*(Inf - Target) + (FX Shock * Beta)
    fx_premium = fx_deprec * fx_beta
    fair_value = r_star + base_inf + 1.5*(base_inf - target_inf) + fx_premium
    gap_bps = (fair_value - curr_rate) * 100

    # DISPLAY METRICS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Headline CPI", f"{base_inf:.2f}%")
    c2.metric("Neutral Rate (r*)", f"{r_star:.1f}%")
    c3.metric("Model Fair Value", f"{fair_value:.2f}%")
    c4.metric("Action Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

    # VISUALIZATION
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], 
                             name="Policy Rate (%)", line=dict(color="#1A1C1E", width=3)))
    
    fig.update_layout(
        title=f"Historical Policy Path: {market}",
        yaxis_title="Interest Rate (%)",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=50)
    )
    st.plotly_chart(fig, use_container_width=True)

    # INSIGHT BOX
    if fx_deprec > 0:
        st.warning(f"**FX Stress Test:** A {fx_deprec}% depreciation adds a **{fx_premium:.2f}%** risk premium to the fair value, highlighting the trade-off between currency stability and domestic rates.")
else:
    st.info("Please ensure 'EM_Macro_Data_India_SG_UK.xlsx' is in your GitHub repository to view analytics.")
