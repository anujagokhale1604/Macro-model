import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. INSTITUTIONAL STYLING (CSS) ---
st.set_page_config(page_title="Macro Terminal Pro", layout="wide")

# CSS for Serif Fonts, Adaptive Containers, and Mode-Agnostic Colors
st.markdown("""
    <style>
    /* Force Institutional Font (Serif) */
    html, body, [class*="css"], .stMarkdown, p, span {
        font-family: 'Times New Roman', Times, serif !important;
    }
    
    /* Elegant Title Styling */
    .main-title {
        font-size: 42px;
        font-weight: 700;
        letter-spacing: -1px;
        border-bottom: 2px solid #d4af37;
        margin-bottom: 20px;
    }

    /* Adaptive Note Containers (Works in Light & Dark Mode) */
    .note-box {
        padding: 20px;
        border-radius: 8px;
        border-left: 5px solid #d4af37;
        background-color: rgba(150, 150, 150, 0.1);
        margin-bottom: 15px;
    }
    
    /* Subtitle Styling */
    .section-header {
        color: #d4af37;
        font-variant: small-caps;
        font-size: 24px;
        margin-top: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_data():
    # Load Macro & Policy
    df = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - Macro data.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # Load GDP Growth
    gdp_raw = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - GDP_Growth.csv', skiprows=1)
    gdp_clean = gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
    gdp_clean.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    gdp_clean['Year'] = pd.to_numeric(gdp_clean['Year'], errors='coerce')
    
    # Load FX Data
    def process_fx(file, col, label):
        f = pd.read_csv(file)
        f['observation_date'] = pd.to_datetime(f['observation_date'])
        f[col] = pd.to_numeric(f[col], errors='coerce')
        return f.resample('MS', on='observation_date').mean().reset_index().rename(columns={'observation_date': 'Date', col: label})

    fx_inr = process_fx('DEXINUS.xlsx - Daily.csv', 'DEXINUS', 'FX_India')
    fx_gbp = process_fx('DEXUSUK.xlsx - Daily.csv', 'DEXUSUK', 'FX_UK')
    
    # Merge
    df['Year'] = df['Date'].dt.year
    df = df.merge(gdp_clean, on='Year', how='left')
    df = df.merge(fx_inr, on='Date', how='left').merge(fx_gbp, on='Date', how='left')
    
    return df.sort_values('Date')

df = load_data()

# --- 3. SIDEBAR: THE ANALYTICAL CONSOLE ---
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>🏛️ Terminal Console</h2>", unsafe_allow_html=True)
    market = st.selectbox("Market Selection", ["India", "UK", "Singapore"])
    
    st.divider()
    st.markdown("### ⏳ Time Horizon")
    horizon = st.radio("Select Period", ["Historical", "10 Years", "5 Years"], index=1)
    
    st.divider()
    st.markdown("### 📉 Macro Scenarios")
    scenario = st.selectbox("Simulation Mode", 
                           ["Baseline", "Stagflation 🌪️", "Depression 📉", "Economic Boom 🚀", "Custom Override ⚙️"])
    
    # Custom Toggle Logic
    c_cpi, c_gdp, c_rate = 0.0, 0.0, 0.0
    if "Custom" in scenario:
        st.info("Manual Override Active")
        c_cpi = st.slider("CPI Adjustment (%)", -5.0, 10.0, 0.0)
        c_gdp = st.slider("GDP Adjustment (%)", -10.0, 5.0, 0.0)
        c_rate = st.slider("Policy Shift (bps)", -300, 300, 0) / 100

# --- 4. SCENARIO CALCULATIONS ---
mapping = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "ccy": "INR"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "ccy": "GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "ccy": "SGD"}
}
m = mapping[market]

# Horizon Filter
max_date = df['Date'].max()
if horizon == "5 Years":
    p_df = df[df['Date'] >= (max_date - pd.DateOffset(years=5))].copy()
elif horizon == "10 Years":
    p_df = df[df['Date'] >= (max_date - pd.DateOffset(years=10))].copy()
else:
    p_df = df.copy()

# Apply Scenario Logic
if "Stagflation" in scenario:
    p_df[m['cpi']] += 5.0
    p_df[m['gdp']] -= 3.0
elif "Depression" in scenario:
    p_df[m['gdp']] -= 8.0
    p_df[m['cpi']] -= 2.0
elif "Boom" in scenario:
    p_df[m['gdp']] += 4.0
    p_df[m['cpi']] += 1.5
elif "Custom" in scenario:
    p_df[m['cpi']] += c_cpi
    p_df[m['gdp']] += c_gdp
    p_df[m['p']] += c_rate

# --- 5. MAIN DASHBOARD UI ---
st.markdown(f"<div class='main-title'>🏛️ {market.upper()} MACRO TERMINAL</div>", unsafe_allow_html=True)

# Metrics Cards
c1, c2, c3, c4 = st.columns(4)
c1.metric("📌 Policy Rate", f"{p_df[m['p']].iloc[-1]:.2f}%")
c2.metric("🔥 CPI Inflation", f"{p_df[m['cpi']].iloc[-1]:.2f}%")
c3.metric("📈 GDP Growth", f"{p_df[m['gdp']].iloc[-1]:.1f}%")
c4.metric("💱 FX Spot", f"{p_df[m['fx']].iloc[-1]:.2f}" if pd.notnull(p_df[m['fx']].iloc[-1]) else "N/A")

# --- GRAPH 1: POLICY & FX ---
st.markdown("<div class='section-header'>I. Monetary Policy & Equilibrium</div>", unsafe_allow_html=True)
fig1 = make_subplots(specs=[[{"secondary_y": True}]])

# Primary: Policy Rate
fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Policy Rate (%)", 
                         line=dict(color='#003366', width=4)), secondary_y=False)

# Secondary: FX Overlay
if pd.notnull(p_df[m['fx']]).any():
    fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name=f"FX ({m['ccy']}/USD)", 
                             line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)

fig1.update_layout(height=450, template="none", hovermode="x unified", legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig1, width='stretch')

# --- GRAPH 2: GDP & CPI ---
st.markdown("<div class='section-header'>II. Growth & Fundamental Dynamics</div>", unsafe_allow_html=True)
fig2 = go.Figure()

# CPI Bars
fig2.add_trace(go.Bar(x=p_df['Date'], y=p_df[m['cpi']], name="CPI (YoY %)", 
                     marker_color='rgba(150, 150, 150, 0.4)'))

# GDP Line (Historical Growth Data)
fig2.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['gdp']], name="Annual GDP Growth (%)", 
                         line=dict(color='#1D8348', width=3)))

fig2.update_layout(height=400, template="none", barmode='overlay', hovermode="x unified")
st.plotly_chart(fig2, width='stretch')

# --- 6. DOCUMENTATION: NOTES ---
st.divider()
st.markdown("<div class='section-header'>📜 Research Intelligence</div>", unsafe_allow_html=True)

col_exp, col_meth = st.columns(2)

with col_exp:
    st.markdown(f"""
    <div class="note-box">
        <b>📝 Explanatory Note</b><br>
        This terminal simulates the <b>Monetary Transmission Mechanism</b> for {market}. 
        By toggling scenarios like <i>Stagflation</i>, the model adjusts the underlying 
        macro fundamentals to show how the current policy rate environment would react 
        to severe exogenous shocks.
    </div>
    """, unsafe_allow_html=True)

with col_meth:
    st.markdown("""
    <div class="note-box">
        <b>🧪 Methodological Note</b><br>
        <b>Data Sync:</b> Monthly macro data is merged with Annual GDP growth rates. 
        FX rates are derived from daily spot averages.<br>
        <b>Scenario Math:</b> Stagflation adds a +5.0% shock to CPI; Depression simulates 
        a -8.0% GDP contraction.
    </div>
    """, unsafe_allow_html=True)

st.caption("Institutional Intelligence Platform | Garamond/Times Stylized | v3.0")
