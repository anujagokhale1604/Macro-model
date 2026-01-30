import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 1. DATA ENGINE (XLSX OPTIMIZED) ---
@st.cache_data
def load_and_sync_data():
    try:
        # Load Primary Macro & Policy Data
        df_macro = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Macro data')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        
        # Load GDP Growth (Cleaning messy headers)
        gdp_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='GDP_Growth', skiprows=1)
        gdp_clean = gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
        gdp_clean.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        gdp_clean['Year'] = pd.to_numeric(gdp_clean['Year'], errors='coerce')
        gdp_clean = gdp_clean.dropna(subset=['Year'])
        
        # FX Processing (Resampling Daily to Monthly)
        def process_fx(file, sheet, col, label):
            try:
                f = pd.read_excel(file, sheet_name=sheet)
                date_col = 'observation_date' if 'observation_date' in f.columns else f.columns[0]
                f[date_col] = pd.to_datetime(f[date_col])
                f[col] = pd.to_numeric(f[col], errors='coerce')
                return f.resample('MS', on=date_col).mean().reset_index().rename(columns={date_col: 'Date', col: label})
            except: return pd.DataFrame(columns=['Date', label])

        fx_inr = process_fx('DEXINUS.xlsx', 'Daily', 'DEXINUS', 'FX_India')
        fx_gbp = process_fx('DEXUSUK.xlsx', 'Daily', 'DEXUSUK', 'FX_UK')
        fx_sgd = process_fx('AEXSIUS.xlsx', 'Annual', 'AEXSIUS', 'FX_Singapore') # Using annual for SGP
        
        # Merge Master Dataframe
        df_macro['Year'] = df_macro['Date'].dt.year
        df = df_macro.merge(gdp_clean, on='Year', how='left')
        df = df.merge(fx_inr, on='Date', how='left').merge(fx_gbp, on='Date', how='left')
        
        # Fill Singapore FX based on Year
        fx_sgd['Year'] = fx_sgd['Date'].dt.year
        df = df.merge(fx_sgd[['Year', 'FX_Singapore']], on='Year', how='left')
        
        return df.sort_values('Date').reset_index(drop=True)
    except Exception as e:
        st.error(f"Operational Error: {e}")
        return pd.DataFrame()

# --- 2. CONFIGURATION & UI ---
st.set_page_config(page_title="Macro Terminal", layout="wide")
df = load_and_sync_data()

