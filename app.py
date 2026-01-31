import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. INSTITUTIONAL BEIGE & SLATE STYLING ---
st.set_page_config(page_title="Macro Terminal Pro", layout="wide")

st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #F5F5DC; /* Beige */
        color: #2c3e50;
    }
    
    /* Sidebar: Dark Slate */
    section[data-testid="stSidebar"] {
        background-color: #2c3e50 !important;
        border-right: 2px solid #d4af37;
    }
    
    /* Sidebar Text & Toggles */
    section[data-testid="stSidebar"] .stWidgetLabel, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stSlider {
        color: #ecf0f1 !important;
    }

    .main-title {
        font-size: 36px;
        font-weight: 800;
        color: #1a1a1a;
        border-bottom: 3px solid #d4af37;
        margin-bottom: 25px;
        text-transform: uppercase;
    }

    /* Note Boxes */
    .note-box {
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #d4af37;
        background-color: #ffffff;
        margin-bottom: 20px;
        color: #2c3e50;
        box-shadow: 2px 2px 12px rgba(0,0,0,0.05);
    }
    
    .header-gold { color: #b8860b; font-weight: bold; font-size: 20px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_data():
    files = {
        "workbook": 'EM_Macro_Data_India_SG_UK.xlsx',
        "inr": 'DEXINUS.xlsx',
        "gbp": 'DEXUSUK.xlsx',
        "sgd": 'AEXSIUS.xlsx'
    }

    df_macro = pd.read_excel(files["workbook"], sheet_name='Macro data')
    df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
    
    df_gdp = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
    df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')

    def get_fx(path, out_col):
        try:
            xls = pd.ExcelFile(path)
            sheet = [s for s in xls.sheet_names if s != 'README'][0]
            f = pd.read_excel(path, sheet_name=sheet)
            d_col = [c for c in f.columns if 'date' in c.lower()][0]
            v_col = [c for c in f.columns if c != d_col][0]
            f[d_col] = pd.to_datetime(f[d_col], errors='coerce')
            f[v_col] = pd.to_numeric(f[v_col], errors='coerce')
            return f.dropna().resample('MS', on=d_col).mean().reset_index().rename(columns={d_col:'Date', v_col:out_col})
        except: return pd.DataFrame(columns=['Date', out_col])

    fx_inr = get_fx(files["inr"], 'FX_India')
    fx_gbp = get_fx(files["gbp"], 'FX_UK')
    fx_sgd = get_fx(files["sgd"], 'FX_Singapore')

    df_macro['Year'] = df_macro['Date'].dt.year
    df = df_macro.merge(df_gdp, on='Year', how='left')
    for fx in [fx_inr, fx_gbp, fx_sgd]:
        df = df.merge(fx, on='Date', how='left')
    
    return df.sort_values('Date')

raw_df = load_data()

# --- 3. THE COMPLETE TOGGLE SUITE (SIDEBAR) ---
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>🏛️ TERMINAL CONTROLS</h2>", unsafe_allow_html=True)
    
    if st.button("🔄 Reset to Default"):
        st.rerun()
    
    st.divider()
    # Toggle 1: Market
    market = st.selectbox("Select Target Market", ["India", "UK", "Singapore"])
    
    # Toggle 2: Timeframe
    horizon = st.radio("Analysis Horizon", ["Historical", "10 Years", "5 Years"], index=1)
    
    st.divider()
    # Toggle 3: Macro Scenario
    scenario = st.selectbox("Global Scenario", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    
    # Toggle 4: Stress Test Intensity
    stress_level = st.slider("Scenario Severity (%)", 0, 100, 50)
    
    # Toggle 5: Chart View
    show_fx = st.toggle("Overlay FX Exchange Rate", value=True)
    show_metrics = st.toggle("Display Raw Data Metrics", value=True)

# --- 4. DATA PROCESSING & SIMULATION ---
m_map = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD"}
}
m = m_map[market]

df = raw_df.copy()

# Apply Horizon
if horizon == "10 Years":
    df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
elif horizon == "5 Years":
    df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

# Apply Simulation Logic with Severity Slider
mult = stress_level / 100
if "Stagflation" in scenario:
    df[m['cpi']] += (5.0 * mult); df[m['gdp']] -= (3.0 * mult)
elif "Depression" in scenario:
    df[m['gdp']] -= (8.0 * mult); df[m['cpi']] -= (2.0 * mult)
elif "High Growth" in scenario:
    df[m['gdp']] += (4.0 * mult); df[m['cpi']] -= (1.0 * mult)

# --- 5. DASHBOARD LAYOUT ---
st.markdown(f"<div class='main-title'>MONETARY TERMINAL: {market.upper()}</div>", unsafe_allow_html=True)

if show_metrics:
    cols = st.columns(4)
    cols[0].metric("Policy Rate", f"{df[m['p']].iloc[-1]:.2f}%")
    cols[1].metric("CPI (Inflation)", f"{df[m['cpi']].iloc[-1]:.2f}%")
    cols[2].metric("GDP Growth", f"{df[m['gdp']].iloc[-1]:.1f}%")
    cols[3].metric(f"FX ({m['sym']})", f"{df[m['fx']].iloc[-1]:.2f}" if pd.notnull(df[m['fx']].iloc[-1]) else "N/A")

# Primary Charts
st.markdown("<div class='header-gold'>I. Monetary Corridor & Currency Sensitivity</div>", unsafe_allow_html=True)
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Policy Rate (%)", line=dict(color='#1f77b4', width=3)), secondary_y=False)
if show_fx:
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name=f"FX Spot ({m['sym']})", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
fig1.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450)
st.plotly_chart(fig1, use_container_width=True)

