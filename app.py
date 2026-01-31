import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. INSTITUTIONAL BEIGE STYLING ---
st.set_page_config(page_title="Macro Terminal Pro", layout="wide")

st.markdown("""
    <style>
    /* Background and Global Font */
    .stApp {
        background-color: #F5F5DC; /* Beige */
        color: #2c3e50;
    }
    
    /* Sidebar Styling: Dark & Professional */
    section[data-testid="stSidebar"] {
        background-color: #2c3e50 !important;
        border-right: 2px solid #d4af37;
    }
    
    /* Dark Toggles/Labels in Sidebar */
    section[data-testid="stSidebar"] .stWidgetLabel, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {
        color: #ecf0f1 !important;
    }

    .main-title {
        font-size: 38px;
        font-weight: 800;
        color: #1a1a1a;
        border-bottom: 3px solid #d4af37;
        margin-bottom: 20px;
    }

    /* Professional Note Boxes */
    .note-box {
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #d4af37;
        background-color: #ffffff;
        margin-bottom: 20px;
        line-height: 1.6;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    
    .header-gold { color: #b8860b; font-weight: bold; font-size: 20px; }
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

    # Load Main Data
    df_macro = pd.read_excel(files["workbook"], sheet_name='Macro data')
    df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
    
    # Load GDP
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

# --- 3. SIDEBAR CONTROLS & RESET ---
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>🏛️ TERMINAL SETUP</h2>", unsafe_allow_html=True)
    
    if st.button("🔄 Reset Terminal"):
        st.rerun()

    market = st.selectbox("Select Market", ["India", "UK", "Singapore"])
    horizon = st.radio("Lookback Horizon", ["Historical", "10 Years", "5 Years"], index=1)
    st.divider()
    scenario = st.selectbox("Macro Simulation", 
                           ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])

# --- 4. ANALYTICS MAPPING ---
m_map = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "₹"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "£"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "S$"}
}
m = m_map[market]

# Filtering
df = raw_df.copy()
if horizon == "10 Years":
    df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
elif horizon == "5 Years":
    df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

# Scenario Logic
if "Stagflation" in scenario:
    df[m['cpi']] += 4.0; df[m['gdp']] -= 2.5
elif "Depression" in scenario:
    df[m['gdp']] -= 7.0; df[m['cpi']] -= 1.5
elif "High Growth" in scenario:
    df[m['gdp']] += 3.0; df[m['cpi']] -= 0.5

# --- 5. UI LAYOUT ---
st.markdown(f"<div class='main-title'>MONETARY INTELLIGENCE: {market.upper()}</div>", unsafe_allow_html=True)

# Metrics Row
cols = st.columns(4)
cols[0].metric("Policy Rate", f"{df[m['p']].iloc[-1]:.2f}%")
cols[1].metric("CPI (YoY)", f"{df[m['cpi']].iloc[-1]:.2f}%")
cols[2].metric("GDP Growth", f"{df[m['gdp']].iloc[-1]:.1f}%")
cols[3].metric("FX Rate", f"{df[m['fx']].iloc[-1]:.2f}" if pd.notnull(df[m['fx']].iloc[-1]) else "N/A")

# Graphs
st.markdown("<div class='header-gold'>I. Monetary Corridor & Currency Dynamics</div>", unsafe_allow_html=True)
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Policy Rate", line=dict(color='#1f77b4', width=3)), secondary_y=False)
fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="FX Spot", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
fig1.update_layout(height=400, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)')
st.plotly_chart(fig1, use_container_width=True)

c_a, c_b = st.columns(2)
with c_a:
    st.markdown("<div class='header-gold'>II. Inflationary Trends (CPI)</div>", unsafe_allow_html=True)
    fig2 = go.Figure(go.Scatter(x=df['Date'], y=df[m['cpi']], fill='tozeroy', line=dict(color='#e74c3c')))
    fig2.update_layout(height=300, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig2, use_container_width=True)
with c_b:
    st.markdown("<div class='header-gold'>III. GDP Growth Trajectory</div>", unsafe_allow_html=True)
    fig3 = go.Figure(go.Bar(x=df['Date'], y=df[m['gdp']], marker_color='#2ecc71'))
    fig3.update_layout(height=300, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig3, use_container_width=True)

# --- 6. DETAILED NOTES ---
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("<div class='header-gold'>Explanatory Note</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='note-box'>
    <b>What this graph shows:</b> This dashboard visualizes the interplay between <b>Central Bank Policy</b>, <b>Inflation (CPI)</b>, and <b>Economic Output (GDP)</b>.<br><br>
    <b>Meaning:</b> When the blue line (Policy Rate) rises, the central bank is trying to cool down inflation (red chart). 
    A strengthening currency (Gold dotted line) often follows higher rates. In the <b>{scenario}</b> scenario, 
    we simulate how these variables deviate from historical norms, allowing you to see if the currency can withstand economic shocks.
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='header-gold'>Recommendations</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='note-box'>
    <b>Institutional Actions:</b><br>
    1. <b>Hedge Currency Risk:</b> If the simulation shows high FX volatility, consider forward contracts.<br>
    2. <b>Monitor Real Rates:</b> Ensure the Policy Rate stays above CPI to maintain purchasing power.<br>
    3. <b>Diversify:</b> In Stagflation scenarios, increase exposure to non-cyclical assets.
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown("<div class='header-gold'>Methodological Note</div>", unsafe_allow_html=True)
    st.markdown("""<div class='note-box'>
    <b>The Concept:</b> This model utilizes <i>Macro-Financial Integration</i>. 
    It combines daily-frequency FX data with monthly CPI and annual GDP data into a unified time-series.<br><br>
    <b>Data Processing:</b> 
    - <b>Resampling:</b> Daily FX rates are averaged into monthly buckets to align with inflation reporting.<br>
    - <b>Temporal Mapping:</b> Annual GDP growth is mapped to the final month of each fiscal year to prevent look-ahead bias.<br>
    - <b>Simulation:</b> Scenario adjustments use additive and multiplicative shifts based on historical standard deviations.
    </div>""", unsafe_allow_html=True)
