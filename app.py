import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. INSTITUTIONAL STYLING (CSS) ---
st.set_page_config(page_title="Macro Terminal Pro", layout="wide")

st.markdown("""
    <style>
    /* Professional Serif Font - Garamond/Times Premier */
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@400;700&display=swap');

    html, body, [class*="css"], .stMarkdown, p, span {
        font-family: 'EB Garamond', serif !important;
        font-size: 1.05rem;
    }
    
    .main-title {
        font-size: 48px;
        font-weight: 700;
        color: #d4af37;
        border-bottom: 2px solid rgba(212, 175, 55, 0.3);
        margin-bottom: 25px;
        text-align: center;
    }

    /* Adaptive Note Containers */
    .note-box {
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(212, 175, 55, 0.3);
        background-color: rgba(150, 150, 150, 0.08);
        margin-bottom: 15px;
        line-height: 1.6;
    }
    
    .section-header {
        color: #d4af37;
        font-variant: small-caps;
        font-size: 26px;
        margin-top: 35px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ROBUST DATA ENGINE (EXCEL VERSION) ---
@st.cache_data
def load_data():
    # Paths to the .xlsx files as confirmed
    files = {
        "workbook": 'EM_Macro_Data_India_SG_UK.xlsx',
        "inr": 'DEXINUS.xlsx',
        "gbp": 'DEXUSUK.xlsx',
        "sgd": 'AEXSIUS.xlsx'
    }
    
    # Check if files exist to avoid FileNotFoundError
    for key, path in files.items():
        if not os.path.exists(path):
            st.error(f"⚠️ Missing File: `{path}`. Please ensure it is uploaded to your GitHub repository.")
            st.stop()

    # 2a. Load Main Macro Data from Sheet
    df = pd.read_excel(files["workbook"], sheet_name='Macro data')
    df['Date'] = pd.to_datetime(df['Date'])
    
    # 2b. Load GDP Growth from Sheet
    # Note: skiprows=1 is used based on your specific file structure
    gdp = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
    gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    gdp['Year'] = pd.to_numeric(gdp['Year'], errors='coerce')
    
    # 2c. Helper to process FX Workbooks
    def get_fx(path, col, name):
        f = pd.read_excel(path)
        # Identify date column (usually 'observation_date' or the first column)
        date_col = 'observation_date' if 'observation_date' in f.columns else f.columns[0]
        f[date_col] = pd.to_datetime(f[date_col])
        f[col] = pd.to_numeric(f[col], errors='coerce')
        # Aggregate to Monthly
        return f.resample('MS', on=date_col).mean().reset_index().rename(columns={date_col: 'Date', col: name})

    fx_inr = get_fx(files["inr"], 'DEXINUS', 'FX_India')
    fx_gbp = get_fx(files["gbp"], 'DEXUSUK', 'FX_UK')
    fx_sgd = get_fx(files["sgd"], 'AEXSIUS', 'FX_Singapore')
    
    # 2d. Merge Datasets
    df['Year'] = df['Date'].dt.year
    df = df.merge(gdp, on='Year', how='left')
    df = df.merge(fx_inr, on='Date', how='left')
    df = df.merge(fx_gbp, on='Date', how='left')
    df = df.merge(fx_sgd, on='Date', how='left')
    
    return df.sort_values('Date')

df = load_data()

# --- 3. SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>🏛️ Terminal Setup</h2>", unsafe_allow_html=True)
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

# Horizon Filter
max_date = df['Date'].max()
mask = df['Date'] > (max_date - pd.DateOffset(years=5 if "5" in horizon else 10)) if "Historical" not in horizon else [True]*len(df)
p_df = df[mask].copy()

# Scenario Logic (Dynamic adjustments)
if "Stagflation" in scenario:
    p_df[m['cpi']] += 4.0; p_df[m['gdp']] -= 2.5
elif "Depression" in scenario:
    p_df[m['gdp']] -= 7.0; p_df[m['cpi']] -= 1.5

# --- 5. UI LAYOUT ---
st.markdown(f"<div class='main-title'>MONETARY INTELLIGENCE: {market.upper()}</div>", unsafe_allow_html=True)

# Metrics Row
cols = st.columns(4)
cols[0].metric("Policy Rate", f"{p_df[m['p']].iloc[-1]:.2f}%")
cols[1].metric("CPI (YoY)", f"{p_df[m['cpi']].iloc[-1]:.2f}%")
cols[2].metric("GDP Growth", f"{p_df[m['gdp']].iloc[-1]:.1f}%")
# Dynamic FX label based on currency
cols[3].metric(f"FX Rate ({m['sym']})", f"{p_df[m['fx']].iloc[-1]:.2f}" if pd.notnull(p_df[m['fx']].iloc[-1]) else "N/A")

# Charts
st.markdown("<div class='section-header'>I. Interest Rate & Currency Corridor</div>", unsafe_allow_html=True)
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Policy Rate", line=dict(color='#1f77b4', width=3)), secondary_y=False)
fig1.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name="FX Spot", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
fig1.update_layout(template="plotly_white", height=400, margin=dict(t=20, b=20), legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig1, width="stretch")

# Notes Section
st.divider()
n1, n2 = st.columns(2)
with n1:
    st.markdown(f"""<div class='note-box'><b>💡 Explanatory:</b> This view captures {market}'s 
    monetary stance. In <b>{scenario}</b> mode, we observe the deviation of real rates from 
    long-term growth targets.</div>""", unsafe_allow_html=True)
with n2:
    st.markdown("""<div class='note-box'><b>🧪 Methodological:</b> Data is sourced directly from Excel (.xlsx) workbooks. 
    FX rates represent monthly averages of daily spot prices. GDP is mapped annually.</div>""", unsafe_allow_html=True)
