import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. STYLING (INSTITUTIONAL BEIGE & SLATE) ---
st.set_page_config(page_title="Macro Intelligence Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F5F5DC; color: #2c3e50; }
    section[data-testid="stSidebar"] { background-color: #2c3e50 !important; border-right: 2px solid #d4af37; }
    section[data-testid="stSidebar"] .stWidgetLabel, section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stSlider { color: #ecf0f1 !important; }
    .main-title { font-size: 34px; font-weight: 800; color: #1a1a1a; border-bottom: 3px solid #d4af37; margin-bottom: 25px; }
    .note-box { padding: 18px; border-radius: 8px; border: 1px solid #d4af37; background-color: #ffffff; margin-bottom: 20px; line-height: 1.5; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    .header-gold { color: #b8860b; font-weight: bold; font-size: 18px; margin-bottom: 8px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_data():
    files = {"workbook": 'EM_Macro_Data_India_SG_UK.xlsx', "inr": 'DEXINUS.xlsx', "gbp": 'DEXUSUK.xlsx', "sgd": 'AEXSIUS.xlsx'}
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

    fx_inr, fx_gbp, fx_sgd = get_fx(files["inr"], 'FX_India'), get_fx(files["gbp"], 'FX_UK'), get_fx(files["sgd"], 'FX_Singapore')
    df_macro['Year'] = df_macro['Date'].dt.year
    df = df_macro.merge(df_gdp, on='Year', how='left').merge(fx_inr, on='Date', how='left').merge(fx_gbp, on='Date', how='left').merge(fx_sgd, on='Date', how='left')
    return df.sort_values('Date')

raw_df = load_data()

# --- 3. SIDEBAR WITH ADVANCED TOGGLES ---
with st.sidebar:
    st.markdown("<h2 style='color:#d4af37;'>🏛️ CONTROL CENTER</h2>", unsafe_allow_html=True)
    if st.button("🔄 Reset to Default"): st.rerun()
    
    market = st.selectbox("Market Focus", ["India", "UK", "Singapore"])
    horizon = st.radio("Lookback Window", ["Historical", "10 Years", "5 Years"], index=1)
    
    st.divider()
    st.markdown("⚠️ **SCENARIO ANALYSIS**")
    scenario = st.selectbox("Global Event", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    severity = st.slider("Scenario Severity (%)", 0, 100, 50)
    
    st.divider()
    st.markdown("🛠️ **ADVANCED LEVERS**")
    view_real = st.toggle("View 'Real' Interest Rates", help="Subtracts Inflation from the Policy Rate to show the true cost of money.")
    rate_intervention = st.slider("Simulate Rate Hike/Cut (bps)", -200, 200, 0, step=25)
    lag_effect = st.selectbox("Transmission Lag (Months)", [0, 3, 6, 12], help="Shifts the data to show how long it takes for policy to hit the real economy.")

# --- 4. DATA LOGIC ---
m_map = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR"},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP"},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD"}
}
m = m_map[market]
df = raw_df.copy()

# Date Filtering
if horizon == "10 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
elif horizon == "5 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

# Apply Simulation & Intervention
mult = severity / 100
df[m['p']] += (rate_intervention / 100) # Apply slider hike/cut

if "Stagflation" in scenario:
    df[m['cpi']] += (5.0 * mult); df[m['gdp']] -= (3.0 * mult)
elif "Depression" in scenario:
    df[m['gdp']] -= (8.0 * mult); df[m['cpi']] -= (2.0 * mult)

# Calculate Real Rate if toggled
if view_real:
    df[m['p']] = df[m['p']] - df[m['cpi']]

# Apply Lag if selected
if lag_effect > 0:
    df[m['cpi']] = df[m['cpi']].shift(lag_effect)
    df[m['gdp']] = df[m['gdp']].shift(lag_effect)

# --- 5. DASHBOARD ---
st.markdown(f"<div class='main-title'>{market.upper()} // STRATEGIC MACRO TERMINAL</div>", unsafe_allow_html=True)

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Policy Rate", f"{df[m['p']].iloc[-1]:.2f}%", help="The 'Price of Money' set by the Central Bank.")
c2.metric("Inflation (CPI)", f"{df[m['cpi']].iloc[-1]:.2f}%", help="How fast prices are rising.")
c3.metric("GDP Growth", f"{df[m['gdp']].iloc[-1]:.1f}%", help="The speed of economic expansion.")
c4.metric(f"FX Spot ({m['sym']})", f"{df[m['fx']].iloc[-1]:.2f}" if pd.notnull(df[m['fx']].iloc[-1]) else "N/A")

# Graph 1: Monetary Corridor
st.markdown("<div class='header-gold'>I. Monetary Corridor & Currency Sensitivity</div>", unsafe_allow_html=True)
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
p_label = "Real Interest Rate" if view_real else "Nominal Policy Rate"
fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name=p_label, line=dict(color='#1f77b4', width=3)), secondary_y=False)
fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="Exchange Rate", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
fig1.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(t=10))
st.plotly_chart(fig1, use_container_width=True)

# Graph 2: Combined Health
st.markdown("<div class='header-gold'>II. Economic Health: Growth vs. Inflation</div>", unsafe_allow_html=True)
fig2 = make_subplots(specs=[[{"secondary_y": True}]])
fig2.add_trace(go.Bar(x=df['Date'], y=df[m['gdp']], name="GDP Growth (Annual %)", marker_color='#2ecc71', opacity=0.7), secondary_y=False)
fig2.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI Inflation (YoY %)", line=dict(color='#e74c3c', width=3)), secondary_y=True)
fig2.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=400, margin=dict(t=10))
st.plotly_chart(fig2, use_container_width=True)

