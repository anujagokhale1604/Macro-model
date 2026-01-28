import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime

# --- 1. SETTINGS ---
st.set_page_config(page_title="Macro Surveillance Terminal", layout="wide")

# High-authority branding
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stWidgetLabel"] p, label p, h1, h2, h3 {
        color: #333333 !important; font-weight: 800 !important;
    }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #D1C7B7; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE RESILIENT DATA ENGINE ---
@st.cache_data
def load_and_clean_data():
    try:
        # Load Main Macro File
        macro_file = 'EM_Macro_Data_India_SG_UK.xlsx'
        if not os.path.exists(macro_file):
            return None, f"Missing file: {macro_file}"
            
        df_macro = pd.read_excel(macro_file, sheet_name="Macro data")
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        
        def scrape_fred_file(filename):
            if not os.path.exists(filename):
                raise FileNotFoundError(f"File {filename} not found.")
            
            # Load the whole file to scan for data start
            raw = pd.read_excel(filename, header=None)
            
            # Find the first row where the first column is a date
            start_row = 0
            for i in range(len(raw)):
                try:
                    test_val = pd.to_datetime(raw.iloc[i, 0], errors='raise')
                    if not pd.isna(test_val):
                        start_row = i
                        break
                except:
                    continue
            
            # Reload from the detected data start
            df = pd.read_excel(filename, skiprows=start_row, header=None)
            df.columns = ['date', 'val']
            
            # Convert and Clean
            df['val'] = pd.to_numeric(df['val'], errors='coerce')
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            return df.dropna(subset=['val', 'date']).reset_index(drop=True)

        # Ingest FX sources
        inr = scrape_fred_file('DEXINUS.xlsx')
        gbp = scrape_fred_file('DEXUSUK.xlsx')
        sgd = scrape_fred_file('AEXSIUS.xlsx')
        
        return (df_macro, inr, gbp, sgd), None
        
    except Exception as e:
        return None, str(e)

# UNPACKING SAFELY
data_bundle, error_msg = load_and_clean_data()

if error_msg or data_bundle is None:
    st.error(f"🛠️ **Terminal Offline:** {error_msg}")
    st.info(f"Verified files in root: {os.listdir('.')}")
    st.stop()

# Assign variables from bundle
df_macro, df_inr, df_gbp, df_sgd = data_bundle

# --- 3. DASHBOARD ANALYTICS ---
st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 External Shock")
fx_shock = st.sidebar.slider("FX Depreciation (%)", 0.0, 15.0, 0.0)
beta = st.sidebar.slider("Pass-through Beta", 0.0, 1.0, 0.2)

st.sidebar.divider()
st.sidebar.subheader("🏗️ Internal Calibration")
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)

# Mapping
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx": df_inr},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx": df_gbp},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx": df_sgd}
}

m = m_map[market]
latest_macro = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
latest_fx = m['fx'].iloc[-1]

# Taylor Rule: Policy = r* + Inf + 1.5*(Inf - Target) + (FX Shock * Beta)
fair_value = r_star + latest_macro[m['cpi']] + 1.5*(latest_macro[m['cpi']] - 2.0) + (fx_shock * beta)
gap = (fair_value - latest_macro[m['rate']]) * 100

# --- 4. VISUALIZATION ---
st.title(f"{market} Policy & Stability Terminal")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Spot FX Rate", f"{latest_fx['val']:.2f}")
c2.metric("Headline CPI", f"{latest_macro[m['cpi']]:.2f}%")
c3.metric("Taylor Fair Value", f"{fair_value:.2f}%")
c4.metric("Action Gap", f"{gap:+.0f} bps", delta_color="inverse")

# Dual Axis Plot
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate (%)", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=m['fx']['date'], y=m['fx']['val'], name="Historical FX", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    yaxis=dict(title="Policy Rate (%)", gridcolor="#E0E0E0"),
    yaxis2=dict(title="FX Rate (vs USD)", overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("Terminal v6.5 | Developed for MAS EPG Technical Evaluation")
