import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PREMIUM ADAPTIVE UI ---
st.set_page_config(page_title="Institutional Macro Terminal", layout="wide")

# Custom CSS for "Neutral Glassmorphism" - legible in all modes
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    [data-testid="stMetricValue"] { font-family: 'Inter', sans-serif; font-weight: 700; color: #1e293b; }
    .stSidebar { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #0f172a !important; font-family: 'Inter', sans-serif; }
    .stButton>button { border-radius: 8px; font-weight: 600; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MULTI-SHEET DATA ENGINE ---
@st.cache_data
def load_institutional_environment():
    try:
        # A. LOAD CORE MACRO (CPI & Policy)
        xl = pd.ExcelFile('EM_Macro_Data_India_SG_UK.xlsx')
        df_macro = xl.parse('Macro data')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        
        # B. LOAD & CLEAN GDP (Annual to Monthly Merge)
        df_gdp = xl.parse('GDP_Growth')
        # Map: India (Col 2), Singapore (Col 3), UK (Col 4)
        gdp_clean = df_gdp.iloc[1:, [0, 2, 3, 4]].copy()
        gdp_clean.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        gdp_clean['Year'] = pd.to_numeric(gdp_clean['Year'], errors='coerce')
        gdp_clean = gdp_clean.dropna(subset=['Year'])
        
        # Merge GDP into Macro using Year extraction
        df_macro['Year'] = df_macro['Date'].dt.year
        df_final = pd.merge(df_macro, gdp_clean, on='Year', how='left')
        
        # C. LOAD FX FILES
        def load_fx(f):
            xf = pd.ExcelFile(f)
            sheet = xf.sheet_names[-1] # Usually 'Daily' or 'observation'
            df = xf.parse(sheet)
            df.columns = ['date', 'val']
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['val'] = pd.to_numeric(df['val'], errors='coerce')
            return df.dropna().sort_values('date')

        return {
            "Master": df_final,
            "India": load_fx('DEXINUS.xlsx'),
            "UK": load_fx('DEXUSUK.xlsx'),
            "Singapore": load_fx('AEXSIUS.xlsx')
        }, None
    except Exception as e:
        return None, str(e)

data_env, error = load_institutional_environment()

if error:
    st.error(f"📡 Data Integration Error: {error}")
    st.stop()

# --- 3. STRATEGIC CONTROLS ---
st.sidebar.title("🛂 Policy Strategy Unit")
market = st.sidebar.selectbox("Jurisdiction", ["India", "UK", "Singapore"])

# Custom Scenario Logic
st.sidebar.subheader("🎯 Macro Scenarios")
if 'scenario' not in st.session_state: st.session_state.scenario = "Base Case"

col_a, col_b, col_c = st.sidebar.columns(3)
if col_a.button("Hawkish"): st.session_state.scenario = "Hawkish"
if col_b.button("Dovish"): st.session_state.scenario = "Dovish"
if col_c.button("Base"): st.session_state.scenario = "Base Case"

# Parameters for the Open-Economy Taylor Rule
scenarios = {
    "Hawkish": {"r_star": 2.5, "fx_beta": 0.45, "target": 2.0, "desc": "Aggressive inflation targeting."},
    "Dovish": {"r_star": 0.5, "fx_beta": 0.10, "target": 3.0, "desc": "Accommodative growth support."},
    "Base Case": {"r_star": 1.5, "fx_beta": 0.25, "target": 2.5, "desc": "Standard equilibrium path."}
}
s = scenarios[st.session_state.scenario]

# --- 4. ANALYTICS & MAPPING ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "gdp": "GDP_India", "fx": data_env["India"]},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "gdp": "GDP_UK", "fx": data_env["UK"]},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "gdp": "GDP_Singapore", "fx": data_env["Singapore"]}
}

m = m_map[market]
df = data_env["Master"]
fx_df = m['fx']

# Extract latest data points
latest_macro = df.dropna(subset=[m['cpi'], m['rate'], m['gdp']]).iloc[-1]
latest_fx = fx_df.iloc[-1]['val']

# THE TAYLOR RULE ENGINE: i = r* + pi + 0.5(pi - target) + 0.5(GDP - Pot_GDP)
inf = latest_macro[m['cpi']]
repo = latest_macro[m['rate']]
gdp_act = latest_macro[m['gdp']]
pot_gdp = 5.0 if market == "India" else 2.5 # Potential GDP assumptions

fair_val = s['r_star'] + inf + 0.5*(inf - s['target']) + 0.5*(gdp_act - pot_gdp)
gap_bps = (fair_val - repo) * 100

# --- 5. EXECUTIVE DASHBOARD ---
st.title(f"🏛️ Institutional Macro Terminal | {market}")
st.markdown(f"**Strategy Focus:** `{st.session_state.scenario}` — {s['desc']}")

# Top Row Metrics
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Current Repo", f"{repo:.2f}%")
c2.metric("CPI Inflation", f"{inf:.2f}%")
c3.metric("GDP Growth", f"{gdp_act:.2f}%")
c4.metric("Model Fair Value", f"{fair_val:.2f}%")
c5.metric("Policy Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- 6. MULTIVARIATE RESEARCH CHART ---
st.subheader("Transmission Dynamics: Interest Rates, Prices & GDP")
horizon = st.select_slider("Analysis Horizon", options=["5Y", "10Y", "Max"], value="Max")

fig = make_subplots(specs=[[{"secondary_y": True}]])

# Policy Rate Area
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['rate']], name="Repo Rate", 
                         line=dict(color='#1e3a8a', width=4), fill='tozeroy', fillcolor='rgba(30, 58, 138, 0.1)'))
# CPI
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI Inflation", line=dict(color='#dc2626', width=2, dash='dot')))
# GDP
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['gdp']], name="GDP Growth", line=dict(color='#16a34a', width=2, dash='dash')))
# FX (Secondary Axis)
fig.add_trace(go.Scatter(x=fx_df['date'], y=fx_df['val'], name="FX Rate (RHS)", 
                         line=dict(color='#ca8a04', width=1), opacity=0.5), secondary_y=True)

fig.update_layout(height=600, template="simple_white", hovermode="x unified",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

# --- 7. STRATEGIC COMMENTARY ---
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("💹 Monetary Buffer Analysis")
    st.write(f"""
    - **Real Rate:** The implied real policy rate is **{(repo - inf):.2f}%**.
    - **External Pass-through:** Under the `{st.session_state.scenario}`, currency volatility has a 
      **{s['fx_beta']*100}%** sensitivity to headline CPI.
    - **FX Context:** Current spot of **{latest_fx:.2f}** is trading against a cyclical average of **{fx_df['val'].mean():.2f}**.
    """)

with col_right:
    st.subheader("📑 Investment Implication")
    if gap_bps > 50:
        st.error("🚨 **BEHIND THE CURVE:** Potential for imminent hawkish surprises. Favor short-duration cash instruments.")
    elif gap_bps < -50:
        st.success("✅ **POLICY HEADROOM:** Conditions favor monetary easing. Bullish for fixed-income duration.")
    else:
        st.warning("⚖️ **NEUTRAL STANCE:** Policy is currently aligned with the Taylor frontier. Maintain benchmark exposure.")

st.caption("Terminal v10.0 | Institutional Research Architecture")
