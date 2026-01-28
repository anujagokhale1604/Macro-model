import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 1. CONFIGURATION & UI STYLE ---
st.set_page_config(page_title="Macro Policy Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; }
    .main-header { font-size: 2.2rem; font-weight: 800; color: #0f172a; margin-bottom: 0.5rem; }
    .metric-card { background: white; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; }
    [data-testid="stMetricValue"] { font-weight: 700; color: #1e40af; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA INTEGRATION ENGINE (OG MERGE LOGIC) ---
@st.cache_data
def load_and_merge_data():
    try:
        # Load Monthly Macro Data (Exact Filenames from your upload)
        df_macro = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - Macro data.csv')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        df_macro['Year'] = df_macro['Date'].dt.year
        
        # Load and Clean GDP Growth (Annual Data)
        df_gdp_raw = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - GDP_Growth.csv')
        # Mapping: Year (Col 0), India (Col 2), Singapore (Col 3), UK (Col 4)
        df_gdp = df_gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
        df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')
        for col in ['GDP_India', 'GDP_Singapore', 'GDP_UK']:
            df_gdp[col] = pd.to_numeric(df_gdp[col], errors='coerce')
        
        # Merge Annual GDP onto Monthly Data
        df_merged = pd.merge(df_macro, df_gdp.dropna(subset=['Year']), on='Year', how='left')
        return df_merged, None
    except Exception as e:
        return None, str(e)

df, error = load_and_merge_data()

if error:
    st.error(f"📡 Data Link Error: {error}")
    st.stop()

# --- 3. JURISDICTION & SCENARIO SELECTION ---
st.sidebar.title("🛂 Policy Control Unit")
market = st.sidebar.selectbox("Jurisdiction", ["India", "UK", "Singapore"])

st.sidebar.subheader("🎯 Macro Scenarios")
scen_choice = st.sidebar.radio("Policy Stance", ["Hawkish", "Neutral", "Dovish"])

# Central Bank Scenario Logic (Taylor Rule Inputs)
# Parameters: r_star (Neutral Rate), pi_target (Inflation Target)
scenarios = {
    "Hawkish": {"r_star": 2.5, "pi_target": 2.0, "label": "Tightening Bias / Inflation Fighting"},
    "Neutral": {"r_star": 1.5, "pi_target": 2.5, "label": "Equilibrium Policy Path"},
    "Dovish":  {"r_star": 0.5, "pi_target": 4.0, "label": "Growth Supportive / Accommodative"}
}
s = scenarios[scen_choice]

# --- 4. DATA MAPPING (FIXES KEYERROR) ---
# Map user selection to the exact column names in your CSV
mapping = {
    "India":     {"cpi": "CPI_India", "rate": "Policy_India", "gdp": "GDP_India", "pot": 5.5},
    "UK":        {"cpi": "CPI_UK", "rate": "Policy_UK", "gdp": "GDP_UK", "pot": 2.0},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "gdp": "GDP_Singapore", "pot": 2.5}
}
m = mapping[market]

# --- 5. TAYLOR RULE CALCULATION ---
# Get latest valid data row
latest = df.dropna(subset=[m['cpi'], m['rate'], m['gdp']]).iloc[-1]

inf = latest[m['cpi']]
repo = latest[m['rate']]
gdp_val = latest[m['gdp']]
pot_gdp = m['pot']

# Taylor Rule Formula: i = r* + pi + 0.5(pi - pi_target) + 0.5(GDP - Potential)
# i: Implied Nominal Policy Rate
implied_rate = s['r_star'] + inf + 0.5*(inf - s['pi_target']) + 0.5*(gdp_val - pot_gdp)
gap_bps = (implied_rate - repo) * 100

# --- 6. VISUAL TERMINAL ---
st.markdown(f"<div class='main-header'>🏛️ Macro Intelligence | {market}</div>", unsafe_allow_html=True)
st.write(f"**Current Stance:** `{s['label']}`")

# Metrics Display
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Current Rate", f"{repo:.2f}%")
with c2: st.metric("CPI Inflation", f"{inf:.2f}%")
with c3: st.metric("GDP Growth", f"{gdp_val:.1f}%")
with c4: st.metric("Taylor Implied", f"{implied_rate:.2f}%", delta=f"{gap_bps:+.0f} bps")

# Trend Chart
st.subheader("Policy vs. Fundamentals")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['rate']], name="Policy Rate", line=dict(color='#1e3a8a', width=4)))
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="Inflation", line=dict(color='#dc2626', dash='dot')))
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['gdp']], name="GDP Growth", line=dict(color='#16a34a', dash='dash')))

fig.update_layout(template="simple_white", height=500, hovermode="x unified",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

# --- 7. STRATEGIST "LEAN NOTE" & METHODOLOGY ---
st.divider()
col_note, col_method = st.columns([1, 1.2])

with col_note:
    st.subheader("📑 Strategist Lean Note")
    if gap_bps > 75:
        st.error(f"**Action: HAWKISH LEAN.** The model indicates policy is significantly behind the curve by **{gap_bps:+.0f} bps**. Expect upward pressure on yields.")
    elif gap_bps < -75:
        st.success(f"**Action: DOVISH LEAN.** Model identifies significant room for accommodation. Potential for policy easing in the coming quarters.")
    else:
