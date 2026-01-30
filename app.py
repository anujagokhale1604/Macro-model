import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. DATA ENGINE (Optimized for Excel) ---
@st.cache_data
def load_and_sync_data():
    try:
        # Load Primary Macro & Policy Data
        df_macro = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Macro data')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        
        # Load and clean GDP data (Annual)
        gdp_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='GDP_Growth', skiprows=1)
        # Identifying columns based on your file structure: Year, IND, SGP, GBR
        gdp_clean = gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
        gdp_clean.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        gdp_clean['Year'] = pd.to_numeric(gdp_clean['Year'], errors='coerce')
        gdp_clean = gdp_clean.dropna(subset=['Year'])
        
        # Load FX Data (Daily sheets converted to Monthly averages)
        def process_fx_xlsx(filename, col_name, new_name):
            try:
                f = pd.read_excel(filename, sheet_name='Daily')
                f['observation_date'] = pd.to_datetime(f['observation_date'])
                f[col_name] = pd.to_numeric(f[col_name], errors='coerce')
                # Align daily FX to monthly macro dates
                f_m = f.resample('MS', on='observation_date').mean().reset_index()
                return f_m.rename(columns={'observation_date': 'Date', col_name: new_name})
            except:
                return pd.DataFrame(columns=['Date', new_name])

        fx_inr = process_fx_xlsx('DEXINUS.xlsx', 'Daily')
        fx_gbp = process_fx_xlsx('DEXUSUK.xlsx', 'Daily')
        
        # Global Join
        df_macro['Year'] = df_macro['Date'].dt.year
        df = df_macro.merge(gdp_clean, on='Year', how='left')
        df = df.merge(fx_inr.rename(columns={'DEXINUS': 'FX_India'}), on='Date', how='left')
        df = df.merge(fx_gbp.rename(columns={'DEXUSUK': 'FX_UK'}), on='Date', how='left')
        
        # Singapore FX (Annual data)
        fx_sgd = pd.read_excel('AEXSIUS.xlsx', sheet_name='Annual')
        fx_sgd['Year'] = pd.to_datetime(fx_sgd['observation_date']).dt.year
        df = df.merge(fx_sgd[['Year', 'AEXSIUS']], on='Year', how='left').rename(columns={'AEXSIUS': 'FX_Singapore'})
        
        return df.sort_values('Date')
    
    except Exception as e:
        st.error(f"Operational Error: {e}. Ensure all XLSX files are in the repository.")
        return pd.DataFrame()

# --- 2. INTERFACE SETUP ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide")
df = load_and_sync_data()

if not df.empty:
    st.title("🏛️ Global Macro-Financial Intelligence Terminal")
    st.caption("Quantitative Policy Analysis & Market Equilibrium Dashboard")

    # --- 3. SIDEBAR CONTROLS ---
    with st.sidebar:
        st.header("Terminal Parameters")
        market = st.selectbox("Market Selection", ["India", "UK", "Singapore"])
        
        st.divider()
        st.subheader("Scenario Modeling")
        min_y, max_y = int(df['Date'].dt.year.min()), int(df['Date'].dt.year.max())
        timeline = st.slider("Horizon", min_y, max_y, (2015, max_y))
        
        scenario = st.radio("Policy Bias", ["Neutral", "Hawkish (+75bps)", "Dovish (-75bps)"])
        
        st.divider()
        st.subheader("Analytical Toggles")
        show_taylor = st.toggle("Overlay Taylor Rule (Implied)", value=False)
        show_fx = st.toggle("Overlay FX Spot Rate", value=True)
        show_gdp = st.toggle("Show GDP Context", value=True)

    # --- 4. MAPPING & SCENARIO LOGIC ---
    mapping = {
        "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "label": "INR"},
        "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "label": "GBP"},
        "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "label": "SGD"}
    }

    m = mapping[market]
    p_df = df[(df['Date'].dt.year >= timeline[0]) & (df['Date'].dt.year <= timeline[1])].copy()

    # Apply Shocks to Policy Column
    if scenario == "Hawkish (+75bps)": p_df[m['p']] += 0.75
    elif scenario == "Dovish (-75bps)": p_df[m['p']] -= 0.75

    # --- 5. CORE ANALYSIS: MONETARY EQUILIBRIUM ---
    st.subheader("I. Monetary Path & Market Equilibrium")
    
    # Dual Axis: Policy Rate vs FX
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])

    # Trace: Policy Rate
    fig1.add_trace(go.Scatter(
        x=p_df['Date'], y=p_df[m['p']], 
        name="Policy Rate (%)", 
        line=dict(color='#003366', width=4)
    ), secondary_y=False)

    # Trace: Taylor Rule (Implied)
    if show_taylor:
        # Rule: 2.5 (Neutral Rate) + CPI + 0.5 * (CPI - 2.0 Target)
        taylor = 2.5 + p_df[m['cpi']] + 0.5 * (p_df[m['cpi']] - 2.0)
        fig1.add_trace(go.Scatter(
            x=p_df['Date'], y=taylor, 
            name="Taylor Rule (Implied)", 
            line=dict(color='rgba(128, 128, 128, 0.5)', dash='dash')
        ), secondary_y=False)

    # Trace: FX Spot (Secondary Axis)
    if show_fx and m['fx'] in p_df.columns:
        fig1.add_trace(go.Scatter(
            x=p_df['Date'], y=p_df[m['fx']], 
            name=f"USD/{m['label']} Spot", 
            line=dict(color='#E67E22', width=2, dash='dot')
        ), secondary_y=True)

    fig1.update_layout(height=500, template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
    fig1.update_yaxes(title_text="Policy Rate (%)", secondary_y=False)
    fig1.update_yaxes(title_text=f"Exchange Rate (USD/{m['label']})", secondary_y=True)
    st.plotly_chart(fig1, use_container_width=True)

    # --- 6. FUNDAMENTALS ---
    st.subheader("II. Macroeconomic Fundamentals")
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**Consumer Price Index (YoY %)**")
        fig_cpi = go.Figure(go.Bar(x=p_df['Date'], y=p_df[m['cpi']], marker_color='#2E86C1'))
        fig_cpi.update_layout(height=350, template="plotly_white", margin=dict(t=10))
        st.plotly_chart(fig_cpi, use_container_width=True)

    with c2:
        if show_gdp:
            st.write("**Real GDP Growth (Annual %)**")
            gdp_disp = p_df.drop_duplicates('Year')
            fig_gdp = go.Figure(go.Bar(x=gdp_disp['Year'], y=gdp_disp[m['gdp']], marker_color='#1D8348'))
            fig_gdp.update_layout(height=350, template="plotly_white", margin=dict(t=10))
            st.plotly_chart(fig_gdp, use_container_width=True)

st.divider()
st.info("**Analysis Summary:** This terminal reconciles monthly macro data with daily market spot rates. Correlation between the Policy Rate and FX often illustrates the **Interest Rate Parity** model.")
