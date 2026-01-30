import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. DATA ENGINE (High-Fidelity Terminal Standard) ---
@st.cache_data
def load_and_process_intelligence():
    try:
        # Load sheets directly from Excel
        policy_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Policy_Rate', engine='openpyxl')
        macro_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Macro data', engine='openpyxl')
        gdp_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='GDP_Growth', engine='openpyxl')
    except Exception as e:
        st.error(f"System Error: Data source not found. Details: {e}")
        return pd.DataFrame()

    # Reconstruct Policy Dates (Handling the Year-Header layout)
    current_year, cleaned_rows = None, []
    months_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                  'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    
    for _, row in policy_raw.iterrows():
        val = str(row['Date']).strip().split('.')[0]
        if val.isdigit() and len(val) == 4: current_year = int(val)
        elif val in months_map and current_year:
            dt = pd.Timestamp(year=current_year, month=months_map[val], day=1)
            cleaned_rows.append({
                'Date': dt, 
                'Policy_India': row['India'], 
                'Policy_UK': row['UK'], 
                'Policy_Singapore': row['Singapore']
            })
    
    df = pd.DataFrame(cleaned_rows)

    # Clean Macro Data (Ensure Date is datetime)
    macro_raw['Date'] = pd.to_datetime(macro_raw['Date'])
    
    # Process FX (Daily to Monthly Avg)
    def get_fx(file, col, label):
        try:
            f_df = pd.read_excel(file, sheet_name='Daily', engine='openpyxl')
            f_df['observation_date'] = pd.to_datetime(f_df['observation_date'])
            f_df[col] = pd.to_numeric(f_df[col], errors='coerce')
            return f_df.resample('MS', on='observation_date').mean().reset_index().rename(columns={'observation_date': 'Date', col: label})
        except: return pd.DataFrame(columns=['Date', label])

    inr = get_fx('DEXINUS.xlsx', 'DEXINUS', 'USDINR')
    gbp = get_fx('DEXUSUK.xlsx', 'DEXUSUK', 'USDGBP')

    # Merge into Master Intelligence Frame
    df = df.merge(macro_raw, on='Date', how='left')
    df = df.merge(inr, on='Date', how='left').merge(gbp, on='Date', how='left')
    
    return df.sort_values('Date').reset_index(drop=True)

# --- 2. TERMINAL INTERFACE ---
st.set_page_config(page_title="Global Macro Terminal", layout="wide")
df = load_and_process_intelligence()

st.title("🏛️ Global Macro-Financial Intelligence Terminal")
st.caption("Cross-Asset Equilibrium & Monetary Policy Modeling")

# --- 3. ADVANCED SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Terminal Parameters")
    market = st.selectbox("Market Focus", ["India", "UK", "Singapore"])
    
    st.divider()
    st.subheader("Scenario Modeling")
    timeline = st.slider("Analysis Horizon", 2012, 2025, (2018, 2025))
    scenario = st.radio("Policy Bias", ["Neutral", "Hawkish (+75bps)", "Dovish (-75bps)", "Custom"])
    
    custom_adj = 0.0
    if scenario == "Custom":
        custom_adj = st.slider("Manual Rate Adjustment (%)", -3.0, 3.0, 0.0, 0.25)
    
    st.divider()
    st.subheader("Analytical Overlays")
    show_taylor = st.toggle("Overlay Taylor Rule Implied Rate", value=False)
    show_fx_overlay = st.toggle("Overlay FX Spot Rate", value=True)
    
    if st.button("Reset Terminal"):
        st.rerun()

# --- 4. ANALYTICS LOGIC (MAPPING) ---
# Column Mapping based on selection
mapping = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "fx": "USDINR", "fx_name": "INR"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "fx": "USDGBP", "fx_name": "GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "fx": "USDINR", "fx_name": "SGD (Proxy)"}
}

m = mapping[market]
mask = (df['Date'].dt.year >= timeline[0]) & (df['Date'].dt.year <= timeline[1])
p_df = df.loc[mask].copy()

# Apply Scenario Deltas
if scenario == "Hawkish (+75bps)": p_df[m['p']] += 0.75
elif scenario == "Dovish (-75bps)": p_df[m['p']] -= 0.75
elif scenario == "Custom": p_df[m['p']] += custom_adj

# --- 5. CORE VISUALIZATION: MONETARY EQUILIBRIUM ---
st.subheader("I. Monetary Path & Market Pricing")

fig1 = make_subplots(specs=[[{"secondary_y": True}]])

# Primary Axis: Policy Rate
fig1.add_trace(go.Scatter(
    x=p_df['Date'], y=p_df[m['p']], 
    name=f"{market} Policy Rate", 
    line=dict(color='#1f77b4', width=4)
), secondary_y=False)

# Secondary Axis: FX Spot
if show_fx_overlay and m['fx'] in p_df.columns:
    fig1.add_trace(go.Scatter(
        x=p_df['Date'], y=p_df[m['fx']], 
        name=f"USD/{m['fx_name']} Spot", 
        line=dict(color='#ff7f0e', width=2, dash='dot')
    ), secondary_y=True)

# Taylor Rule Overlay
if show_taylor:
    # Rule: Neutral Rate (e.g. 2%) + 0.5*(Inflation - 2%) + 0.5*(Output Gap)
    # Simplified here for the demo
    taylor = 2.5 + 1.5 * (p_df[m['cpi']] - 2.0)
    fig1.add_trace(go.Scatter(
        x=p_df['Date'], y=taylor, 
        name="Taylor Rule (Implied)", 
        line=dict(color='rgba(128, 128, 128, 0.5)', dash='dash')
    ))

fig1.update_layout(height=500, template="plotly_white", hovermode="x unified")
fig1.update_yaxes(title_text="Policy Rate (%)", secondary_y=False)
fig1.update_yaxes(title_text="FX Rate", secondary_y=True)
st.plotly_chart(fig1, use_container_width=True)

# --- 6. MACRO FUNDAMENTALS (CPI & GDP) ---
st.subheader("II. Macroeconomic Fundamentals")
col1, col2 = st.columns(2)

with col1:
    st.write("**Consumer Price Index (YoY % Change)**")
    fig_cpi = go.Figure()
    fig_cpi.add_trace(go.Bar(x=p_df['Date'], y=p_df[m['cpi']], marker_color='cadetblue', name="CPI"))
    fig_cpi.update_layout(height=350, template="plotly_white")
    st.plotly_chart(fig_cpi, use_container_width=True)

with col2:
    st.write("**Institutional Insights**")
    # Quick Correlation Stat
    valid_data = p_df[[m['p'], m['cpi']]].dropna()
    if not valid_data.empty:
        correlation = valid_data.corr().iloc[0, 1]
        st.metric("Policy-Inflation Correlation", f"{round(correlation, 2)}")
    
    st.info("""
    **Transmission Note:** In standard economic theory, a positive correlation suggests the Central Bank is actively chasing inflation (Hawkish stance), while a lag indicates a 'wait-and-see' Dovish approach.
    """)
    
    if st.checkbox("View Real-Time Data Table"):
        st.dataframe(p_df[['Date', m['p'], m['cpi'], m['fx']]].tail(10))

st.divider()
st.caption("Terminal Disclaimer: This dashboard is for analytical purposes and uses resampled daily market data to match monthly macroeconomic reporting cycles.")
