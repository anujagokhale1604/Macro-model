import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. DATA ENGINE (High-Fidelity Excel Integration) ---
@st.cache_data
def load_and_process_intelligence():
    try:
        # Load all relevant sheets from Excel
        policy_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Policy_Rate', engine='openpyxl')
        macro_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Macro data', engine='openpyxl')
        gdp_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='GDP_Growth', engine='openpyxl')
    except Exception as e:
        st.error(f"Data Connection Error: {e}")
        return pd.DataFrame()

    # Workaround for the "Human-Readable" Policy Date format
    current_year, cleaned_rows = None, []
    months_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                  'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    
    for _, row in policy_raw.iterrows():
        val = str(row['Date']).strip().split('.')[0]
        if val.isdigit() and len(val) == 4: current_year = int(val)
        elif val in months_map and current_year:
            dt = pd.Timestamp(year=current_year, month=months_map[val], day=1)
            cleaned_rows.append({'Date': dt, 'Policy_India': row['India'], 'Policy_UK': row['UK'], 'Policy_SG': row['Singapore']})
    
    df_policy = pd.DataFrame(cleaned_rows)

    # Clean Macro Data (CPI)
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

    # Global Merge
    df = df_policy.merge(macro_raw, on='Date', how='left')
    df = df.merge(inr, on='Date', how='left').merge(gbp, on='Date', how='left')
    
    return df.sort_values('Date')

# --- 2. THE TERMINAL UI ---
st.set_page_config(page_title="Global Macro Intelligence", layout="wide")
df = load_and_process_intelligence()

st.title("🏛️ Global Macro-Financial Intelligence Terminal")
st.caption("Central Bank Policy & Market Equilibrium Analysis")

# --- 3. ADVANCED SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Terminal Parameters")
    market = st.selectbox("Market Focus", ["India", "UK", "Singapore"])
    
    st.divider()
    st.subheader("Timeline & Scenarios")
    timeline = st.slider("Analysis Horizon", 2015, 2025, (2018, 2025))
    scenario = st.radio("Monetary Scenario", ["Standard", "Hawkish", "Dovish", "Custom"])
    
    if scenario == "Custom":
        custom_rate = st.slider("Target Policy Rate Adjustment (%)", -2.0, 2.0, 0.0, 0.25)
    
    st.divider()
    st.subheader("Taylor Rule Toggles")
    use_taylor = st.toggle("Overlay Taylor Rule (Implied)", value=False)
    inflation_target = st.number_input("Inflation Target (%)", 0.0, 10.0, 4.0 if market == "India" else 2.0)
    
    if st.button("Reset Terminal"):
        st.rerun()

# --- 4. DATA LOGIC MAPPING ---
# Filter data by timeline
mask = (df['Date'].dt.year >= timeline[0]) & (df['Date'].dt.year <= timeline[1])
plot_df = df.loc[mask].copy()

# Market mapping
if market == "India":
    p_col, cpi_col, fx_col, fx_label = 'Policy_India', 'CPI_India', 'USDINR', 'INR'
elif market == "UK":
    p_col, cpi_col, fx_col, fx_label = 'Policy_UK', 'CPI_UK', 'USDGBP', 'GBP'
else:
    p_col, cpi_col, fx_col, fx_label = 'Policy_SG', 'CPI_Singapore', 'USDINR', 'SGD' # Mocked for SG

# Apply Scenarios to Policy Rate
if scenario == "Hawkish": plot_df[p_col] += 0.75
elif scenario == "Dovish": plot_df[p_col] -= 0.75
elif scenario == "Custom": plot_df[p_col] += custom_rate

# --- 5. VISUALIZATION SUITE ---

# TAB 1: MONETARY & FX EQUILIBRIUM
st.subheader("I. Monetary & Currency Equilibrium")
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df[p_col], name="Policy Rate (%)", line=dict(color='navy', width=3)), secondary_y=False)

if fx_col in plot_df.columns:
    fig1.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df[fx_col], name=f"FX Spot (USD/{fx_label})", line=dict(color='orange', width=2, dash='dot')), secondary_y=True)

if use_taylor:
    # Simplified Taylor: Neutral + 1.5*(CPI - Target)
    taylor_implied = 4.0 + 1.5 * (plot_df[cpi_col] - inflation_target)
    fig1.add_trace(go.Scatter(x=plot_df['Date'], y=taylor_implied, name="Taylor Rule Implied", line=dict(color='gray', dash='dash')))

fig1.update_layout(height=450, template="plotly_white", margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig1, use_container_width=True)

# TAB 2: MACRO FUNDAMENTALS (CPI & GDP)
st.subheader("II. Macroeconomic Fundamentals")
c1, c2 = st.columns(2)

with c1:
    st.write("**Consumer Price Index (YoY)**")
    fig_cpi = go.Figure()
    fig_cpi.add_trace(go.Bar(x=plot_df['Date'], y=plot_df[cpi_col], name="CPI", marker_color='cadetblue'))
    fig_cpi.add_hline(y=inflation_target, line_dash="dash", line_color="red", annotation_text="Target")
    fig_cpi.update_layout(height=350, template="plotly_white")
    st.plotly_chart(fig_cpi, use_container_width=True)

with c2:
    st.write("**Policy Transmission Analysis**")
    # Correlation between Rate and Inflation
    corr = plot_df[[p_col, cpi_col]].corr().iloc[0,1]
    st.metric("Rate-Inflation Correlation", f"{round(corr, 2)}")
    st.caption("Institutional Note: A negative correlation suggests effective monetary tightening against inflationary pressures.")
    
    if st.checkbox("Show Raw Macro Data"):
        st.dataframe(plot_df[['Date', p_col, cpi_col, fx_col]].tail(10))

# --- 6. TERMINAL FOOTNOTES ---
st.divider()
st.info(f"**Analytics Desk:** Viewing {market} Market. Scenarios are calculated using a delta-basis adjustment on the latest reported central bank figures. FX data is resampled from daily high-frequency spot rates to match monthly policy reporting.")
