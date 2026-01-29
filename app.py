import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="📜")

# --- FILE DISCOVERY HELPER ---
def find_file(keywords):
    """Finds a file in the current directory containing specific keywords."""
    for f in os.listdir("."):
        if all(k.lower() in f.lower() for k in keywords):
            return f
    return None

@st.cache_data
def load_and_sync_data():
    # 1. Find and Load Macro Data
    macro_path = find_file(['Macro', 'data'])
    if not macro_path:
        st.error("Could not find Macro Data CSV"); st.stop()
    df_macro = pd.read_csv(macro_path)
    df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
    df_macro['Year'] = df_macro['Date'].dt.year

    # 2. Find and Load GDP Growth
    gdp_path = find_file(['GDP', 'Growth'])
    if not gdp_path:
        st.error("Could not find GDP Growth CSV"); st.stop()
    df_gdp_raw = pd.read_csv(gdp_path)
    # The snippet shows headers are in row 0/1: IND is col 2, SGP is col 3, GBR is col 4
    df_gdp = df_gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
    df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')
    for col in ['GDP_India', 'GDP_Singapore', 'GDP_UK']:
        df_gdp[col] = pd.to_numeric(df_gdp[col], errors='coerce')

    # 3. Load FX Data
    fx_configs = {
        "India": (['DEXINUS'], 'DEXINUS'),
        "UK": (['DEXUSUK'], 'DEXUSUK'),
        "Singapore": (['AEXSIUS'], 'AEXSIUS')
    }
    fx_data = {}
    for country, (keys, col_name) in fx_configs.items():
        path = find_file(keys)
        if path:
            f = pd.read_csv(path)
            f['observation_date'] = pd.to_datetime(f['observation_date'], errors='coerce')
            f[col_name] = pd.to_numeric(f[col_name], errors='coerce')
            fx_data[country] = f.dropna()
        else:
            fx_data[country] = pd.DataFrame()

    df_final = pd.merge(df_macro, df_gdp.dropna(subset=['Year']), on='Year', how='left')
    return df_final.dropna(subset=['Date']), fx_data

# Execute Load
df, fx_dict = load_and_sync_data()

# --- SIDEBAR & UI ---
st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

# Exact Title Mapping from your CSV Headers
titles = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "gdp": "GDP_India", "fx": "DEXINUS"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "gdp": "GDP_UK", "fx": "DEXUSUK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "gdp": "GDP_Singapore", "fx": "AEXSIUS"}
}
t = titles[market]

# --- SCENARIOS ---
scenario = st.sidebar.selectbox("Macro Scenario", ["Baseline", "Soft Landing", "Stagflation", "Global Recession"])
if scenario == "Soft Landing": r_star, target_inf, gap = 1.5, 2.0, 0.5
elif scenario == "Stagflation": r_star, target_inf, gap = 2.5, 2.0, -2.5
elif scenario == "Global Recession": r_star, target_inf, gap = 0.5, 2.0, -4.0
else: r_star, target_inf, gap = 1.5, (4.0 if market == "India" else 2.0), 0.0

philosophy = st.sidebar.radio("Framework", ["Standard", "Hawk", "Dovish"])
weights = {"Standard": 1.5, "Hawk": 2.2, "Dovish": 1.0}
inf_weight = weights[philosophy]

# --- CALCULATIONS ---
valid_df = df.dropna(subset=[t['cpi'], t['rate']])
latest = valid_df.sort_values('Date').iloc[-1]

inf_val = latest[t['cpi']]
rate_val = latest[t['rate']]
gdp_val = latest[t['gdp']]

fair_value = r_star + inf_val + inf_weight * (inf_val - target_inf) + 0.5 * gap
gap_bps = (fair_value - rate_val) * 100

# --- DISPLAY ---
st.title(f"{market} Policy Intelligence")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{inf_val:.2f}%")
c2.metric("GDP Growth", f"{gdp_val:.1f}%")
c3.metric("Current Rate", f"{rate_val:.2f}%")
c4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=valid_df['Date'], y=valid_df[t['rate']], name="Policy Rate", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=valid_df['Date'], y=valid_df[t['cpi']], name="Inflation", line=dict(color="#A68A64", dash='dot')))

# FX Data (RHS Axis)
fx_df = fx_dict[market]
if not fx_df.empty:
    fig.add_trace(go.Scatter(x=fx_df['observation_date'], y=fx_df[t['fx']], name="FX (RHS)", yaxis="y2", opacity=0.3))

fig.update_layout(
    template="simple_white",
    yaxis2=dict(overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2)
)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("📝 Taylor Rule Equation")

st.latex(r"i_t = r^* + \pi_t + \alpha(\pi_t - \pi^*) + \beta(y_t - \bar{y}_t)")
