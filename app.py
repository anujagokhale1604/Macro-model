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
        background-color: rgba(150, 150, 150, 0.08); margin-bottom: 15px;
    }
    .section-header {
        color: #d4af37; font-variant: small-caps; font-size: 26px; font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE ULTIMATE DATA ENGINE ---
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
            st.error(f"⚠️ Missing file: `{path}`. Please ensure it is in your repository.")
            st.stop()

    # 2a. Main Macro & GDP Data
    df_macro = pd.read_excel(files["workbook"], sheet_name='Macro data')
    df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
    
    df_gdp = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
    df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')

    # 2b. Universal FX Loader (Handles any XLSX structure)
    def get_fx_universal(path, output_name):
        try:
            # Read all sheets; usually FRED data is on the first or second sheet
            xls = pd.ExcelFile(path)
            # Search for a sheet that likely contains data
            sheet_name = xls.sheet_names[0]
            for s in xls.sheet_names:
                if "observation" in s.lower() or "fred" in s.lower():
                    sheet_name = s
                    break
            
            # Read sheet without skipping to find the header row dynamically
            df_raw = pd.read_excel(path, sheet_name=sheet_name)
            
            # Find the row where 'observation_date' or a Date-like string exists
            header_row = 0
            for i, row in df_raw.head(20).iterrows():
                row_str = " ".join(str(val).lower() for val in row.values)
                if 'date' in row_str or 'observation' in row_str:
                    header_row = i + 1
                    break
            
            # Reload with the correct header
            df_clean = pd.read_excel(path, sheet_name=sheet_name, skiprows=header_row)
            df_clean.columns = [str(c).strip() for c in df_clean.columns]
            
            # Find the date column and value column by checking types
            date_col = None
            val_col = None
            
            for col in df_clean.columns:
                converted_date = pd.to_datetime(df_clean[col], errors='coerce')
                if converted_date.notnull().sum() > 5: # If column has actual dates
                    date_col = col
                    break
            
            for col in df_clean.columns:
                if col != date_col:
                    converted_val = pd.to_numeric(df_clean[col], errors='coerce')
                    if converted_val.notnull().sum() > 5:
                        val_col = col
                        break

            if date_col and val_col:
                df_clean[date_col] = pd.to_datetime(df_clean[date_col], errors='coerce')
                df_clean[val_col] = pd.to_numeric(df_clean[val_col], errors='coerce')
                df_clean = df_clean.dropna(subset=[date_col, val_col])
                
                # Resample to Monthly Mean
                return df_clean.resample('MS', on=date_col).mean().reset_index().rename(columns={date_col: 'Date', val_col: output_name})
            
            return pd.DataFrame(columns=['Date', output_name])
        except Exception:
            return pd.DataFrame(columns=['Date', output_name])

    fx_inr = get_fx_universal(files["inr"], 'FX_India')
    fx_gbp = get_fx_universal(files["gbp"], 'FX_UK')
    fx_sgd = get_fx_universal(files["sgd"], 'FX_Singapore')

    # 2c. Final Assembly
    df_macro['Year'] = df_macro['Date'].dt.year
    final = df_macro.merge(df_gdp, on='Year', how='left')
    for f in [fx_inr, fx_gbp, fx_sgd]:
        if not f.empty:
            final = final.merge(f, on='Date', how='left')
    
    return final.sort_values('Date').dropna(subset=['Date'])

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

# Filter
max_date = df['Date'].max()
if horizon == "10 Years": df = df[df['Date'] > (max_date - pd.DateOffset(years=10))]
elif horizon == "5 Years": df = df[df['Date'] > (max_date - pd.DateOffset(years=5))]

# Scenario Simulation
p_df = df.copy()
if "Stagflation" in scenario:
    p_df[m['cpi']] += 3.5; p_df[m['gdp']] -= 2.0
elif "Depression" in scenario:
    p_df[m['gdp']] -= 6.0

st.markdown(f"<div class='main-title'>MONETARY INTELLIGENCE: {market.upper()}</div>", unsafe_allow_html=True)

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Policy Rate", f"{p_df[m['p']].iloc[-1]:.2f}%")
c2.metric("CPI (YoY)", f"{p_df[m['cpi']].iloc[-1]:.2f}%")
c3.metric("GDP Growth", f"{p_df[m['gdp']].iloc[-1]:.1f}%")
c4.metric(f"FX: {m['sym']}", f"{p_df[m['fx']].iloc[-1]:.2f}" if m['fx'] in p_df.columns else "N/A")

# Main Chart
st.markdown("<div class='section-header'>I. Monetary & Currency Corridor</div>", unsafe_allow_html=True)
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['p']], name="Policy Rate (%)", line=dict(color='#1f77b4', width=3)), secondary_y=False)
if m['fx'] in p_df.columns:
    fig.add_trace(go.Scatter(x=p_df['Date'], y=p_df[m['fx']], name=f"FX Rate ({m['sym']})", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)

fig.update_layout(template="plotly_white", height=500, margin=dict(t=20, b=20), legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.markdown(f"<div class='note-box'><b>💡 Analysis:</b> Market viewing {market} through a <b>{scenario}</b> lens. Data is automatically parsed from .xlsx workbooks.</div>", unsafe_allow_html=True)
