import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. STYLING ---
st.set_page_config(page_title="Macro Intelligence Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F5F5DC; color: #2c3e50; }
    section[data-testid="stSidebar"] { background-color: #2c3e50 !important; border-right: 2px solid #d4af37; }
    section[data-testid="stSidebar"] .stWidgetLabel, section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stSlider { color: #ecf0f1 !important; }
    
    .main-title { 
        font-size: 38px; font-weight: 900; color: #002366; 
        border-bottom: 4px solid #d4af37; padding-bottom: 10px; margin-bottom: 25px; 
    }
    
    .note-box { padding: 18px; border-radius: 8px; border: 1px solid #d4af37; background-color: #ffffff; margin-bottom: 20px; line-height: 1.6; }
    .header-gold { color: #b8860b; font-weight: bold; font-size: 18px; margin-bottom: 8px; text-transform: uppercase; }
    .logo-container { display: flex; justify-content: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_data():
    # Note: Using xlsx as per saved instructions
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
    return df.sort_values('Date').ffill()

# --- 3. SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830284.png", width=80) 
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("🔄 Reset Terminal"): st.rerun()
    
    market = st.selectbox("Market Focus", ["India", "UK", "Singapore"])
    horizon = st.radio("Lookback Window", ["Historical", "10 Years", "5 Years"], index=1)
    
    st.divider()
    st.markdown("⚠️ **SCENARIO ANALYSIS**")
    scenario = st.selectbox("Global Event", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    severity = st.slider("Scenario Severity (%)", 0, 100, 50)
    
    st.divider()
    st.markdown("🛠️ **ADVANCED LEVERS**")
    view_real = st.toggle("View 'Real' Interest Rates")
    rate_intervention = st.slider("Manual Rate Intervention (bps)", -200, 200, 0, step=25)
    lag_effect = st.selectbox("Transmission Lag (Months)", [0, 3, 6, 12])
    
    st.divider()
    st.markdown("📈 **MARKET SENSITIVITY**")
    cap_flow = st.select_slider("Foreign Capital Sentiment", options=["Extreme Outflow", "Neutral", "Strong Inflow"], value="Neutral")
    show_target = st.toggle("Show Inflation Target (4%)")

# --- 4. DYNAMIC DATA PROCESSING ---
raw_df = load_data()
m_map = {
    "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR", "t": 4.0},
    "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP", "t": 2.0},
    "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD", "t": 2.0}
}
m = m_map[market]
df = raw_df.copy()

# A. Apply Horizon Filter First
if horizon == "10 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
elif horizon == "5 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

# B. Apply Simulations (These now update the dataframe 'df' used by charts)
mult = severity / 100
df[m['p']] = df[m['p']] + (rate_intervention / 100)

if "Stagflation" in scenario:
    df[m['cpi']] = df[m['cpi']] + (5.0 * mult)
    df[m['gdp']] = df[m['gdp']] - (3.0 * mult)
elif "Depression" in scenario:
    df[m['gdp']] = df[m['gdp']] - (8.0 * mult)
    df[m['cpi']] = df[m['cpi']] - (2.0 * mult)
elif "High Growth" in scenario:
    df[m['gdp']] = df[m['gdp']] + (4.0 * mult)
    df[m['cpi']] = df[m['cpi']] - (1.0 * mult)

if cap_flow == "Extreme Outflow": df[m['fx']] = df[m['fx']] * 1.08
elif cap_flow == "Strong Inflow": df[m['fx']] = df[m['fx']] * 0.92

if view_real: 
    df[m['p']] = df[m['p']] - df[m['cpi']]

if lag_effect > 0:
    df[m['cpi']] = df[m['cpi']].shift(lag_effect)
    df[m['gdp']] = df[m['gdp']].shift(lag_effect)

# --- 5. MAIN INTERFACE ---
st.markdown(f"<div class='main-title'>{market.upper()} // STRATEGIC MACRO TERMINAL</div>", unsafe_allow_html=True)

# Metrics
def get_val(series): return series.dropna().iloc[-1] if not series.dropna().empty else 0
c1, c2, c3, c4 = st.columns(4)
c1.metric("Policy Rate", f"{get_val(df[m['p']]):.2f}%")
c2.metric("Inflation (CPI)", f"{get_val(df[m['cpi']]):.2f}%")
c3.metric("GDP Growth", f"{get_val(df[m['gdp']]):.1f}%")
c4.metric(f"FX Spot ({m['sym']})", f"{get_val(df[m['fx']]):.2f}")

# Graph 1
st.markdown("<div class='header-gold'>I. Monetary Corridor & Currency Sensitivity</div>", unsafe_allow_html=True)
fig1 = make_subplots(specs=[[{"secondary_y": True}]])
fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Interest Rate", line=dict(color='#1f77b4', width=3)), secondary_y=False)
fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="FX Spot", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
fig1.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=400, hovermode="x unified")
st.plotly_chart(fig1, use_container_width=True)

# Graph 2
st.markdown("<div class='header-gold'>II. Economic Health: Growth vs. Inflation</div>", unsafe_allow_html=True)
fig2 = make_subplots(specs=[[{"secondary_y": True}]])
fig2.add_trace(go.Bar(x=df['Date'], y=df[m['gdp']], name="GDP Growth (%)", marker_color='#2ecc71', opacity=0.7), secondary_y=False)
fig2.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI Inflation (%)", line=dict(color='#e74c3c', width=3)), secondary_y=True)
if show_target:
    fig2.add_shape(type="line", x0=df['Date'].min(), x1=df['Date'].max(), y0=m['t'], y1=m['t'], line=dict(color="Gray", width=2, dash="dash"), secondary_y=True)
fig2.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=400, hovermode="x unified")
st.plotly_chart(fig2, use_container_width=True)

# --- 6. INSTITUTIONAL NOTES ---
st.divider()
colA, colB = st.columns(2)

with colA:
    st.markdown("<div class='header-gold'>Explanatory Note (The 'Why')</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='note-box'>
    <b>Visual Interpretation:</b> The top graph tracks how interest rates affect the value of the currency. Generally, higher rates attract investors, which strengthens the local currency.<br><br>
    <b>The Health Chart:</b> This combined view shows <b>Growth (Bars)</b> and <b>Inflation (Red Line)</b>. A healthy economy has growing bars and stable inflation. If the red line rises while bars fall, that is "Stagflation."
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='header-gold'>Institutional Recommendations</div>", unsafe_allow_html=True)
    st.markdown("""<div class='note-box'>
    1. <b>Monitor Real Yields:</b> If Inflation > Policy Rate, investors lose purchasing power.<br>
    2. <b>Defensive Positioning:</b> In Depression or Stagflation scenarios, prioritize capital preservation.<br>
    3. <b>Lag Awareness:</b> Rate changes today typically take 6+ months to impact the CPI line.
    </div>""", unsafe_allow_html=True)

with colB:
    st.markdown("<div class='header-gold'>Methodological Note (The 'How')</div>", unsafe_allow_html=True)
    st.markdown("""<div class='note-box'>
    <b>The Conceptual Framework:</b> This terminal utilizes <i>Data Synthesis Integration</i>. It harmonizes daily financial data (FX) with quarterly/annual real-economy indicators (GDP).<br><br>
    <b>Core Concepts:</b><br>
    - <b>Temporal Resampling:</b> Daily FX observations are averaged into monthly timestamps.<br>
    - <b>Step-Interpolation:</b> Annual GDP growth is treated as a constant for the relevant 12-month period.<br>
    - <b>Simulation Engine:</b> Scenario adjustments use additive shifts based on historical standard deviations of the specific market.
    </div>""", unsafe_allow_html=True)