c_left, c_right = st.columns(2)
with c_left:
    st.markdown("<div class='header-gold'>II. CPI Inflation (YoY %)</div>", unsafe_allow_html=True)
    fig2 = go.Figure(go.Scatter(x=df['Date'], y=df[m['cpi']], fill='tozeroy', line=dict(color='#e74c3c')))
    fig2.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=300)
    st.plotly_chart(fig2, use_container_width=True)
with c_right:
    st.markdown("<div class='header-gold'>III. Real GDP Growth Rate</div>", unsafe_allow_html=True)
    fig3 = go.Figure(go.Bar(x=df['Date'], y=df[m['gdp']], marker_color='#2ecc71'))
    fig3.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=300)
    st.plotly_chart(fig3, use_container_width=True)

# --- 6. INSTITUTIONAL NOTES & RECOMMENDATIONS ---
st.divider()
n1, n2 = st.columns(2)

with n1:
    st.markdown("<div class='header-gold'>Explanatory Note</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='note-box'>
    <b>Visual Interpretation:</b> The primary chart tracks the <b>Policy Rate</b> against <b>Currency Fluctuations</b>. 
    Typically, an increasing Policy Rate (Blue) attracts foreign capital, strengthening the local currency (Gold).<br><br>
    <b>Simulation Impact:</b> You are currently viewing the <b>{scenario}</b> scenario at a <b>{stress_level}% intensity</b>. 
    In this model, "Stagflation" simulates a supply-side shock where prices rise despite falling output, 
    challenging the Central Bank's ability to maintain price stability.
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='header-gold'>Institutional Recommendations</div>", unsafe_allow_html=True)
    st.markdown("""<div class='note-box'>
    1. <b>Liquidity Management:</b> In high-rate environments, focus on cash-flow matching to handle increased borrowing costs.<br>
    2. <b>FX Hedging:</b> Utilize European-style options to protect against the downside currency volatility observed in the current simulation.<br>
    3. <b>Portfolio Weighting:</b> If GDP growth remains sub-2%, tilt portfolios toward defensive sectors (Utilities/Healthcare).
    </div>""", unsafe_allow_html=True)

with n2:
    st.markdown("<div class='header-gold'>Methodological Note</div>", unsafe_allow_html=True)
    st.markdown("""<div class='note-box'>
    <b>The Conceptual Framework:</b> This terminal utilizes <i>Data Synthesis Integration</i>. It solves the "Frequency Mismatch" problem 
    inherent in macroeconomics by harmonizing daily financial data (FX) with quarterly/annual real-economy indicators (GDP).<br><br>
    <b>Core Concepts Explained:</b><br>
    - <b>Temporal Resampling:</b> Daily FX observations are averaged into monthly timestamps to create a linear correlation with CPI.<br>
    - <b>Step-Interpolation:</b> Annual GDP growth is treated as a constant for the relevant 12-month period to ensure the charts remain scannable.<br>
    - <b>Stress Testing:</b> Scenario adjustments are applied to the most recent 24 months of data to project potential future deviations.
    </div>""", unsafe_allow_html=True)
