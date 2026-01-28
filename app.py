import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime

# --- 1. SETTINGS ---
st.set_page_config(page_title="Macro FX Terminal v6.4", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stWidgetLabel"] p, label p, h1, h2, h3 {
        color: #333333 !important; font-weight: 800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE BRUTE-FORCE DATA ENGINE ---
@st.cache_data
def load_and_clean_data():
    try:
        # Load Main Macro File
        df_macro = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        
        def scrape_fred_file(filename):
            # Load raw to find where data actually starts
            raw = pd.read_excel(filename)
            # Find first row that is not all NaN and has a date-like string
            # FRED files usually have 10 rows of headers. We'll skip them dynamically.
            df = pd.read_excel(filename, skiprows=10)
            
            # Identify columns by type
            # We look for the first column that looks like a date and the first that looks like a number
            date_col = None
            val_col = None
            
            for col in df.columns:
                # Try to convert to numeric to see if it's the data column
                converted_val = pd.to_numeric(df[col], errors='coerce')
                if converted_val.notna().sum() > 10: # If it has more than 10 numbers, it's our value col
                    val_col = col
                
                # Try to convert to date
                try:
                    converted_date = pd.to_datetime(df[col], errors='coerce')
                    if converted_date.notna().sum() > 10:
                        date_col = col
                except:
                    continue
            
            # Clean and return
            df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            return df.dropna(subset=[val_col, date_col])[[date_col, val_col]].rename(columns={date_col: 'date', val_col: 'val'})

        inr = scrape_fred_file('DEXINUS.xlsx')
        gbp = scrape_fred_file('DEXUSUK.xlsx')
        sgd = scrape_fred_file('AEXSIUS.xlsx')
        
        return df_macro, inr, gbp, sgd, None
    except Exception as e:
        return None, None, None, None, str(e)

df_macro, df_inr, df_gbp, df_sgd, error_msg = load_and_clean_data()

# --- 3. ANALYTICS ---
if error_msg:
    st.error(f"🛠️ Terminal Error: {error_msg}")
    st.stop()

st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 External Toggles")
fx_shock = st.sidebar.slider("FX Depreciation (%)", 0.0, 15.0, 0.0)
beta = st.sidebar.slider("Pass-through (Beta)", 0.0, 1.0, 0.2)

st.sidebar.divider()
st.sidebar.subheader("🏗️ Domestic Calibration")
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

# Rule Logic
fair_value = r_star + latest_macro[m['cpi']] + 1.5*(latest_macro[m['cpi']] - 2.0) + (fx_shock * beta)
gap = (fair_value - latest_macro[m['rate']]) * 100

# --- 4. DISPLAY ---
st.title(f"{market} Surveillance Terminal")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest FX Rate", f"{latest_fx['val']:.2f}")
c2.metric("Headline CPI", f"{latest_macro[m['cpi']]:.2f}%")
c3.metric("Taylor Fair Value", f"{fair_value:.2f}%")
c4.metric("Action Gap", f"{gap:+.0f} bps", delta_color="inverse")

# Dual Axis Graph
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate (%)", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=m['fx']['date'], y=m['fx']['val'], name="Historical FX", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    yaxis=dict(title="Policy Rate (%)"),
    yaxis2=dict(title="FX Rate (vs USD)", overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("🎓 Concepts Used & Lessons Learnt")
st.write("""
- **Open-Economy Taylor Rule:** Extension of standard monetary policy models to include FX risk premiums for EM stability.
- **Data Pipeline Orchestration:** Developed a custom 'Brute Force' scanner to clean disparate Excel formats from FRED and central banks.
- **Policy Sensitivity:** Real-time simulation of FX pass-through effects on domestic price stability.
""")
