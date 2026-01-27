import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Macro FX Terminal v5.0", layout="wide")

# --- 2. CSS RESET (Forcing a color change to prove update) ---
st.markdown("""
    <style>
    /* If the background is not this 'Parchment' color, the update failed */
    .stApp { background-color: #FDF5E6 !important; } 
    
    [data-testid="stSidebar"] { background-color: #F5DEB3 !important; border-right: 3px solid #8B4513; }
    
    /* Force all text to High-Contrast Black */
    p, span, label, h1, h2, h3, [data-testid="stWidgetLabel"] p {
        color: #000000 !important;
        font-weight: 800 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. THE SIDEBAR (Redesigned to avoid caching) ---
st.sidebar.title("🏛️ TERMINAL v5.0")

# If you still see "Scenario" or "Framework" below, the code didn't update!
st.sidebar.header("🌍 FX STABILITY")
fx_shock = st.sidebar.slider("Simulate FX Shock (%)", 0.0, 20.0, 0.0)
fx_beta = st.sidebar.slider("FX Pass-Through (Beta)", 0.0, 1.0, 0.2)

st.sidebar.header("🏗️ DOMESTIC CALIBRATION")
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 2.0)

market = st.sidebar.selectbox("Select Country", ["India", "UK", "Singapore"])

if st.sidebar.button("🔄 FORCE CLEAR CACHE"):
    st.cache_data.clear()
    st.rerun()

# --- 4. DATA LOADING ---
def load_data():
    # Names exactly as they appear in your GitHub
    f_macro = 'EM_Macro_Data_India_SG_UK.xlsx'
    f_inr = 'DEXINUS.xlsx - Daily.csv'
    f_gbp = 'DEXUSUK.xlsx - Daily.csv'
    f_sgd = 'AEXSIUS.xlsx - Annual.csv'
    
    files = [f_macro, f_inr, f_gbp, f_sgd]
    missing = [f for f in files if not os.path.exists(f)]
    
    if missing:
        return None, f"Missing files: {', '.join(missing)}"
    
    try:
        df_m = pd.read_excel(f_macro, sheet_name="Macro data")
        inr = pd.read_csv(f_inr, parse_dates=['observation_date'])
        gbp = pd.read_csv(f_gbp, parse_dates=['observation_date'])
        sgd = pd.read_csv(f_sgd, parse_dates=['observation_date'])
        return (df_m, inr, gbp, sgd), "Success"
    except Exception as e:
        return None, str(e)

datasets, message = load_data()

# --- 5. MAIN VIEW ---
st.title(f"Macro Terminal: {market}")

if datasets is None:
    st.warning(f"Status: {message}")
    st.info("The FX Toggles should be visible in the sidebar even if data is missing.")
else:
    df_macro, df_inr, df_gbp, df_sgd = datasets
    
    # Simple mapping for display
    m_map = {
        "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx": df_inr, "col": "DEXINUS"},
        "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx": df_gbp, "col": "DEXUSUK"},
        "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx": df_sgd, "col": "AEXSIUS"}
    }
    m = m_map[market]
    
    # Analytics
    inf = df_macro.dropna(subset=[m['cpi']]).iloc[-1][m['cpi']]
    curr = df_macro.dropna(subset=[m['rate']]).iloc[-1][m['rate']]
    
    # Calculate Fair Value (Taylor + FX Premium)
    fair_value = r_star + inf + 1.5*(inf - target_inf) + (fx_shock * fx_beta)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Current Inflation", f"{inf:.2f}%")
    c2.metric("Taylor Fair Value", f"{fair_value:.2f}%")
    c3.metric("Current Policy Rate", f"{curr:.2f}%")

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate", line=dict(color="black")))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)
