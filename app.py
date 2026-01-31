import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. THE BEAUTIFICATION ENGINE (Custom CSS) ---
st.set_page_config(page_title="Macro Terminal", layout="wide")

st.markdown("""
    <style>
    /* Professional Serif Font */
    html, body, [class*="css"] {
        font-family: 'Times New Roman', Times, serif;
    }
    
    /* Adaptive Glassmorphism for Notes */
    .stExpander {
        border: 1px solid rgba(150, 150, 150, 0.3) !important;
        border-radius: 10px !important;
        background: rgba(150, 150, 150, 0.05) !important;
    }
    
    /* Metric Card Styling */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #d4af37; /* Gold touch */
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_and_sync_data():
    # Load Macro & Policy
    df = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - Macro data.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Load GDP Growth (Handling the multi-header CSV snippet)
    gdp_raw = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - GDP_Growth.csv', skiprows=1)
    gdp_clean = gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
    gdp_clean.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    gdp_clean['Year'] = pd.to_numeric(gdp_clean['Year'], errors='coerce')
    gdp_clean = gdp_clean.dropna(subset=['Year'])
    
    # Load FX Data
    def process_fx(file, col, label):
        f = pd.read_csv(file)
        f['observation_date'] = pd.to_datetime(f['observation_date'])
        f[col] = pd.to_numeric(f[col], errors='coerce')
        return f.resample('MS', on='observation_date').mean().reset_index().rename(columns={'observation_date': 'Date', col: label})

    fx_inr = process_fx('DEXINUS.xlsx - Daily.csv', 'DEXINUS', 'FX_India')
    fx_gbp = process_fx('DEXUSUK.xlsx - Daily.csv', 'DEXUSUK', 'FX_UK')
    fx_sgd = pd.read_csv('AEXSIUS.xlsx - Annual.csv')
    fx_sgd['Year'] = pd.to_datetime(fx_sgd['observation_date']).dt.year
    
    # Global Join
    df['Year'] = df['Date'].dt.year
    df = df.merge(gdp_clean, on='Year', how='left')
    df = df.merge(fx_inr, on='Date', how='left').merge(fx_gbp, on='Date', how='left')
    df = df.merge(fx_sgd[['Year', 'AEXSIUS']], on='Year', how='left').rename(columns={'AEXSIUS': 'FX_Singapore'})
    
    return df.sort_values('Date')

df = load_and_sync_data()

# --- 3. SIDEBAR: NAVIGATION & SCENARIOS ---
with st.sidebar:
    st.header("🏛️ Research Parameters")
    market = st.selectbox("Market Focus", ["India", "UK", "Singapore"])
    
    st.divider()
    st.subheader("📅 Time Horizon")
    horizon = st.radio("Lookback Period", ["Historical", "10 Years", "5 Years"])
    
    st.divider()
    st.subheader("🌋 Macro Scenarios")
    scenario_mode = st.selectbox("Environment Simulation", 
                               ["Standard", "Stagflation", "Depression", "Economic Boom", "Custom"])
    
    # Customization Overrides
    if scenario_mode == "Custom":
        c_cpi = st.slider("CPI Adjustment (%)", -5.0, 10.0, 0.0)
        c_gdp = st.slider("GDP Adjustment (%)", -10.0, 5.0, 0.0)
        c_rate = st.slider("Policy Shift (bps)", -300, 300, 0) / 100
    else:
        c_cpi, c_gdp, c_rate = 0.0, 0.0, 0.0

# --- 4. SCENARIO CALCULATIONS ---
mapping = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "ccy": "INR"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "ccy": "GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "ccy": "SGD"}
}
m = mapping[market]

# Apply Time Filter
max_date = df['Date'].max()
if horizon == "5 Years":
    p_df = df[df['Date'] >= (max_date - pd.DateOffset(years=5))].copy()
elif horizon == "10 Years":
    p_df = df[df['Date'] >= (max_date - pd.DateOffset(years=10))].copy()
else:
    p_df = df.copy()

# Apply Scenario Logic
if scenario_mode == "Stagflation":
    p_df[m['cpi']] += 4.5
    p_df[m['gdp']] -= 3.0
elif scenario_mode == "Depression":
    p_df[m['gdp']] -= 8.0
    p_df[m['cpi']] -= 2.0
elif scenario_mode == "Economic Boom":
    p_df[m['gdp']] += 3.5
    p_df[m['cpi']] += 1.0
elif scenario_mode == "Custom":
    p_df[m['cpi']] += c_cpi
    p_df[m['gdp']] += c_gdp
    p_df[m['p']] += c_rate

# --- 5. DASHBOARD LAYOUT ---
st.title(f"🏛️ {market} Macro Intelligence Report")
st.markdown(f"**Current Scenario:** {scenario_mode} | **Horizon:** {horizon}")

# Top Metrics Row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Policy Rate", f"{p_df[m['p']].iloc[-1]:.2f}%")
c2.metric("Inflation (YoY)", f"{p_df[m['cpi']].iloc[-1]:.2f}%")
c3.metric("GDP Growth", f"{p_df[m['gdp']].iloc[-1]:.2f}%")
c4.metric("FX Spot", f"{p_df[m['fx']].iloc[-1]:.2f}")

# Main Chart: Policy & Market Equilibrium
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Policy Rate", line=dict(color='#003366', width=3)), secondary_y=False)

# Taylor Rule Overlay
taylor = 2.5 + p_df[m['cpi']] + 0.5 * (p_df[m['cpi']] - 2.0)
fig1.add_trace(go.Scatter(x=p_df['Date'], y=taylor, name="Taylor Rule", line=dict(color='gray', dash='dash', width=1.5)), secondary_y=False)

# FX Overlay
fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name=f"FX ({m['ccy']}/USD)", line=dict(color='#E67E22', width=2)), secondary_y=True)

fig1.update_layout(height=450, template="none", hovermode="x unified", legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig1, use_container_width=True)

# Fundamental Chart: GDP Growth Data
st.subheader("📉 Growth & Price Dynamics")
fig2 = go.Figure()
fig2.add_trace(go.Bar(x=p_df['Date'], y=p_df[m['cpi']], name="CPI (YoY)", marker_color='rgba(46, 134, 193, 0.6)'))
fig2.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['gdp']], name="Annual GDP Growth", line=dict(color='#1D8348', width=4)))

fig2.update_layout(height=400, template="none", barmode='overlay')
st.plotly_chart(fig2, use_container_width=True)

# --- 6. NOTES: EXPLANATORY & METHODICAL ---
st.divider()
st.subheader("📚 Research Documentation")

exp_col, meth_col = st.columns(2)

with exp_col:
    st.info("### 💡 Explanatory Note")
    st.write(f"""
    **Context:** This terminal tracks {market}'s monetary health. 
    By toggling scenarios, you are viewing how exogenous shocks (like **{scenario_mode}**) 
    stress-test current interest rate levels.
    
    * **Policy Rate:** The cost of borrowing set by the central bank.
    * **FX Spot:** The market value of the {m['ccy']} against the USD.
    * **Taylor Rule:** A theoretical benchmark for where rates *should* be to control inflation.
    """)

with meth_col:
    st.success("### 🧪 Methodical Note")
    st.write(f"""
    **Calculation Framework:**
    - **Data Sync:** Monthly CPI and Policy rates are harmonized with Daily FX averages.
    - **Taylor Rule Formula:** $i = r + \pi + 0.5(\pi - 2.0)$, where $r$ is the neutral rate.
    - **Growth Modeling:** GDP data is annual growth (%) mapped across the historical timeline.
    - **Scenario Math:** Stagflation assumes a +450bps inflation shock and -300bps GDP shock.
    """)

st.divider()
st.caption("Terminal v3.0 | Quantitative Macro Framework | Times New Roman Institutional Style")
