import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. DATA ENGINE (Standardized Mapping) ---
@st.cache_data
def load_and_sync_data():
    # Load primary macro data
    df = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - Macro data.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Load and clean GDP data (handling the non-standard header)
    gdp_raw = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - GDP_Growth.csv', skiprows=1)
    # The snippet suggests: Col 0: Year, Col 2: IND, Col 3: SGP, Col 4: GBR
    gdp_clean = gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
    gdp_clean.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    gdp_clean['Year'] = pd.to_numeric(gdp_clean['Year'], errors='coerce')
    gdp_clean = gdp_clean.dropna(subset=['Year'])
    
    # Load FX Data
    def process_fx(filename, col_name, new_name):
        try:
            f = pd.read_csv(filename)
            f['observation_date'] = pd.to_datetime(f['observation_date'])
            f[col_name] = pd.to_numeric(f[col_name], errors='coerce')
            # Resample to monthly to match macro data
            f_m = f.resample('MS', on='observation_date').mean().reset_index()
            return f_m.rename(columns={'observation_date': 'Date', col_name: new_name})
        except:
            return pd.DataFrame(columns=['Date', new_name])

    fx_inr = process_fx('DEXINUS.xlsx - Daily.csv', 'DEXINUS', 'FX_India')
    fx_gbp = process_fx('DEXUSUK.xlsx - Daily.csv', 'DEXUSUK', 'FX_UK')
    fx_sgd = pd.read_csv('AEXSIUS.xlsx - Annual.csv')
    fx_sgd['observation_date'] = pd.to_datetime(fx_sgd['observation_date'])
    fx_sgd = fx_sgd.rename(columns={'observation_date': 'Date', 'AEXSIUS': 'FX_Singapore'})

    # Merge everything into one Master Frame
    df['Year'] = df['Date'].dt.year
    df = df.merge(gdp_clean, on='Year', how='left')
    df = df.merge(fx_inr, on='Date', how='left')
    df = df.merge(fx_gbp, on='Date', how='left')
    df = df.merge(fx_sgd[['Date', 'FX_Singapore']], on='Date', how='left')
    
    return df.sort_values('Date')

# --- 2. TERMINAL INTERFACE ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide")
df = load_and_sync_data()

st.title("🏛️ Global Macro-Financial Intelligence Terminal")
st.caption("Quantitative Policy Analysis & Market Equilibrium Dashboard")

# --- 3. SIDEBAR CONTROLS (Restored Original Toggles) ---
with st.sidebar:
    st.header("Terminal Parameters")
    market = st.selectbox("Market Selection", ["India", "UK", "Singapore"])
    
    st.divider()
    st.subheader("Scenario Modeling")
    timeline = st.slider("Horizon", int(df['Date'].dt.year.min()), int(df['Date'].dt.year.max()), (2018, 2024))
    scenario = st.radio("Policy Bias", ["Neutral", "Hawkish (+75bps)", "Dovish (-75bps)", "Custom Adjustment"])
    
    custom_val = 0.0
    if scenario == "Custom Adjustment":
        custom_val = st.slider("Manual Adjustment (%)", -3.0, 3.0, 0.0, 0.25)
    
    st.divider()
    st.subheader("Analytical Overlays")
    show_taylor = st.toggle("Overlay Taylor Rule (Implied)", value=False)
    show_fx = st.toggle("Overlay FX Spot Rate", value=True)
    show_gdp = st.toggle("Show GDP Context", value=True)
    
    if st.button("Reset Terminal"):
        st.rerun()

# --- 4. ANALYTICS LOGIC (Safe Column Mapping) ---
mapping = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "fx_label": "USD/INR"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "fx_label": "GBP/USD"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "fx_label": "USD/SGD"}
}

m = mapping[market]
mask = (df['Date'].dt.year >= timeline[0]) & (df['Date'].dt.year <= timeline[1])
p_df = df.loc[mask].copy()

# Apply Scenario Logic
if scenario == "Hawkish (+75bps)": p_df[m['p']] += 0.75
elif scenario == "Dovish (-75bps)": p_df[m['p']] -= 0.75
elif scenario == "Custom Adjustment": p_df[m['p']] += custom_val

# --- 5. VISUALIZATION SUITE ---

# GRAPH 1: MONETARY EQUILIBRIUM (Entwined Policy & FX)
st.subheader("I. Monetary Path & Currency Equilibrium")
fig1 = make_subplots(specs=[[{"secondary_y": True}]])

# Policy Rate
fig1.add_trace(go.Scatter(
    x=p_df['Date'], y=p_df[m['p']], 
    name="Policy Rate (%)", 
    line=dict(color='#003366', width=4)
), secondary_y=False)

# Taylor Rule Overlay
if show_taylor:
    # Simplified Taylor: 2.0 (Neutral) + CPI + 0.5*(CPI - 2.0)
    taylor_rate = 2.0 + p_df[m['cpi']] + 0.5 * (p_df[m['cpi']] - 2.0)
    fig1.add_trace(go.Scatter(
        x=p_df['Date'], y=taylor_rate, 
        name="Taylor Implied", 
        line=dict(color='gray', dash='dash')
    ), secondary_y=False)

# FX Overlay (Secondary Axis)
if show_fx and not p_df[m['fx']].isnull().all():
    fig1.add_trace(go.Scatter(
        x=p_df['Date'], y=p_df[m['fx']], 
        name=f"FX Spot ({m['fx_label']})", 
        line=dict(color='#E67E22', width=2, dash='dot')
    ), secondary_y=True)

fig1.update_layout(height=500, template="plotly_white", hovermode="x unified")
fig1.update_yaxes(title_text="Policy Rate (%)", secondary_y=False)
fig1.update_yaxes(title_text=f"FX Rate ({m['fx_label']})", secondary_y=True)
st.plotly_chart(fig1, use_container_width=True)

# GRAPH 2: MACRO FUNDAMENTALS (CPI & GDP)
st.subheader("II. Macroeconomic Fundamentals")
col1, col2 = st.columns(2)

with col1:
    st.write("**Consumer Price Index (YoY %)**")
    fig_cpi = go.Figure()
    fig_cpi.add_trace(go.Bar(x=p_df['Date'], y=p_df[m['cpi']], marker_color='#2E86C1', name="CPI"))
    fig_cpi.update_layout(height=350, template="plotly_white", margin=dict(t=20))
    st.plotly_chart(fig_cpi, use_container_width=True)

with col2:
    if show_gdp:
        st.write("**Annual GDP Growth (%)**")
        fig_gdp = go.Figure()
        # GDP is annual, so we take unique years for the bar chart
        gdp_disp = p_df.drop_duplicates('Year')
        fig_gdp.add_trace(go.Bar(x=gdp_disp['Year'], y=gdp_disp[m['gdp']], marker_color='#1D8348', name="GDP"))
        fig_gdp.update_layout(height=350, template="plotly_white", margin=dict(t=20))
        st.plotly_chart(fig_gdp, use_container_width=True)
    else:
        st.info("GDP context is currently hidden. Toggle 'Show GDP Context' in the sidebar to view institutional growth data.")

st.divider()
st.caption("Terminal Data Note: Monthly values for Policy and CPI are sourced from the EM Macro dataset. FX rates are resampled monthly averages. GDP data is annual institutional reporting.")