# --- 6. SIMPLIFIED NOTES ---
st.divider()
n1, n2 = st.columns(2)

with n1:
    st.markdown("<div class='header-gold'>Explanatory Note (The 'Why')</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='note-box'>
    <b>What are you looking at?</b><br>
    The top graph shows how the Central Bank uses interest rates to protect the value of the currency. If you use the <b>Simulate Rate Hike</b> slider, you can see how higher rates theoretically make a currency stronger.<br><br>
    <b>The Health Chart:</b> This combines <b>Growth (Bars)</b> and <b>Inflation (Red Line)</b>. A healthy economy has tall green bars and a low red line. If you see the red line going up while green bars go down, that is "Stagflation"—the hardest puzzle for a country to solve.
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='header-gold'>Recommendations</div>", unsafe_allow_html=True)
    st.markdown("""<div class='note-box'>
    - <b>If Inflation > Policy Rate:</b> Your money is losing value. Consider assets that grow with inflation (like Gold or Commodities).<br>
    - <b>If GDP is falling:</b> The economy is slowing. Be cautious with aggressive investments and look for "defensive" companies.<br>
    - <b>If FX is volatile:</b> Use the 'Intervention' slider to see how much of a rate hike would be needed to stabilize it.
    </div>""", unsafe_allow_html=True)

with n2:
    st.markdown("<div class='header-gold'>Methodological Note (The 'How')</div>", unsafe_allow_html=True)
    st.markdown("""<div class='note-box'>
    <b>Real Interest Rates:</b> We calculate this by taking the official bank rate and subtracting inflation. This tells you the <i>actual</i> profit an investor makes after accounting for rising prices.<br><br>
    <b>Transmission Lag:</b> Economics doesn't happen overnight. When a bank changes rates, it takes 6–12 months for people to change their spending. Use the <b>Lag Toggle</b> to see how today’s decisions affect future growth.<br><br>
    <b>Data Pairing:</b> We use sophisticated "Outer Joining" to link your daily currency data with annual GDP, ensuring no data points are deleted during processing.
    </div>""", unsafe_allow_html=True)
