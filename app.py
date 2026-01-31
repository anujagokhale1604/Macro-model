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
        font-size: 48px; font-weight: 700; color: #d4af37;
        border-bottom: 2px solid rgba(212, 175, 55, 0.3);
        margin-bottom: 25px; text-align: center;
    }
    .note-box {
        padding: 20px; border-radius: 12px; border: 1px solid rgba(212, 175, 55, 0.3);
        background-color: rgba(150, 150, 150, 0.08); margin-bottom: 15px; line-height: 1.6;
    }
    .section-header {
        color: #d4af37; font-variant: small-caps; font-size: 26px;
        margin-top: 35px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DYNAMIC DATA ENGINE ---
@st.cache_data
def load_data():
    files = {
        "workbook": 'EM_Macro_Data_India_SG_UK.xlsx',
        "inr": 'DEXINUS.xlsx',
        "gbp": 'DEXUSUK.xlsx',
        "sgd": 'AEXSIUS.xlsx'
    }
    
    for key, path in files.items():
        if not os.path.exists(path):
            st.error(f"⚠️ Missing: `{path}`. Please upload to GitHub.")
            st.stop()

    # 2a. Main Macro & GDP (Sheet specific)
    df = pd.read_excel(files["workbook"], sheet_name='Macro data')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    gdp = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
    gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    gdp['Year'] = pd.to_numeric(gdp['Year'], errors='coerce')
    
    # 2b. Robust FX Loader for FRED XLSX
    def get_fx(path, fred_col, output_name):
        # We try to read the file. We don't skip rows initially to find the header.
        try:
            # First, read a small chunk to find where 'observation_date' actually is
            preview = pd.read_excel(path, nrows=20)
            # Find row index where 'observation_date' appears
            skip_n = 10 # Default for FRED
            for i, row in preview.iterrows():
                if 'observation_date' in row.values:
                    skip_n = i + 1
                    break
            
            f = pd.read_excel(path, skiprows=skip_n)
            f.columns = f.columns.str.strip() # Remove spaces
            
            # Find date column and value column by name
            date_col = 'observation_date' if 'observation_date' in f.columns else f.columns[0]
            val_col = fred_col if fred_col in f.columns else f.columns[1]
            
            # Clean and Convert
            f[date_col] = pd.to_datetime(f[date_col], errors='coerce')
            f[val_col] = pd.to_numeric(f[val_col], errors='coerce')
            
            # Drop metadata rows/empty rows
            f = f.dropna(subset=[date_col, val_col])
            
            # Resample to Monthly Mean
            return f.resample('MS', on=date_col).mean().reset_index().rename(columns={date_col: 'Date', val_col: output_name})
        
        except Exception as e:
            st.warning(f"Could not parse {path} automatically. Check file structure.")
            return pd.DataFrame(columns=['Date', output_name])

    fx_inr = get_fx(files["inr"], 'DEXINUS', 'FX_India')
    fx_gbp = get_fx(files["gbp"], 'DEXUSUK', 'FX_UK')
    fx_sgd = get_fx(files["sgd"], 'AEXSIUS', 'FX_Singapore')
    
    # 2c. Final Merge
    df['Year'] = df['Date'].dt.year
    df = df.merge(gdp, on='Year', how='left')
    df = df.merge(fx_inr, on='Date', how='left').merge(fx_gbp, on='Date', how='left').merge(fx_sgd, on='Date', how='left')
    
    return df.sort_values('Date').dropna(subset=['Date'])

df = load_data()

# --- 3. UI & ANALYTICS ---
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>🏛️ Terminal Setup</h2>", unsafe_allow_html=True)
    market = st.selectbox("Select Market", ["India", "UK", "Singapore"])
    horizon = st.radio("Horizon", ["Historical", "10 Years", "5 Years"], index=1)
    scenario = st.selectbox("Simulation", ["Standard", "Stagflation 🌪️", "Depression 📉"])

m_map = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR/USD"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "USD/GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD/USD"}
}
m = m_map[market]

# Filter
max_date = df['Date'].max()
if horizon == "10 Years": df = df[df['Date'] > (max_date - pd.DateOffset(years=10))]
elif horizon == "5 Years": df = df[df['Date'] > (max_date - pd.DateOffset(years=5))]

# Scenario
p_df = df.copy()
if "Stagflation" in scenario: p_df[m['cpi']] += 3.5; p_df[m['gdp']] -= 2.0
elif "Depression" in scenario: p_df[m['gdp']] -= 6.0

st.markdown(f"<div class='main-title'>MONETARY INTELLIGENCE: {market.upper()}</div>", unsafe_allow_html=True)

# Layout
c1, c2, c3, c4 = st.columns(4)
c1.metric("Policy Rate", f"{p_df[m['p']].iloc[-1]:.2f}%")
c2.metric("CPI (YoY)", f"{p_df[m['cpi']].iloc[-1]:.2f}%")
c3.metric("GDP Growth", f"{p_df[m['gdp']].iloc[-1]:.1f}%")
c4.metric(f"FX: {m['sym']}", f"{p_df[m['fx']].iloc[-1]:.2f}")

st.markdown("<div class='section-header'>I. Monetary & Currency Corridor</div>", unsafe_allow_html=True)
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Policy Rate (%)", line=dict(color='#1f77b4', width=3)), secondary_y=False)
fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name=f"FX Rate ({m['sym']})", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
fig.update_layout(template="plotly_white", height=500, margin=dict(t=20, b=20), legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, width="stretch")

st.divider()
st.markdown(f"<div class='note-box'><b>💡 Analysis:</b> Market viewing {market} via a <b>{scenario}</b> lens. Data is sourced from institutional .xlsx workbooks.</div>", unsafe_allow_html=True)
