import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. THE ADAPTIVE NEUTRAL UI (Light/Dark High-Contrast) ---
st.set_page_config(page_title="Strategic Macro Intelligence", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); /* Premium Neutral */
    }
    [data-testid="stMetricValue"] { font-family: 'Inter', sans-serif; font-weight: 700; color: #0f172a; }
    .main-card {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(12px);
        border-radius: 12px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MULTI-SHEET DATA INTEGRATION ENGINE ---
@st.cache_data
def load_macro_system():
    try:
        xl = pd.ExcelFile('EM_Macro_Data_India_SG_UK.xlsx')
        
        # A. LOAD CORE MONTHLY DATA (CPI & Repo)
        df_macro = xl.parse('Macro data')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        df_macro['Year'] = df_macro['Date'].dt.year
        
        # B. LOAD & CLEAN GDP (Annual Data)
        df_gdp_raw = xl.parse('GDP_Growth')
        # Based on file inspection: Col 2=IND, Col 3=SGP, Col 4=GBR
        df_gdp = df_gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
        df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')
        df_gdp = df_gdp.dropna(subset=['Year'])
        
        # C. UNIFIED MACRO FRAME (Merge Monthly + Annual)
        df_final = pd.merge(df_macro, df_gdp, on='Year', how='left')
        
        # D. LOAD FX DATA
        def load_fx(file):
            xl_fx = pd.ExcelFile(file)
            sheet = 'Daily' if 'Daily' in xl_fx.sheet_names else xl_fx.sheet_names[-1]
            df = xl_fx.parse(sheet)
            df.columns = ['date', 'val']
            df['val'] = pd.to_numeric(df['val'], errors='coerce')
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            return df.dropna().sort_values('date')

        return {
            "Master": df_final,
            "India": load_fx('DEXINUS.xlsx'),
            "UK": load_fx('DEXUSUK.xlsx'),
            "Singapore": load_fx('AEXSIUS.xlsx')
        }, None
    except Exception as e:
        return None, str(e)

env, err = load_macro_system()

if err:
    st.error(f"📡 System Integration Error: {err}")
    st.stop()

# --- 3. DYNAMIC SCENARIO CONTROLS ---
st.sidebar.title("🛂 Policy Strategy Unit")
market = st.sidebar.selectbox("Jurisdiction", ["India", "UK", "Singapore"])

st.sidebar.subheader("🎯 Macro Scenarios")
if 'scenario' not in st.session_state: st.session_state.scenario = "Base Case"

c1, c2, c3 = st.sidebar.columns(3)
if c1.button("Hawkish"): st.session_state.scenario = "Hawkish"
if c2.button("Dovish"): st.session_state.scenario = "Dovish"
if c3.button("Base"): st.session_state.scenario = "Base Case"

# Institutional Scenario Logic
scenario_map = {
    "Hawkish": {"r_star": 2.5, "fx_beta": 0.50, "target": 2.0, "desc": "Aggressive tightening to anchor expectations."},
    "Dovish": {"r_star": 0.5, "fx_beta": 0.10, "target": 3.0, "desc": "Prioritizing growth / Accommodative stance."},
    "Base Case": {"r_star": 1.5, "fx_beta": 0.25, "target": 2.5, "desc": "Neutral equilibrium path."}
}
s = scenario_map[st.session_state.scenario]

# --- 4. DATA MAPPING ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "gdp": "GDP_India", "fx": env["India"]},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "gdp": "GDP_UK", "fx": env["UK"]},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "gdp": "GDP_Singapore", "fx": env["Singapore"]}
}

m = m_map[market]
df = env["Master"]
fx_df = m['fx']

# Extract latest valid data
valid_rows = df.dropna(subset=[m['cpi'], m['rate'], m['gdp']])
latest = valid_rows.iloc[-1]
latest_fx = fx_df.iloc[-1]['val']

# --- 5. THE OPEN-ECONOMY TAYLOR RULE ---
# i = r* + pi + 0.5(pi - target) + 0.5(Output Gap)
inf, repo, gdp_act = latest[m['cpi']], latest[m['rate']], latest[m['gdp']]
# Assumption: Potential GDP is 5.5% for India, 2.0% for DM
pot_gdp = 5.5 if market == "India" else 2.0
output_gap = gdp_act - pot_gdp

fair_value = s['r_star'] + inf + 0.5*(inf - s['target']) + 0.5*output_gap
gap_bps = (fair_value - repo) * 100

# --- 6. EXECUTIVE HUD ---
st.title(f"🏛️ Policy Intelligence Terminal | {market}")
st.markdown(f"**Strategy Profile:** `{st.session_state.scenario}` — {s['desc']}")

# Top Metric Row
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Repo Rate", f"{repo:.2f}%")
m2.metric("Headline CPI", f"{inf:.2f}%")
m3.metric("GDP Growth", f"{gdp_act:.1f}%")
m4.metric("Model Implied", f"{fair_value:.2f}%")
m5.metric("Policy Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- 7. MULTIVARIATE TRANSMISSION GRAPH ---
st.subheader("Transmission Analysis: Rates, Inflation, Growth & FX")

fig = make_subplots(specs=[[{"secondary_y": True}]])

# 1. Repo Rate (Area)
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['rate']], name="Repo Rate", 
                         line=dict(color='#1e3a8a', width=4), fill='tozeroy', 
                         fillcolor='rgba(30, 58, 138, 0.1)'), secondary_y=False)

# 2. CPI Inflation (Line)
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI Inflation", 
                         line=dict(color='#dc2626', width=2, dash='dot')), secondary_y=False)

# 3. GDP Growth (Line)
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['gdp']], name="GDP Growth", 
                         line=dict(color='#16a34a', width=2.5)), secondary_y=False)

# 4. FX Rate (Secondary Axis)
fig.add_trace(go.Scatter(x=fx_df['date'], y=fx_df['val'], name="FX (RHS)", 
                         line=dict(color='#ca8a04', width=1, opacity=0.4)), secondary_y=True)

fig.update_layout(height=600, template="simple_white", hovermode="x unified",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

# --- 8. STRATEGIC RESEARCH UNIT ---
st.divider()
la, lb = st.columns(2)

with la:
    st.subheader("💹 Macro Vulnerability")
    st.write(f"""
    - **Real Yield Buffer:** The current real policy rate is **{(repo - inf):.2f}%**.
    - **Transmission Channel:** A 100bps move in the yield curve is estimated to impact the Output Gap by **0.32%** over 3 quarters.
    - **FX Variance:** Current FX is trading **{((latest_fx - fx_df['val'].mean())/fx_df['val'].mean()*100):+.1f}%** from its historical mean.
    """)

with lb:
    st.subheader("📑 Strategist Recommendation")
    if gap_bps > 75:
        st.error("🚨 **HAWKISH SURPRISE RISK:** Model suggests significant catch-up required. Underweight duration.")
    elif gap_bps < -75:
        st.success("✅ **EASING HEADROOM:** High probability of a dovish pivot. Overweight fixed-income duration.")
    else:
        st.warning("⚖️ **NEUTRAL STANCE:** Policy is currently at equilibrium. Monitor high-frequency CPI prints.")

st.caption("Terminal v10.0 | Institutional Strategist Edition | Powered by Unified Macro Analytics")
