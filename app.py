import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. TERMINAL UI CONFIGURATION (DARK & GOLD) ---
st.set_page_config(page_title="Macro Terminal Pro", layout="wide")

st.markdown("""
    <style>
    /* Main App Background */
    .stApp {
        background-color: #0b0e14;
        color: #e0e0e0;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #12161d !important;
        border-right: 1px solid #d4af37;
    }

    /* Force visibility on labels and radio buttons */
    .stWidgetLabel, label, .stMarkdown p {
        color: #ffffff !important;
        font-weight: 500;
    }

    /* Gold Titles and Blue Headers */
    .main-title {
        color: #d4af37;
        font-size: 42px;
        font-weight: 800;
        text-transform: uppercase;
        border-bottom: 2px solid #d4af37;
        margin-bottom: 20px;
    }

    .note-header {
        color: #58a6ff;
        font-size: 20px;
        font-weight: bold;
        margin-top: 20px;
        border-left: 4px solid #58a6ff;
        padding-left: 10px;
    }

    .note-body {
        background-color: #1c2128;
        padding: 15px;
        border-radius: 5px;
        border: 1px solid #30363d;
        color: #c9d1d9;
        margin-bottom: 20px;
    }
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

    # 2a. Load Macro Data
    df_macro = pd.read_excel(files["workbook"], sheet_name='Macro data')
    df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
    
    # 2b. Load GDP (Correcting headers)
    df_gdp = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
    df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')

    # 2c. Robust FX Reader
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

    # 2d. Merge (Outer join to prevent data loss)
    df_macro['Year'] = df_macro['Date'].dt.year
    df = df_macro.merge(df_gdp, on='Year', how='left')
    for fx in [fx_inr, fx_gbp, fx_sgd]:
        df = df.merge(fx, on='Date', how='left')
    
    return df.sort_values('Date')

df = load_data()

# --- 3. SIDEBAR & LOGIC ---
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>CONTROL PANEL</h2>", unsafe_allow_html=True)
    market = st.selectbox("Market Focus", ["India", "UK", "Singapore"])
    horizon = st.radio("Time Horizon", ["5 Years", "10 Years", "Max Historical"], index=1)
    
m_map = {
    "India": {"p":"Policy_India", "cpi":"CPI_India", "gdp":"GDP_India", "fx":"FX_India", "lbl":"INR/USD"},
    "UK": {"p":"Policy_UK", "cpi":"CPI_UK", "gdp":"GDP_UK", "fx":"FX_UK", "lbl":"GBP/USD"},
    "Singapore": {"p":"Policy_Singapore", "cpi":"CPI_Singapore", "gdp":"GDP_Singapore", "fx":"FX_Singapore", "lbl":"SGD/USD"}
}
m = m_map[market]

# Date Filter
if horizon == "5 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]
elif horizon == "10 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]

# --- 4. MAIN INTERFACE ---
st.markdown(f"<div class='main-title'>{market} Macro Dashboard</div>", unsafe_allow_html=True)

# Top Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Policy Rate", f"{df[m['p']].iloc[-1]:.2f}%")
c2.metric("Inflation (CPI)", f"{df[m['cpi']].iloc[-1]:.2f}%")
c3.metric("GDP Growth", f"{df[m['gdp']].iloc[-1]:.1f}%")
c4.metric(f"FX: {m['lbl']}", f"{df[m['fx']].iloc[-1]:.2f}" if m['fx'] in df.columns else "N/A")

# --- GRAPHS ---
# Row 1: Policy & FX
st.markdown("<div class='note-header'>I. Monetary Policy vs Currency Stability</div>", unsafe_allow_html=True)
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Policy Rate (%)", line=dict(color='#58a6ff', width=3)), secondary_y=False)
fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="FX Rate", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400)
st.plotly_chart(fig1, use_container_width=True)

# Row 2: CPI & GDP
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("<div class='note-header'>II. Consumer Price Index (CPI)</div>", unsafe_allow_html=True)
    fig2 = go.Figure(go.Scatter(x=df['Date'], y=df[m['cpi']], fill='tozeroy', line=dict(color='#ff7b72')))
    fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
    st.plotly_chart(fig2, use_container_width=True)
with col_b:
    st.markdown("<div class='note-header'>III. Annual GDP Growth</div>", unsafe_allow_html=True)
    fig3 = go.Figure(go.Bar(x=df['Date'], y=df[m['gdp']], marker_color='#3fb950'))
    fig3.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
    st.plotly_chart(fig3, use_container_width=True)

# --- NOTES SECTION ---
st.markdown("<div class='note-header'>Methodological Note</div>", unsafe_allow_html=True)
st.markdown(f"""<div class='note-body'>
This terminal aggregates data from Federal Reserve Economic Data (FRED) and your internal master workbook. 
Current market: <b>{market}</b>. All currency data is resampled to monthly averages to match CPI frequency.
</div>""", unsafe_allow_html=True)

st.markdown("<div class='note-header'>Explanatory Note</div>", unsafe_allow_html=True)
st.markdown(f"""<div class='note-body'>
<b>Policy Rate:</b> Reflects central bank targets.<br>
<b>FX:</b> Quoted as {m['lbl']}.<br>
<b>GDP:</b> Sourced from annual worksheets and mapped to corresponding years.
</div>""", unsafe_allow_html=True)
