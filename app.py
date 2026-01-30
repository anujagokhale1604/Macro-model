import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. DATA ENGINE (High-Fidelity Terminal Standard) ---
@st.cache_data
def load_data():
    try:
        # Standardize loading: Reading directly from Excel sheets
        policy_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Policy_Rate', engine='openpyxl')
        macro_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Macro data', engine='openpyxl')
    except Exception as e:
        st.error(f"System Error: Data source not found. {e}")
        return pd.DataFrame()

    # RECONSTRUCT POLICY DATES (Fixing the Year-Header layout)
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

    # PROCESS FX: Daily to Monthly Average
    def get_fx(file, col, label):
        try:
            f_df = pd.read_excel(file, sheet_name='Daily', engine='openpyxl')
            f_df['observation_date'] = pd.to_datetime(f_df['observation_date'])
            f_df[col] = pd.to_numeric(f_df[col], errors='coerce')
            return f_df.resample('MS', on='observation_date').mean().reset_index().rename(columns={'observation_date': 'Date', col: label})
        except: return pd.DataFrame(columns=['Date', label])

    inr = get_fx('DEXINUS.xlsx', 'DEXINUS', 'USDINR')
    gbp = get_fx('DEXUSUK.xlsx', 'DEXUSUK', 'USDGBP')

    # GLOBAL JOIN (Merge Policy, CPI, and FX)
    master = df_policy.merge(macro_raw, on='Date', how='left')
    master = master.merge(inr, on='Date', how='left').merge(gbp, on='Date', how='left')
    
    return master.sort_values('Date').reset_index(drop=True)

# --- 2. INTERFACE SETUP ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide")
df = load_data()

st.title("🏛️ Global Macro-Financial Intelligence Terminal")
st.caption("Quantitative Policy Analysis & Market Equilibrium Dashboard")

# --- 3. INSTITUTIONAL SIDEBAR ---
with st.sidebar:
    st.header("Terminal Parameters")
    market = st.selectbox("Market Selection", ["India", "UK", "Singapore"])
    
    st.divider()
    st.subheader("Monetary Scenarios")
    timeline = st.slider("Analysis Horizon", 2012, 2025, (2018, 2025))
    scenario = st.radio("Policy Stance", ["Neutral", "Hawkish (+75bps)", "Dovish (-75bps)", "Custom Adjustment"])
    
    custom_val = 0.0
    if scenario == "Custom Adjustment":
        custom_val = st.slider("Delta (%)", -3.0, 3.0, 0.0, 0.25)
    
    st.divider()
    st.subheader("Analytical Toggles")
    show_taylor = st.toggle("Taylor Rule (Implied)", value=False)
    show_fx_sep = st.toggle("Separate FX Market Analysis", value=True)
    
    if st.button("Reset Terminal"):
        st.rerun()

# --- 4. ANALYTICS MAPPING & LOGIC ---
# This mapping prevents the KeyError by explicitly matching the cleaned columns
mapping = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "fx": "USDINR", "fx_label": "INR"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "fx": "USDGBP", "fx_label": "GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "fx": "USDINR", "fx_label": "SGD (Proxy)"}
}

m = mapping[market]
mask = (df['Date'].dt.year >= timeline[0]) & (df['Date'].dt.year <= timeline[1])
p_df = df.loc[mask].copy()

# Apply Scenario Logic (Shifting the Curve)
if scenario == "Hawkish (+75bps)": p_df[m['p']] += 0.75
elif scenario == "Dovish (-75bps)": p_df[m['p']] -= 0.75
elif scenario == "Custom Adjustment": p_df[m['p']] += custom_val

# --- 5. VISUALIZATION SUITE ---

# GRAPH 1: POLICY & FUNDAMENTALS
st.subheader("I. Monetary Policy & Inflation Path")
fig1 = go.Figure()

# Policy Rate Trace
fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name=f"{market} Policy Rate", 
                         line=dict(color='#003366', width=4)))

# CPI Trace
fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['cpi']], name="CPI (YoY%)", 
                         line=dict(color='#2E86C1', width=2, dash='dot')))

# Taylor Rule Overlay
if show_taylor:
    # Rule: Neutral Rate (2.5) + 1.5*(CPI - Target(2.0))
    taylor = 2.5 + 1.5 * (p_df[m['cpi']] - 2.0)
    fig1.add_trace(go.Scatter(x=p_df['Date'], y=taylor, name="Taylor Implied Rate", 
                             line=dict(color='rgba(128, 128, 128, 0.5)', dash='dash')))

fig1.update_layout(height=500, template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig1, use_container_width=True)

# GRAPH 2: FX MARKET ANALYSIS (SEPARATE GRAPH)
if show_fx_sep:
    st.subheader(f"II. Foreign Exchange Market (USD/{m['fx_label']})")
    fig_fx = go.Figure()
    fig_fx.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name="FX Spot Rate", 
                               line=dict(color='#E67E22', width=3)))
    fig_fx.update_layout(height=400, template="plotly_white", 
                        yaxis_title=f"Units of {m['fx_label']} per USD")
    st.plotly_chart(fig_fx, use_container_width=True)

# SECTION 3: INSTITUTIONAL ANALYTICS
st.subheader("III. Intelligence Summary")
c1, c2, c3 = st.columns(3)

with c1:
    st.write("**Correlation: Rate vs Inflation**")
    corr = p_df[[m['p'], m['cpi']]].corr().iloc[0,1]
    st.metric("Transmission Strength", f"{round(corr, 2)}", help="Measures effectiveness of policy tightening.")

with c2:
    st.write("**Scenario Impact**")
    current_r = p_df[m['p']].iloc[-1]
    st.metric("Terminal Rate (Projected)", f"{round(current_r, 2)}%", f"{scenario}")

with c3:
    if st.checkbox("Export Terminal Data"):
        st.dataframe(p_df[['Date', m['p'], m['cpi'], m['fx']]].tail(12))

st.divider()
st.info("**Analytical Note:** This terminal reconciles human-readable central bank datasets with daily high-frequency spot rates via algorithmic resampling.")