if not df.empty:
    st.title("🏛️ Global Macro-Financial Intelligence Terminal")
    st.caption("Quantitative Forecasting & Market Equilibrium Analysis")

    # --- 3. SIDEBAR: THE ANALYTICS DESK ---
    with st.sidebar:
        st.header("🎛️ Analytics Desk")
        market = st.selectbox("Market Selection", ["India", "UK", "Singapore"])
        
        st.divider()
        st.subheader("⏳ Time Horizon")
        horizon = st.radio("Select View", ["Historical", "10 Years", "5 Years"])
        
        st.divider()
        st.subheader("📉 Macro Scenarios")
        scenario_mode = st.selectbox("Environment Simulation", 
                                   ["Standard (Actuals)", "Stagflation", "Depression", "Economic Boom", "Custom Scenario"])
        
        # Customization Toggle Logic
        custom_cpi, custom_gdp, custom_rate = 0.0, 0.0, 0.0
        if scenario_mode == "Custom Scenario":
            st.info("Manual Parameter Override Active")
            custom_cpi = st.slider("CPI Adjustment (%)", -5.0, 10.0, 0.0)
            custom_gdp = st.slider("GDP Adjustment (%)", -10.0, 5.0, 0.0)
            custom_rate = st.slider("Policy Rate Shift (bps)", -300, 300, 0) / 100

        st.divider()
        st.subheader("🔍 Analytical Toggles")
        show_taylor = st.toggle("Overlay Taylor Rule", value=True)
        show_fx = st.toggle("Overlay FX Spot", value=True)
        show_metrics = st.toggle("Show Summary Metrics", value=True)

    # --- 4. SCENARIO & HORIZON ENGINE ---
    mapping = {
        "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "ccy": "INR"},
        "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "ccy": "GBP"},
        "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "ccy": "SGD"}
    }
    m = mapping[market]
    
    # Filter Horizon
    max_date = df['Date'].max()
    if horizon == "5 Years":
        p_df = df[df['Date'] >= (max_date - pd.DateOffset(years=5))].copy()
    elif horizon == "10 Years":
        p_df = df[df['Date'] >= (max_date - pd.DateOffset(years=10))].copy()
    else:
        p_df = df.copy()

    # Apply Scenario Impacts
    if scenario_mode == "Stagflation":
        p_df[m['cpi']] += 4.5  # High Inflation
        p_df[m['gdp']] -= 3.0  # Stagnant Growth
    elif scenario_mode == "Depression":
        p_df[m['gdp']] -= 8.0  # Sharp Contraction
        p_df[m['cpi']] -= 2.0  # Deflationary Pressure
    elif scenario_mode == "Economic Boom":
        p_df[m['gdp']] += 3.5  # Strong Growth
        p_df[m['cpi']] += 1.5  # Moderate Inflation
    elif scenario_mode == "Custom Scenario":
        p_df[m['cpi']] += custom_cpi
        p_df[m['gdp']] += custom_gdp
        p_df[m['p']] += custom_rate

    # --- 5. VISUALIZATION: THE COMMAND CENTER ---
    
    # Metrics Row
    if show_metrics:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Terminal Policy Rate", f"{p_df[m['p']].iloc[-1]:.2f}%")
        c2.metric("Latest CPI (YoY)", f"{p_df[m['cpi']].iloc[-1]:.2f}%")
        c3.metric("Annual GDP Growth", f"{p_df[m['gdp']].iloc[-1]:.2f}%")
        c4.metric("FX Spot Rate", f"{p_df[m['fx']].iloc[-1]:.2f} {m['ccy']}/USD")

    # Main Graph: Policy & Market Equilibrium
    st.subheader("I. Monetary Policy & Market Equilibrium")
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Policy Rate
    fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Policy Rate (%)", 
                             line=dict(color='#003366', width=4)), secondary_y=False)
    
    # Taylor Rule Overlay
    if show_taylor:
        # Taylor Formula: Neutral(2.5) + CPI + 0.5*(CPI - 2.0)
        taylor = 2.5 + p_df[m['cpi']] + 0.5 * (p_df[m['cpi']] - 2.0)
        fig1.add_trace(go.Scatter(x=p_df['Date'], y=taylor, name="Taylor Implied", 
                                 line=dict(color='rgba(128,128,128,0.5)', dash='dash')), secondary_y=False)

    # FX Overlay
    if show_fx:
        fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name=f"FX ({m['ccy']}/USD)", 
                                 line=dict(color='#E67E22', width=2, dash='dot')), secondary_y=True)

    fig1.update_layout(height=500, template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
    fig1.update_yaxes(title_text="Rate (%)", secondary_y=False)
    fig1.update_yaxes(title_text="Exchange Rate", secondary_y=True)
    st.plotly_chart(fig1, use_container_width=True)

    # Fundamentals Graph: CPI & GDP
    st.subheader("II. Macroeconomic Fundamentals (CPI & GDP Growth)")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=p_df['Date'], y=p_df[m['cpi']], name="CPI Inflation (YoY)", marker_color='#2E86C1', opacity=0.7))
    
    # Adding GDP as a line plot for clarity on growth trends
    gdp_data = p_df.drop_duplicates('Year')
    fig2.add_trace(go.Scatter(x=gdp_data['Date'], y=gdp_data[m['gdp']], name="GDP Growth (Annual %)", 
                             line=dict(color='#1D8348', width=3), mode='lines+markers'))

    fig2.update_layout(height=400, template="plotly_white", barmode='group', 
                      yaxis_title="Percentage (%)", hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    # --- 6. DOCUMENTATION EXPANDERS ---
    st.divider()
    col_note1, col_note2 = st.columns(2)
    
    with col_note1:
        with st.expander("📝 Explanatory Note", expanded=True):
            st.write("""
            **Purpose of the Terminal:**
            This dashboard is designed to analyze the **Monetary Transmission Mechanism**. It allows users to see how changes in 
            central bank policy rates affect inflation (CPI) and currency value (FX).
            
            **Key Indicators:**
            - **Policy Rate:** The primary tool used by central banks to manage economic heat.
            - **Taylor Rule:** A benchmark that suggests what the interest rate *should* be based on current inflation.
            - **GDP Growth:** A measure of economic health. In the graph above, the green line represents the annual percentage change in real GDP.
            """)
            
    with col_note2:
        with st.expander("🧪 Methodological Note", expanded=True):
            st.write("""
            **Data Harmonization:**
            - **Resampling:** Monthly data (CPI/Policy) is synced with Daily FX data using a monthly arithmetic mean calculation.
            - **GDP Mapping:** Annual GDP growth figures are mapped to the 12-month period of the respective year to allow for continuous time-series plotting.
            
            **Scenario Modeling Math:**
            - **Stagflation:** Simulated by adding 4.5% to CPI and subtracting 3% from GDP.
            - **Depression:** Simulated by subtracting 8% from GDP and 2% from CPI.
            - **Interest Rate Parity:** The FX overlay illustrates how currency typically strengthens when local interest rates rise relative to the USD.
            """)

else:
    st.warning("Data load failed. Please ensure the Excel files (EM_Macro_Data_India_SG_UK.xlsx, etc.) are in the root directory.")
