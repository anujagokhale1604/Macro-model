import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. DATA ENGINE (High-Fidelity Terminal Standard) ---
@st.cache_data
def load_data():
    try:
        # Load sheets directly from Excel
        policy_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Policy_Rate', engine='openpyxl')
        macro_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Macro data', engine='openpyxl')
        gdp_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='GDP_Growth', engine='openpyxl')
    except Exception as e:
        st.error(f"System Error: Source files not found. {e}")
        return pd.DataFrame()

    # Reconstruct Policy Dates from the 'Year-Header' Excel format
    current_year, cleaned_rows = None, []
    months_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                  'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    
    for _, row in policy_raw.iterrows():
        val = str(row['Date']).strip().split('.')[0]
        if val.isdigit() and len(val) == 4: 
            current_year = int(val)
        elif val in months_map and current_year:
            dt = pd.Timestamp(year=current_year, month=months_map[val], day=1)
            cleaned_rows.append({
                'Date': dt, 
                'Policy_India': row['India'], 
                'Policy_UK': row['UK'], 
                'Policy_Singapore': row['Singapore']
            })
    
    df_policy = pd.DataFrame(cleaned_rows)
    macro_raw['Date'] = pd.to_datetime(macro_raw['Date'])

    # Process FX Daily to Monthly Average
    def get_fx(file, col, label):
        try:
            f_df = pd.read_excel(file, sheet_name='Daily', engine='openpyxl')
            f_df['observation_date'] = pd.to_datetime(f_df['observation_date'])
            f_df[col] = pd.to_numeric(f_df[col], errors='coerce')
            return f_df.resample('MS', on='observation_date').mean().reset_index().rename(columns={'observation_date': 'Date', col: label})
        except: return pd.DataFrame(columns=['Date', label])

    inr = get_fx('DEXINUS.xlsx', 'DEXINUS', 'USDINR')
    gbp = get_fx('DEXUSUK.xlsx', 'DEXUSUK', 'USDGBP')

    # Global Join
    master = df_policy.merge(macro_raw, on='Date', how='left')
    master = master.merge(inr, on='Date', how='left').merge(gbp, on='Date', how='left')
    
    return master.sort_values('Date').reset_index(drop=True)

# --- 2. INTERFACE SETUP ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide")
df = load_data()

st.title("🏛️ Global Macro-Financial Intelligence Terminal")
st.caption("Quantitative Policy Analysis & Market Equilibrium Dashboard")

# --- 3. SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Terminal Parameters")
    market = st.selectbox("Market Selection", ["India", "UK", "Singapore"])
    
    st.divider()
    st.subheader("Monetary Scenarios")
    timeline = st.slider("Horizon", 2012, 2025, (2018, 2025))
    scenario = st.radio("Policy Stance", ["Neutral", "Hawkish (+75bps)", "Dovish (-75bps)", "Custom Adjustment"])
    
    custom_val = 0.0
    if scenario == "Custom Adjustment":
        custom_val = st.slider("Delta (%)", -3.0, 3.0, 0.0, 0.25)
    
    st.divider()
    st.subheader("Model Overlays")
    show_taylor = st.toggle("Taylor Rule (Implied)", value=False)
    show_fx = st.toggle("FX Spot Overlay", value=True)
    show_gdp = st.toggle("Show GDP Context", value=True)
    
    if st.button("Reset Terminal"):
        st.rerun()

# --- 4. ANALYTICS MAPPING & SCENARIOS ---
# FIXED: Mapping now matches the cleaning logic exactly
mapping = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "fx": "USDINR", "fx_label": "INR"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "fx": "USDGBP", "fx_label": "GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "fx": "USDINR", "fx_label": "SGD (Proxy)"}
}

m = mapping[market]
mask = (df['Date'].dt.year >= timeline[0]) & (df['Date'].dt.year <= timeline[1])
p_df = df.loc[mask].copy()

# Apply Scenario Logic
if scenario == "Hawkish (+75bps)": p_df[m['p']] += 0.75
elif scenario == "Dovish (-75bps)": p_df[m['p']] -= 0.75
elif scenario == "Custom Adjustment": p_df[m['p']] += custom_val

# --- 5. VISUALIZATION SUITE ---

# GRAPH 1: MONETARY & FX EQUILIBRIUM
st.subheader("I. Monetary Policy & Currency Equilibrium")
fig1 = make_subplots(specs=[[{"secondary_y": True}]])

# Policy Rate Trace
fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Policy Rate", 
                         line=dict(color='#003366', width=4)), secondary_y=False)

# Taylor Rule Trace
if show_taylor:
    # Rule: Neutral Rate (2.5%) + 1.5*(CPI - Target(2.0%))
    taylor = 2.5 + 1.5 * (p_df[m['cpi']] - 2.0)
    fig1.add_trace(go.Scatter(x=p_df['Date'], y=taylor, name="Taylor Rule Implied", 
                             line=dict(color='gray', dash='dash')))

# FX Trace (Twined on Secondary Y-Axis)
if show_fx and m['fx'] in p_df.columns:
    fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name=f"USD/{m['fx_label']} Spot", 
                             line=dict(color='#E67E22', width=2, dash='dot')), secondary_y=True)

fig1.update_layout(height=500, template="plotly_white", hovermode="x unified")
fig1.update_yaxes(title_text="Policy Rate (%)", secondary_y=False)
fig1.update_yaxes(title_text="Exchange Rate", secondary_y=True)
st.plotly_chart(fig1, use_container_width=True)

# GRAPH 2: MACRO FUNDAMENTALS (CPI & GDP)
st.subheader("II. Macroeconomic Fundamentals")
col_left, col_right = st.columns(2)

with col_left:
    st.write("**Consumer Price Index (YoY %)**")
    fig_cpi = go.Figure()
    fig_cpi.add_trace(go.Bar(x=p_df['Date'], y=p_df[m['cpi']], marker_color='#2E86C1', name="CPI"))
    fig_cpi.update_layout(height=350, template="plotly_white")
    st.plotly_chart(fig_cpi, use_container_width=True)

with col_right:
    st.write("**Institutional Analysis Desk**")
    # Quick Correlation Stat
    valid_data = p_df[[m['p'], m['cpi']]].dropna()
    if not valid_data.empty:
        correlation = valid_data.corr().iloc[0, 1]
        st.metric("Policy-Inflation Correlation", f"{round(correlation, 2)}")
    
    st.info(f"**Current Analysis:** The {market} market correlation of {round(correlation, 2)} suggests the responsiveness of the central bank to price stability.")
    
    if st.checkbox("Show Terminal Data Table"):
        st.dataframe(p_df[['Date', m['p'], m['cpi'], m['fx']]].tail(10))

st.divider()
st.caption("Terminal Note: This dashboard is optimized for institutional research. Scenarios are delta-basis adjustments; FX data is resampled to match monthly reporting cycles.")
