import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- 1. SETTINGS & UI ---
st.set_page_config(page_title="Macro FX Terminal v6.3", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stWidgetLabel"] p, label p, h1, h2, h3 {
        color: #333333 !important; font-weight: 800 !important;
    }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #D1C7B7; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEARCH & RESCUE DATA ENGINE ---
@st.cache_data
def load_all_macro_data():
    try:
        # Load Main Macro File
        df_macro = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        
        def robust_fred_load(filename):
            # Load the raw file to scan for the data start
            raw = pd.read_excel(filename, header=None)
            
            # Search for the row where the first column is a date
            start_row = 0
            for i in range(len(raw)):
                val = raw.iloc[i, 0]
                try:
                    if isinstance(pd.to_datetime(val), (pd.Timestamp, datetime)):
                        # We found a date row! Usually, the header is the row ABOVE this.
                        start_row = i - 1 if i > 0 else 0
                        break
                except:
                    continue
            
            # Reload with the identified header row
            df_final = pd.read_excel(filename, skiprows=start_row)
            
            # Standardize columns: Col 0 is Date, Col 1 is the Rate
            df_final.columns = ['observation_date', 'rate_val']
            
            # Final Cleaning: Force numeric and drop empty rows
            df_final['rate_val'] = pd.to_numeric(df_final['rate_val'], errors='coerce')
            df_final['observation_date'] = pd.to_datetime(df_final['observation_date'], errors='coerce')
            return df_final.dropna(subset=['rate_val', 'observation_date'])

        # Load all FX files using the scanner
        inr = robust_fred_load('DEXINUS.xlsx')
        gbp = robust_fred_load('DEXUSUK.xlsx')
        sgd = robust_fred_load('AEXSIUS.xlsx')
        
        return df_macro, inr, gbp, sgd, None
    except Exception as e:
        return None, None, None, None, str(e)

from datetime import datetime
df_macro, df_inr, df_gbp, df_sgd, error_msg = load_all_macro_data()

# --- 3. DASHBOARD LOGIC ---
if error_msg:
    st.error(f"🛠️ **Terminal Offline:** {error_msg}")
    st.info("Files found in root: " + str(os.listdir('.')))
    st.stop()

st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

# External Controls
st.sidebar.divider()
st.sidebar.subheader("🌍 FX Stability Simulation")
fx_shock = st.sidebar.slider("Simulate FX Depreciation (%)", 0.0, 15.0, 0.0)
pass_through = st.sidebar.slider("Pass-through Beta (FX -> Rates)", 0.0, 1.0, 0.2)

# Domestic Controls
st.sidebar.divider()
st.sidebar.subheader("🏗️ Domestic Target")
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)

# Mapping Data
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx": df_inr},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx": df_gbp},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx": df_sgd}
}

m = m_map[market]
fx_df = m['fx']
latest_macro = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
latest_fx = fx_df.iloc[-1]

# Calculations
base_inf = latest_macro[m['cpi']]
curr_rate = latest_macro[m['rate']]
fx_val = latest_fx['rate_val']

# Open Economy Taylor Rule
# Fair Value = r* + Inf + 1.5*(Inf - 2%) + (FX Pressure)
fair_value = r_star + base_inf + 1.5*(base_inf - 2.0) + (fx_shock * pass_through)
gap_bps = (fair_value - curr_rate) * 100

# --- 4. DISPLAY ---
st.title(f"{market} Policy Surveillance Terminal")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current FX Rate", f"{fx_val:.2f}")
c2.metric("Headline CPI", f"{base_inf:.2f}%")
c3.metric("Taylor Fair Value", f"{fair_value:.2f}%")
c4.metric("Action Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

# Dual Axis Visualization
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate (%)", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=fx_df['observation_date'], y=fx_df['rate_val'], 
                         name="Historical FX", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    yaxis=dict(title="Policy Rate (%)"),
    yaxis2=dict(title="FX Rate (vs USD)", overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig, use_container_width=True)

# Footer Education for MAS
st.divider()
st.subheader("💡 Terminal Insights")
st.write(f"""
* The **Action Gap** of **{gap_bps:+.0f} bps** suggests that based on current inflation and simulated FX shocks, the {market} policy rate is 
{"under-tightened" if gap_bps > 0 else "appropriately set or over-tightened"} relative to the Taylor Rule benchmark.
* **Currency Pass-Through:** A {fx_shock}% shock adds **{fx_shock * pass_through:.2f}%** to the necessary interest rate buffer to maintain capital stability.
""")
