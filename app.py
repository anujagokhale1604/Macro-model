import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide")

# --- FILE FINDER UTILITY ---
def find_path(keywords):
    """Searches the current directory for a file containing all keywords."""
    for f in os.listdir("."):
        if all(k.lower() in f.lower() for k in keywords) and f.endswith('.xlsx'):
            return f
    return None

@st.cache_data
def load_and_sync_data():
    # 1. Macro Data (Dates, CPI, Rates)
    macro_file = find_path(['Macro', 'Data'])
    if not macro_file:
        st.error("❌ Could not find Macro Data file in repository.")
        st.stop()
    df_m = pd.read_xlsx(macro_file)
    df_m['Date'] = pd.to_datetime(df_m['Date'], errors='coerce')
    df_m['Year'] = df_m['Date'].dt.year

    # 2. GDP Data (Annual)
    gdp_file = find_path(['GDP', 'Growth'])
    if not gdp_file:
        st.error("❌ Could not find GDP Growth file in repository.")
        st.stop()
    # Skip messy headers: Col 0=Year, 2=India, 3=SG, 4=UK
    df_g = pd.read_csv(gdp_file).iloc[1:, [0, 2, 3, 4]]
    df_g.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    df_g['Year'] = pd.to_numeric(df_g['Year'], errors='coerce')

    # 3. FX Data
    fx_dict = {}
    fx_configs = {
        "India": (['DEXINUS'], 'DEXINUS'),
        "UK": (['DEXUSUK'], 'DEXUSUK'),
        "Singapore": (['AEXSIUS'], 'AEXSIUS')
    }
    for country, (keys, col) in fx_configs.items():
        path = find_path(keys)
        if path:
            f = pd.read_csv(path)
            # Standardize FX columns to 'date' and 'val'
            f.columns = ['date', 'val']
            f['date'] = pd.to_datetime(f['date'], errors='coerce')
            fx_dict[country] = f.dropna()
        else:
            fx_dict[country] = pd.DataFrame()

    # Merge Monthly Macro with Annual GDP
    df_final = pd.merge(df_m, df_g.dropna(subset=['Year']), on='Year', how='left')
    return df_final.dropna(subset=['Date']), fx_dict

# Load Data
df, fx_data = load_and_sync_data()

# --- SIDEBAR & MAPPING ---
st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

# Exact Header Mapping from your CSVs
titles = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "gdp": "GDP_India", "fx": "DEXINUS"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "gdp": "GDP_UK", "fx": "DEXUSUK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "gdp": "GDP_Singapore", "fx": "AEXSIUS"}
}
t = titles[market]

# --- TAYLOR RULE PARAMETERS ---
scenario = st.sidebar.selectbox("Macro Scenario", ["Baseline", "Soft Landing", "Stagflation", "Recession"])
if scenario == "Soft Landing": r_star, target_inf, gap = 1.5, 2.0, 0.5
elif scenario == "Stagflation": r_star, target_inf, gap = 2.5, 2.0, -2.5
elif scenario == "Recession": r_star, target_inf, gap = 0.5, 2.0, -4.0
else: r_star, target_inf, gap = 1.5, (4.0 if market == "India" else 2.0), 0.0

# --- CALCULATIONS ---
valid = df.dropna(subset=[t['cpi'], t['rate']])
latest = valid.sort_values('Date').iloc[-1]

inf_val = latest[t['cpi']]
rate_val = latest[t['rate']]
gdp_val = latest[t['gdp']]

# Taylor Formula: i = r* + pi + 1.5(pi - target) + 0.5(output_gap)
fair_value = r_star + inf_val + 1.5 * (inf_val - target_inf) + 0.5 * gap
gap_bps = (fair_value - rate_val) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Intelligence")
c1, c2, c3, c4 = st.columns(4)
c1.metric("CPI Inflation", f"{inf_val:.2f}%")
c2.metric("GDP Growth", f"{gdp_val:.1f}%")
c3.metric("Current Rate", f"{rate_val:.2f}%")
c4.metric("Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['Date'], y=df[t['rate']], name="Policy Rate", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=df['Date'], y=df[t['cpi']], name="Inflation", line=dict(color="#A68A64", dash='dot')))

# Secondary Axis for FX
fx_df = fx_data[market]
if not fx_df.empty:
    fig.add_trace(go.Scatter(x=fx_df['date'], y=fx_df['val'], name="FX (RHS)", yaxis="y2", opacity=0.3))

fig.update_layout(
    template="simple_white",
    yaxis2=dict(overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2)
)
st.plotly_chart(fig, use_container_width=True)

# --- METHODOLOGY ---
st.divider()
st.subheader("📝 Methodology")

st.latex(r"i_t = r^* + \pi_t + 1.5(\pi_t - \pi^*) + 0.5(y_t - \bar{y}_t)")
