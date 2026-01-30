import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. DATA ENGINE ---
@st.cache_data
def load_and_sync_data():
    try:
        # Core Macro Data
        df = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Macro data')
        df['Date'] = pd.to_datetime(df['Date'])
        
        # GDP Growth
        gdp_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='GDP_Growth', skiprows=1)
        gdp_clean = gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
        gdp_clean.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        gdp_clean['Year'] = pd.to_numeric(gdp_clean['Year'], errors='coerce')
        gdp_clean = gdp_clean.dropna(subset=['Year'])
        
        # FX Data Processing
        def process_fx(file, col, label):
            f = pd.read_excel(file, sheet_name='Daily')
            f['observation_date'] = pd.to_datetime(f['observation_date'])
            f[col] = pd.to_numeric(f[col], errors='coerce')
            return f.resample('MS', on='observation_date').mean().reset_index().rename(columns={'observation_date': 'Date', col: label})

        fx_inr = process_fx('DEXINUS.xlsx', 'DEXINUS', 'FX_India')
        fx_gbp = process_fx('DEXUSUK.xlsx', 'DEXUSUK', 'FX_UK')
        
        # Global Merge
        df['Year'] = df['Date'].dt.year
        df = df.merge(gdp_clean, on='Year', how='left')
        df = df.merge(fx_inr, on='Date', how='left')
        df = df.merge(fx_gbp, on='Date', how='left')
        
        # Singapore FX (Annual)
        fx_sgd = pd.read_excel('AEXSIUS.xlsx', sheet_name='Annual')
        fx_sgd['Year'] = pd.to_datetime(fx_sgd['observation_date']).dt.year
        df = df.merge(fx_sgd[['Year', 'AEXSIUS']], on='Year', how='left').rename(columns={'AEXSIUS': 'FX_Singapore'})
        
        return df.sort_values('Date')
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

# --- 2. CONFIGURATION ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide")
df = load_and_sync_data()

# --- 3. SIDEBAR: THE CONTROL DESK ---
with st.sidebar:
    st.header("🎛️ Control Desk")
    market = st.selectbox("Select Core Market", ["India", "UK", "Singapore"])
    
    st.divider()
    st.subheader("🛠️ Policy Scenarios")
    timeline = st.slider("Time Horizon", 2012, 2025, (2018, 2024))
    shock = st.select_slider("Monetary Shock (bps)", options=[-150, -100, -75, -50, -25, 0, 25, 50, 75, 100, 150], value=0)
    stress_test = st.checkbox("Simulate GDP Shock (-2%)", value=False)

    st.divider()
    st.subheader("🔬 Quantitative Overlays")
    # Impressive Toggles
    show_taylor = st.toggle("Taylor Rule (Neutral: 2.5%)", value=False)
    show_real_rate = st.toggle("Real Interest Rate (Policy - CPI)", value=False)
    show_ma = st.toggle("12-Month Moving Average", value=False)
    
    # Basic Toggles
    st.subheader("📊 Display Settings")
    show_fx = st.toggle("Overlay FX Spot Rate", value=True)
    show_gdp = st.toggle("Show GDP Growth Panel", value=True)

# --- 4. DATA LOGIC ---
mapping = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD"}
}
m = mapping[market]
p_df = df[(df['Date'].dt.year >= timeline[0]) & (df['Date'].dt.year <= timeline[1])].copy()

# Apply Dynamic Shocks
p_df[m['p']] += (shock / 100)
if stress_test:
    p_df[m['gdp']] -= 2.0

# --- 5. MAIN TERMINAL DISPLAY ---
st.title("🏛️ Global Macro-Financial Intelligence Terminal")

# TAB SYSTEM FOR CLEANER UI
tab1, tab2 = st.tabs(["📈 Market Equilibrium", "📔 Methodology & Analysis"])

with tab1:
    # PRIMARY CHART
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 1. Policy Rate
    fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Adjusted Policy Rate", 
                             line=dict(color='#003366', width=4)), secondary_y=False)
    
    # 2. Taylor Rule Overlay
    if show_taylor:
        # Taylor Formula: R = Neutral + CPI + 0.5(CPI - Target)
        taylor = 2.5 + p_df[m['cpi']] + 0.5 * (p_df[m['cpi']] - 2.0)
        fig.add_trace(go.Scatter(x=p_df['Date'], y=taylor, name="Taylor Implied", 
                                 line=dict(color='rgba(128,128,128,0.5)', dash='dash')))

    # 3. Real Interest Rate
    if show_real_rate:
        real_r = p_df[m['p']] - p_df[m['cpi']]
        fig.add_trace(go.Scatter(x=p_df['Date'], y=real_r, name="Real Rate", 
                                 line=dict(color='#C0392B', width=2)))

    # 4. Moving Average
    if show_ma:
        ma_val = p_df[m['p']].rolling(window=12).mean()
        fig.add_trace(go.Scatter(x=p_df['Date'], y=ma_val, name="12M Moving Avg", 
                                 line=dict(color='#F1C40F', width=2)))

    # 5. FX Overlay
    if show_fx:
        fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name=f"USD/{m['sym']}", 
                                 line=dict(color='#E67E22', width=1.5, dash='dot')), secondary_y=True)

    fig.update_layout(height=550, template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
    fig.update_yaxes(title_text="Interest Rate (%)", secondary_y=False)
    fig.update_yaxes(title_text="Exchange Rate", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    # FUNDAMENTAL PANEL
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Price Stability (CPI YoY %)**")
        st.bar_chart(p_df.set_index('Date')[m['cpi']], color='#2E86C1')
    with c2:
        if show_gdp:
            st.write("**Growth Context (Annual GDP %)**")
            gdp_data = p_df.drop_duplicates('Year')
            fig_gdp = go.Figure(go.Bar(x=gdp_data['Year'], y=gdp_data[m['gdp']], 
                                      marker_color=np.where(gdp_data[m['gdp']]<0, '#E74C3C', '#1D8348')))
            fig_gdp.update_layout(height=300, template="plotly_white", margin=dict(t=10))
            st.plotly_chart(fig_gdp, use_container_width=True)

with tab2:
    st.header("Terminal Intelligence Notes")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("💡 Explanatory Note")
        st.write("""
        This dashboard visualizes the **Monetary Policy Transmission Mechanism**. 
        By adjusting the policy rate (Monetary Shock), you can observe how central banks attempt to 
        balance inflation (CPI) and growth (GDP). 
        
        * **Real Rates:** A negative real rate suggests 'easy money' that may fuel inflation.
        * **Taylor Rule:** Often used to judge if a central bank is "behind the curve" regarding inflation targets.
        * **FX Equilibrium:** Displays the relationship between domestic interest rates and currency strength (Interest Rate Parity).
        """)
        

    with col_b:
        st.subheader("🧪 Methodological Note")
        st.markdown("""
        **1. Data Resampling:**
        Daily FX Spot rates are aggregated into monthly arithmetic means to align with the reporting frequency of CPI and Policy data.
        
        **2. Taylor Rule Calculation:**
        We utilize a standardized Taylor Rule model:
        $$i = r_t + \pi_t + 0.5(\pi_t - \pi^*)$$
        Where $r_t$ is the neutral rate (set to 2.5%), $\pi_t$ is current inflation, and $\pi^*$ is the inflation target (assumed 2.0%).
        
        **3. Alignment:**
        GDP is annual data, matched to the monthly timeline by repeating the annual value across all twelve months of the respective year to allow for continuous visualization.
        """)
        

st.divider()
st.caption("Terminal v2.4 | High-Fidelity Macro Analysis Framework")
