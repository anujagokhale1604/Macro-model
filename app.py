import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. INSTITUTIONAL STYLING ---
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
        background-color: rgba(150, 150, 150, 0.08); margin-bottom: 15px;
    }
    .section-header {
        color: #d4af37; font-variant: small-caps; font-size: 26px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE BULLETPROOF DATA ENGINE ---
@st.cache_data
def load_data():
    files = {
        "workbook": 'EM_Macro_Data_India_SG_UK.xlsx',
        "inr": 'DEXINUS.xlsx',
        "gbp": 'DEXUSUK.xlsx',
        "sgd": 'AEXSIUS.xlsx'
    }
    
    # Validation
    for key, path in files.items():
        if not os.path.exists(path):
            st.error(f"⚠️ Missing: `{path}` in GitHub repository.")
            st.stop()

    # 2a. Load Main Macro Data
    # Assuming 'Macro data' is the first sheet or named correctly
    df_macro = pd.read_excel(files["workbook"], sheet_name='Macro data')
    df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
    
    # 2b. Load GDP Data
    df_gdp = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
    df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')

    # 2c. Robust FX Loader: Handles FRED formats without needing exact row counts
    def get_fx_robust(path, output_name):
        try:
            # Load the Excel - we read the whole first sheet
            raw = pd.read_excel(path)
            
            # Step 1: Find the Date column (contains 'observation_date' or starts with dates)
            # We look for the row that contains 'observation_date'
            data_start_idx = 0
            for i, row in raw.iterrows():
                if any("observation_date" in str(val).lower() for val in row.values):
                    data_start_idx = i + 1
                    break
            
            # Re-read from that row
            clean_f = pd.read_excel(path, skiprows=data_start_idx)
            clean_f.columns = [str(c).strip() for c in clean_f.columns]
            
            # Identify columns by typical FRED names
            date_col = [c for c in clean_f.columns if 'date' in c.lower()][0]
            val_col = [c for c in clean_f.columns if c != date_col][0]
            
            clean_f[date_col] = pd.to_datetime(clean_f[date_col], errors='coerce')
            clean_f[val_col] = pd.to_numeric(clean_f[val_col], errors='coerce')
            
            # Aggregate to Monthly
            res = clean_f.dropna(subset=[date_col, val_col])
            return res.resample('MS', on=date_col).mean().reset_index().rename(columns={date_col: 'Date', val_col: output_name})
        
        except Exception:
            # Ultimate Fallback: Try to find any column with dates and any with numbers
            raw_fallback = pd.read_excel(path, skiprows=10) # Standard FRED skip
            raw_fallback.columns = ['Date', output_name] + list(raw_fallback.columns[2:])
            raw_fallback['Date'] = pd.to_datetime(raw_fallback['Date'], errors='coerce')
            raw_fallback[output_name] = pd.to_numeric(raw_fallback[output_name], errors='coerce')
            return raw_fallback.dropna(subset=['Date', output_name])[['Date', output_name]]

    fx_inr = get_fx_robust(files["inr"], 'FX_India')
    fx_gbp = get_fx_robust(files["gbp"], 'FX_UK')
    fx_sgd = get_fx_robust(files["sgd"], 'FX_Singapore')

    # 2d. Combine
    df_macro['Year'] = df_macro['Date'].dt.year
    final_df = df_macro.merge(df_gdp, on='Year', how='left')
    for fx_df in [fx_inr, fx_gbp, fx_sgd]:
        final_df = final_df.merge(fx_df, on='Date', how='left')
        
    return final_df.sort_values('Date').dropna(subset=['Date'])

df = load_data()

# --- 3. UI LAYOUT ---
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>🏛️ Terminal Setup</h2>", unsafe_allow_html=True)
    market = st.selectbox("Select Market", ["India", "UK", "Singapore"])
    horizon = st.radio("Lookback", ["Historical", "10 Years", "5 Years"], index=1)
    scenario = st.selectbox("Simulation", ["Standard", "Stagflation 🌪️", "Depression 📉"])

m_map = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR/USD"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "USD/GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD/USD"}
}
m = m_map[market]

# Filter & Scenario
max_date = df['Date'].max()
if horizon == "10 Years": df = df[df['Date'] > (max_date - pd.DateOffset(years=10))]
elif horizon == "5 Years": df = df[df['Date'] > (max_date - pd.DateOffset(years=5))]

p_df = df.copy()
if "Stagflation" in scenario: p_df[m['cpi']] += 3.5; p_df[m['gdp']] -= 2.0

st.markdown(f"<div class='main-title'>MONETARY INTELLIGENCE: {market.upper()}</div>", unsafe_allow_html=True)

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Policy Rate", f"{p_df[m['p']].iloc[-1]:.2f}%")
c2.metric("CPI (YoY)", f"{p_df[m['cpi']].iloc[-1]:.2f}%")
c3.metric("GDP Growth", f"{p_df[m['gdp']].iloc[-1]:.1f}%")
c4.metric(f"FX: {m['sym']}", f"{p_df[m['fx']].iloc[-1]:.2f}")

# Main Chart
st.markdown("<div class='section-header'>I. Monetary & Currency Corridor</div>", unsafe_allow_html=True)
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Policy Rate (%)", line=dict(color='#1f77b4', width=3)), secondary_y=False)
fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name=f"FX Rate ({m['sym']})", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
fig.update_layout(template="plotly_white", height=500, margin=dict(t=20, b=20), legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.markdown(f"<div class='note-box'><b>💡 Analysis:</b> Market viewing {market} through a <b>{scenario}</b> lens. Data processed from institutional .xlsx sources.</div>", unsafe_allow_html=True)
