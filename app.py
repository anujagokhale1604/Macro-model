import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. PREMIUM TERMINAL STYLING ---
st.set_page_config(page_title="Macro Terminal Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    
    /* Background and Global Font */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    
    html, body, [class*="css"], .stMarkdown, p, span {
        font-family: 'Inter', sans-serif !important;
    }

    /* Gold Accents for Titles */
    .main-title {
        font-size: 42px;
        font-weight: 800;
        color: #d4af37;
        letter-spacing: -1px;
        border-bottom: 1px solid #333;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }

    /* Metric Cards */
    [data-testid="stMetricValue"] {
        color: #d4af37 !important;
        font-family: 'JetBrains Mono', monospace;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #333;
    }

    /* Custom Note Box */
    .terminal-card {
        padding: 20px;
        border-radius: 8px;
        background-color: #1c2128;
        border: 1px solid #30363d;
        color: #8b949e;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    
    .section-header {
        color: #58a6ff;
        font-family: 'JetBrains Mono', monospace;
        font-size: 14px;
        text-transform: uppercase;
        margin-top: 30px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ROBUST DATA ENGINE ---
@st.cache_data
def load_data():
    files = {
        "workbook": 'EM_Macro_Data_India_SG_UK.xlsx',
        "inr": 'DEXINUS.xlsx',
        "gbp": 'DEXUSUK.xlsx',
        "sgd": 'AEXSIUS.xlsx'
    }
    
    # 2a. Main Workbook Processing
    try:
        df_macro = pd.read_excel(files["workbook"], sheet_name='Macro data')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
        
        gdp = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
        gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        gdp['Year'] = pd.to_numeric(gdp['Year'], errors='coerce')
    except Exception as e:
        st.error(f"Error loading main workbook: {e}")
        st.stop()

    # 2b. FX Loader (Targets 'Daily' or 'Annual' sheets specifically)
    def get_fx(path, output_name):
        try:
            xls = pd.ExcelFile(path)
            # Find the sheet that isn't 'README'
            data_sheet = [s for s in xls.sheet_names if s != 'README'][0]
            f = pd.read_excel(path, sheet_name=data_sheet)
            
            # Identify columns
            date_col = [c for c in f.columns if 'date' in c.lower()][0]
            val_col = [c for c in f.columns if c != date_col][0]
            
            f[date_col] = pd.to_datetime(f[date_col], errors='coerce')
            f[val_col] = pd.to_numeric(f[val_col], errors='coerce')
            f = f.dropna(subset=[date_col, val_col])
            
            # Resample to Monthly
            return f.resample('MS', on=date_col).mean().reset_index().rename(columns={date_col: 'Date', val_col: output_name})
        except:
            return pd.DataFrame(columns=['Date', output_name])

    fx_inr = get_fx(files["inr"], 'FX_India')
    fx_gbp = get_fx(files["gbp"], 'FX_UK')
    fx_sgd = get_fx(files["sgd"], 'FX_Singapore')

    # 2c. Merge Logic
    df_macro['Year'] = df_macro['Date'].dt.year
    df = df_macro.merge(gdp, on='Year', how='left')
    for fx in [fx_inr, fx_gbp, fx_sgd]:
        df = df.merge(fx, on='Date', how='left')
    
    return df.sort_values('Date').dropna(subset=['Date'])

df = load_data()

# --- 3. SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>CMD: TERMINAL</h2>", unsafe_allow_html=True)
    market = st.selectbox("Market Selection", ["India", "UK", "Singapore"])
    horizon = st.radio("Lookback Window", ["Max Historical", "10 Years", "5 Years"], index=1)
    scenario = st.select_slider("Stress Test Scenario", 
                               options=["Deflationary", "Standard", "Stagflation", "Hypergrowth"])

# Mapping Data
m_map = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR/USD"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP/USD"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD/USD"}
}
m = m_map[market]

# Horizon Filter
max_date = df['Date'].max()
if horizon == "10 Years":
    df = df[df['Date'] > (max_date - pd.DateOffset(years=10))]
elif horizon == "5 Years":
    df = df[df['Date'] > (max_date - pd.DateOffset(years=5))]

# Scenario Logic
p_df = df.copy()
if scenario == "Stagflation":
    p_df[m['cpi']] *= 1.4
    p_df[m['gdp']] -= 2.5
elif scenario == "Deflationary":
    p_df[m['cpi']] -= 2.0
    p_df[m['p']] *= 0.5

# --- 4. MAIN DASHBOARD ---
st.markdown(f"<div class='main-title'>{market.upper()} // MACRO ANALYTICS</div>", unsafe_allow_html=True)

# Top Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Policy Rate", f"{p_df[m['p']].iloc[-1]:.2f}%")
m2.metric("Inflation (YoY)", f"{p_df[m['cpi']].iloc[-1]:.2f}%")
m3.metric("GDP Growth", f"{p_df[m['gdp']].iloc[-1]:.1f}%")
m4.metric(f"FX: {m['sym']}", f"{p_df[m['fx']].iloc[-1]:.2f}" if m['fx'] in p_df.columns else "---")

# Visualizations
st.markdown("<div class='section-header'>> MONETARY CORRIDOR & CURRENCY STABILITY</div>", unsafe_allow_html=True)

fig = make_subplots(specs=[[{"secondary_y": True}]])

# Policy Rate Area
fig.add_trace(go.Scatter(
    x=p_df['Date'], y=p_df[m['p']], 
    name="Policy Rate", fill='tozeroy',
    line=dict(color='#58a6ff', width=2)
), secondary_y=False)

# FX Rate Line
if m['fx'] in p_df.columns:
    fig.add_trace(go.Scatter(
        x=p_df['Date'], y=p_df[m['fx']], 
        name=f"FX ({m['sym']})", 
        line=dict(color='#d4af37', width=3, dash='dot')
    ), secondary_y=True)

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    height=500,
    margin=dict(l=20, r=20, t=20, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# Footer Analysis
st.divider()
c1, c2 = st.columns(2)
with c1:
    st.markdown(f"""
    <div class='terminal-card'>
    <b>CORE ANALYSIS:</b><br>
    The {market} dashboard is currently processing institutional data via 
    automated XLSX ingestion. Under the <b>{scenario}</b> scenario, we observe 
    divergence between the interest rate policy and real GDP output.
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class='terminal-card'>
    <b>SYSTEM STATUS:</b><br>
    - Data Source: Global Macro Workbooks (.xlsx)<br>
    - Parsing: Dynamic Header Detection Enabled<br>
    - Theme: Institutional Dark (Terminal Gold)
    </div>
    """, unsafe_allow_html=True)
