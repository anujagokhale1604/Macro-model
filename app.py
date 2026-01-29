import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="📜")

# --- STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; border-right: 2px solid #D1C7B7 !important; }
    [data-testid="stWidgetLabel"] p, label p { color: #2E5077 !important; font-weight: 800 !important; }
    [data-testid="stMetricValue"] { color: #2E5077 !important; font-weight: 800; }
    html, body, .stMarkdown, p, li, span { color: #1A1C1E !important; font-family: 'Georgia', serif !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_all_data():
    file_main = 'EM_Macro_Data_India_SG_UK.xlsx'
    
    # 1. Load Macro & Policy Data (from "Macro data" sheet)
    # Titles: Date, CPI_India, CPI_Singapore, CPI_UK, Policy_India, Policy_UK, Policy_Singapore
    df_macro = pd.read_excel(file_main, sheet_name="Macro data")
    df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
    df_macro['Year'] = df_macro['Date'].dt.year

    # 2. Load GDP Growth (from "GDP_Growth" sheet)
    # Headers are messy, mapping exact indices: 0=Year, 2=India, 3=SGP, 4=GBR
    df_gdp_raw = pd.read_excel(file_main, sheet_name="GDP_Growth")
    df_gdp = df_gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
    df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
    df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')

    # 3. Load FX Data from separate files
    fx_data = {}
    fx_configs = {
        "India": ("DEXINUS.xlsx", "Daily", "DEXINUS"),
        "UK": ("DEXUSUK.xlsx", "Daily", "DEXUSUK"),
        "Singapore": ("AEXSIUS.xlsx", "Annual", "AEXSIUS")
    }
    
    for country, (fname, sname, col) in fx_configs.items():
        if os.path.exists(fname):
            tmp = pd.read_excel(fname, sheet_name=sname)
            tmp['observation_date'] = pd.to_datetime(tmp['observation_date'], errors='coerce')
            fx_data[country] = tmp.dropna(subset=['observation_date'])
        else:
            fx_data[country] = pd.DataFrame()

    # Merge Macro and GDP
    df_final = pd.merge(df_macro, df_gdp.dropna(subset=['Year']), on='Year', how='left')
    return df_final.dropna(subset=['Date']), fx_data

# Execute Loading
try:
    df, fx_dict = load_all_data()
except Exception as e:
    st.error(f"Critical Error Loading Excel Files: {e}")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

# EXACT TITLE MAPPING based on Sheet Inspection
titles = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "gdp": "GDP_India", "fx": "DEXINUS"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "gdp": "GDP_UK", "fx": "DEXUSUK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "gdp": "GDP_Singapore", "fx": "AEXSIUS"}
}
t = titles[market]

# --- SCENARIOS ---
st.sidebar.divider()
scenario = st.sidebar.selectbox("Choose Scenario", ["Baseline", "Soft Landing", "Stagflation", "Recession"])

if scenario == "Soft Landing": r_star, target_inf, gap = 1.5, 2.0, 0.5
elif scenario == "Stagflation": r_star, target_inf, gap = 2.5, 2.0, -2.5
elif scenario == "Recession": r_star, target_inf, gap = 0.5, 2.0, -4.0
else: r_star, target_inf, gap = 1.5, (4.0 if market == "India" else 2.0), 0.0

philosophy = st.sidebar.radio("Policy Framework", ["Standard", "Hawk", "Dovish"])
weights = {"Standard": 1.5, "Hawk": 2.2, "Dovish": 1.0}
inf_weight = weights[philosophy]

# --- CALCULATIONS ---
# Filter for specific market availability
valid_df = df.dropna(subset=[t['cpi'], t['rate']])
if valid_df.empty:
    st.warning(f"Note: Some recent data for {market} is missing in the file. Using last available points.")
    latest = df.sort_values('Date').iloc[-1]
else:
    latest = valid_df.sort_values('Date').iloc[-1]

inf_val = latest[t['cpi']]
rate_val = latest[t['rate']]
gdp_val = latest[t[ 'gdp']] if not pd.isna(latest[t['gdp']]) else 0.0

# Taylor Formula
fair_value = r_star + inf_val + inf_weight * (inf_val - target_inf) + 0.5 * gap
gap_bps = (fair_value - rate_val) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Intelligence")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{inf_val:.2f}%")
c2.metric("GDP Growth", f"{gdp_val:.1f}%")
c3.metric("Policy Rate", f"{rate_val:.2f}%")
c4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHARTING ---
fig = go.Figure()

# Core Metrics
fig.add_trace(go.Scatter(x=df['Date'], y=df[t['rate']], name="Policy Rate", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=df['Date'], y=df[t['cpi']], name="Inflation (YoY)", line=dict(color="#A68A64", dash='dot')))

# FX Rate (Secondary Axis)
fx_df = fx_dict[market]
if not fx_df.empty:
    fig.add_trace(go.Scatter(x=fx_df['observation_date'], y=fx_df[t['fx']], 
                             name="FX (RHS)", yaxis="y2", opacity=0.3, line=dict(color="#BC6C25")))

# Fair Value Marker
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=15, color='#BC6C25', symbol='diamond'), name="Model Anchor"))

fig.update_layout(
    height=550, template="simple_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    yaxis=dict(title="Rates / Inflation (%)", showgrid=True, gridcolor="#D1C7B7"),
    yaxis2=dict(title="Exchange Rate", overlaying="y", side="right", showgrid=False),
    legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center")
)
st.plotly_chart(fig, use_container_width=True)

# --- METHODOLOGY ---
st.divider()
st.subheader("📝 Methodology: The Taylor Rule")
st.latex(r"i_t = r^* + \pi_t + \alpha(\pi_t - \pi^*) + \beta(y_t - \bar{y}_t)")
st.markdown(f"""
The model calculates the 'Fair Value' of the interest rate by balancing the **Neutral Rate ({r_star}%)**, 
the **Inflation Gap ({inf_val - target_inf:.2f}%)**, and the **Output Gap ({gap}%)**. 
A positive deviation suggests the central bank is 'behind the curve' and may need to hike.
""")
