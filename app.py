import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. INSTITUTIONAL STYLING (CSS) ---
st.set_page_config(page_title="Macro Terminal Pro", layout="wide")

st.markdown("""
    <style>
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

# --- 2. DATA ENGINE (HANDLING EXCEL HEADERS) ---
@st.cache_data
def load_data():
    # File naming as per your repository
    files = {
        "workbook": 'EM_Macro_Data_India_SG_UK.xlsx',
        "inr": 'DEXINUS.xlsx',
        "gbp": 'DEXUSUK.xlsx',
        "sgd": 'AEXSIUS.xlsx'
    }
    
    for key, path in files.items():
        if not os.path.exists(path):
            st.error(f"⚠️ File Not Found: `{path}`. Please upload the .xlsx file to GitHub.")
            st.stop()

    # 2a. Load Main Macro Data (assuming standard sheet starting at row 0)
    df = pd.read_excel(files["workbook"], sheet_name='Macro data')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # 2b. Load GDP Growth (assuming standard FRED/World Bank style with 1 row skip)
    gdp = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
    gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    gdp['Year'] = pd.to_numeric(gdp['Year'], errors='coerce')
    
    # 2c. Helper to process FX Workbooks with FRED metadata
    def get_fx(path, col_name, output_name):
        try:
            # FRED Excel files typically have 10 rows of header/README info.
            # We skip 10 rows to reach the header "observation_date"
            f = pd.read_excel(path, skiprows=10)
            
            # Clean column names
            f.columns = f.columns.str.strip()
            
            # Identify the date column
            date_col = 'observation_date' if 'observation_date' in f.columns else f.columns[0]
            
            # Convert and Coerce: if a text row remains, it becomes NaT (Not a Time)
            f[date_col] = pd.to_datetime(f[date_col], errors='coerce')
            f[col_name] = pd.to_numeric(f[col_name], errors='coerce')
            
            # Drop rows where the date is invalid (the footer metadata)
            f = f.dropna(subset=[date_col])
            
            # Resample to Monthly Average
            return f.resample('MS', on=date_col).mean().reset_index().rename(columns={date_col: 'Date', col_name: output_name})
        except Exception as e:
            st.warning(f"Metadata mismatch in {path}. Attempting fallback parse...")
            # Fallback if the file has NO header (starts immediately at row 0)
            f_alt = pd.read_excel(path)
            f_alt.columns = ['Date', output_name]
            f_alt['Date'] = pd.to_datetime(f_alt['Date'], errors='coerce')
            return f_alt.dropna()

    fx_inr = get_fx(files["inr"], 'DEXINUS', 'FX_India')
    fx_gbp = get_fx(files["gbp"], 'DEXUSUK', 'FX_UK')
    fx_sgd = get_fx(files["sgd"], 'AEXSIUS', 'FX_Singapore')
    
    # 2d. Merge
    df['Year'] = df['Date'].dt.year
    df = df.merge(gdp, on='Year', how='left')
    df = df.merge(fx_inr, on='Date', how='left')
    df = df.merge(fx_gbp, on='Date', how='left')
    df = df.merge(fx_sgd, on='Date', how='left')
    
    return df.sort_values('Date').dropna(subset=['Date'])

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
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR/USD"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "USD/GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD/USD"}
}
m = m_map[market]

# Horizon Filter
max_date = df['Date'].max()
if horizon == "10 Years":
    mask = df['Date'] > (max_date - pd.DateOffset(years=10))
elif horizon == "5 Years":
    mask = df['Date'] > (max_date - pd.DateOffset(years=5))
else:
    mask = [True] * len(df)

p_df = df[mask].copy()

# Scenario Simulation Logic
if "Stagflation" in scenario:
    p_df[m['cpi']] += 3.5; p_df[m['gdp']] -= 2.0
elif "Depression" in scenario:
    p_df[m['gdp']] -= 6.0; p_df[m['cpi']] -= 1.0

# --- 5. UI LAYOUT ---
st.markdown(f"<div class='main-title'>MONETARY INTELLIGENCE: {market.upper()}</div>", unsafe_allow_html=True)

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Policy Rate", f"{p_df[m['p']].iloc[-1]:.2f}%")
c2.metric("CPI (YoY)", f"{p_df[m['cpi']].iloc[-1]:.2f}%")
c3.metric("GDP Growth", f"{p_df[m['gdp']].iloc[-1]:.1f}%")
c4.metric(f"FX: {m['sym']}", f"{p_df[m['fx']].iloc[-1]:.2f}")

# Chart
st.markdown("<div class='section-header'>I. Monetary & Currency Corridor</div>", unsafe_allow_html=True)
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Policy Rate (%)", line=dict(color='#1f77b4', width=3)), secondary_y=False)
fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name=f"FX Rate ({m['sym']})", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)

fig.update_layout(template="plotly_white", height=500, margin=dict(t=20, b=20), legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, width="stretch")

# Notes
st.divider()
n1, n2 = st.columns(2)
with n1:
    st.markdown(f"""<div class='note-box'><b>💡 Analysis:</b> Current {market} policy stance 
    reflected against FX volatility. Simulation set to <b>{scenario}</b>.</div>""", unsafe_allow_html=True)
with n2:
    st.markdown("""<div class='note-box'><b>🧪 Source:</b> All data extracted from .xlsx workbooks. 
    FRED metadata skipped via automated indexing.</div>""", unsafe_allow_html=True)
