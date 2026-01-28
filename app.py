import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. GLOBAL STYLING (Light/Dark Neutral) ---
st.set_page_config(page_title="Strategic Macro Intelligence", layout="wide")

st.markdown("""
    <style>
    .stApp { background: #F8F9FA; color: #1A202C; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    .metric-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #EDF2F7; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; font-weight: 800; color: #2D3748; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUZZY DATA ENGINE ---
@st.cache_data
def load_macro_environment():
    try:
        # Load Macro File
        m_file = 'EM_Macro_Data_India_SG_UK.xlsx'
        xl_m = pd.ExcelFile(m_file)
        sheet = [s for s in xl_m.sheet_names if 'macro' in s.lower()][0]
        df_macro = xl_m.parse(sheet)
        df_macro.columns = [str(c).strip() for c in df_macro.columns]
        
        # Date Standardization
        date_col = [c for c in df_macro.columns if 'date' in c.lower()][0]
        df_macro[date_col] = pd.to_datetime(df_macro[date_col])
        
        # Load FX Files
        def load_fx(file):
            xl = pd.ExcelFile(file)
            s_name = 'observation' if 'observation' in xl.sheet_names else xl.sheet_names[-1]
            df = xl.parse(s_name)
            df.columns = ['date', 'val']
            df['val'] = pd.to_numeric(df['val'], errors='coerce')
            df['date'] = pd.to_datetime(df['date'])
            return df.dropna().sort_values('date')

        return {
            "Macro": df_macro, "date_key": date_col,
            "India": load_fx('DEXINUS.xlsx'),
            "UK": load_fx('DEXUSUK.xlsx'),
            "Singapore": load_fx('AEXSIUS.xlsx')
        }, None
    except Exception as e:
        return None, str(e)

env, err = load_macro_environment()
if err:
    st.error(f"📡 System Error: {err}")
    st.stop()

# --- 3. DYNAMIC COLUMN MAPPING (Fuzzy Search) ---
def get_cols(market, df_cols):
    # Find columns containing both 'Market' and 'Feature'
    def search(feature):
        candidates = [c for c in df_cols if market.lower() in c.lower() and feature.lower() in c.lower()]
        if not candidates: # Fallback: search just for feature
            candidates = [c for c in df_cols if feature.lower() in c.lower()]
        return candidates[0] if candidates else None

    return {
        "cpi": search("CPI") or search("Inflation"),
        "gdp": search("GDP") or search("Growth"),
        "rate": search("Rate") or search("Repo") or search("Policy")
    }

# --- 4. SCENARIO & CONTROLS ---
st.sidebar.title("🛂 Strategic Research Unit")
market = st.sidebar.selectbox("Market Analysis", ["India", "UK", "Singapore"])
cols = get_cols(market, env["Macro"].columns)

st.sidebar.divider()
st.sidebar.subheader("🎯 Macro Scenarios")
scen = st.sidebar.radio("Select Path", ["Base Case", "Hawkish Pivot", "Dovish Easing"])

# Simulation Parameters based on Scenarios
config = {
    "Base Case": {"r_star": 1.5, "fx_stress": 5.0, "beta": 0.25, "target": 2.0},
    "Hawkish Pivot": {"r_star": 2.5, "fx_stress": 12.0, "beta": 0.50, "target": 2.0},
    "Dovish Easing": {"r_star": 0.5, "fx_stress": 0.0, "beta": 0.10, "target": 3.0}
}
c = config[scen]

# --- 5. ANALYTICS ---
df_m = env["Macro"]
fx_df = env[market]
latest_m = df_m.dropna(subset=[cols['cpi'], cols['gdp'], cols['rate']]).iloc[-1]
latest_fx = fx_df.iloc[-1]['val']

# Open Economy Taylor Rule calculation
# i = r* + pi + 0.5(pi - target) + 0.5(GDP_Gap) + (FX_Shock * Beta)
inf = latest_m[cols['cpi']]
gdp = latest_m[cols['gdp']]
curr_rate = latest_m[cols['rate']]
pot_gdp = 5.0 if market == "India" else 2.5
gdp_gap = gdp - pot_gdp

fair_value = c['r_star'] + inf + 0.5*(inf - c['target']) + 0.5*gdp_gap + (c['fx_stress'] * c['beta'])
gap_bps = (fair_value - curr_rate) * 100

# --- 6. EXECUTIVE HUD ---
st.title(f"Strategic Policy Terminal: {market}")
st.caption(f"Scenario: {scen} | Model: Augmented Open-Economy Taylor Rule")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Repo Rate", f"{curr_rate:.2f}%")
col2.metric("CPI YoY", f"{inf:.2f}%")
col3.metric("GDP Growth", f"{gdp:.2f}%")
col4.metric("Taylor Implied", f"{fair_value:.2f}%")
col5.metric("Policy Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- 7. MULTIVARIATE RESEARCH GRAPH ---
st.subheader("Multivariate Transmission: Rates, Inflation & FX")
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Policy Rate
fig.add_trace(go.Scatter(x=df_m[env['date_key']], y=df_m[cols['rate']], name="Policy Rate", 
                         line=dict(color='#2B6CB0', width=4)), secondary_y=False)
# CPI
fig.add_trace(go.Scatter(x=df_m[env['date_key']], y=df_m[cols['cpi']], name="CPI Inflation", 
                         line=dict(color='#C53030', width=2, dash='dot')), secondary_y=False)
# GDP
fig.add_trace(go.Scatter(x=df_m[env['date_key']], y=df_m[cols['gdp']], name="GDP Growth", 
                         line=dict(color='#2F855A', width=2, dash='dash')), secondary_y=False)
# FX (Secondary Axis)
fig.add_trace(go.Scatter(x=fx_df['date'], y=fx_df['val'], name="Exchange Rate (RHS)", 
                         line=dict(color='#D69E2E', width=1, opacity=0.6)), secondary_y=True)

fig.update_layout(height=600, template="plotly_white", hovermode="x unified",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

# --- 8. RESEARCH COMMENTARY ---
st.divider()
ca, cb = st.columns(2)
with ca:
    st.subheader("📝 Strategic Outlook")
    st.write(f"""
    **Macro Stance:** The model indicates a **{abs(gap_bps):.0f} bps** deviation from the Taylor frontier. 
    In the **{scen}**, the transmission of FX volatility via a Beta of **{c['beta']}** necessitates 
    a {"higher" if gap_bps > 0 else "lower"} real rate buffer of **{(fair_value - inf):.2f}%**.
    """)

with cb:
    st.subheader("🔬 Transmission Channels")
    st.write(f"""
    - **Imported Inflation:** A {c['fx_stress']}% FX shock adds **{c['fx_stress']*c['beta']:.2f}%** to the CPI forecast.
    - **Output Gap:** GDP at {gdp}% vs Potential of {pot_gdp}% creates a **{gdp_gap:+.1f}%** output pressure.
    - **Policy Recommendation:** {"Accumulate short-end duration" if gap_bps < -50 else "Hedge against hawkish surprise" if gap_bps > 50 else "Maintain neutral duration exposure"}.
    """)
