import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. TERMINAL CONFIGURATION ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide")

# Neutral Professional Styling
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stMetricValue"] { color: #1e293b; font-weight: 700; }
    .stSidebar { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE: OG LOGIC + FX INTEGRATION ---
@st.cache_data
def load_and_merge_macro():
    try:
        # A. Load "OG" Monthly Macro Data (CPI & Policy Rates)
        # Using the specific CSV filenames provided in the environment
        df_macro = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - Macro data.csv')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        df_macro['Year'] = df_macro['Date'].dt.year

        # B. Load and Clean "OG" GDP Data
        df_gdp_raw = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - GDP_Growth.csv')
        # Year is Col 0, India=Col 2, SG=Col 3, UK=Col 4
        df_gdp = df_gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
        df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')
        df_gdp = df_gdp.dropna(subset=['Year'])

        # C. Merge Logic (Monthly Macro + Annual GDP)
        df_final = pd.merge(df_macro, df_gdp, on='Year', how='left')

        # D. Load FX Data
        def clean_fx(file, col_name):
            df = pd.read_csv(file)
            df.columns = ['date', 'val']
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['val'] = pd.to_numeric(df['val'], errors='coerce')
            return df.dropna().sort_values('date')

        fx_data = {
            "India": clean_fx('DEXINUS.xlsx - Daily.csv', 'INR'),
            "UK": clean_fx('DEXUSUK.xlsx - Daily.csv', 'GBP'),
            "Singapore": clean_fx('AEXSIUS.xlsx - Annual.csv', 'SGD') # Note: SG FX is annual in this dataset
        }

        return df_final, fx_data, None
    except Exception as e:
        return None, None, str(e)

df_master, fx_dict, err = load_and_merge_macro()

if err:
    st.error(f"❌ Data Load Error: {err}")
    st.stop()

# --- 3. JURISDICTION & STRATEGY CONTROLS ---
st.sidebar.title("🛂 Policy Strategy Unit")
country = st.sidebar.selectbox("Jurisdiction", ["India", "UK", "Singapore"])

# Scenarios / Toggles
st.sidebar.subheader("🎯 Macro Scenarios")
scen = st.sidebar.radio("Policy Stance", ["Base Case", "Hawkish", "Dovish"])

params = {
    "Base Case": {"r_star": 1.5, "target": 2.5, "desc": "Neutral Policy Path"},
    "Hawkish": {"r_star": 2.5, "target": 2.0, "desc": "Aggressive Inflation Anchor"},
    "Dovish": {"r_star": 0.5, "target": 3.5, "desc": "Pro-Growth Accommodation"}
}
p = params[scen]

# --- 4. COLUMN MAPPING (FIXES THE MISSING DATA ERROR) ---
# Map the country selection to the exact headers in your CSV
mapping = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "gdp": "GDP_India", "fx": fx_dict["India"]},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "gdp": "GDP_UK", "fx": fx_dict["UK"]},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "gdp": "GDP_Singapore", "fx": fx_dict["Singapore"]}
}

m = mapping[country]
fx_df = m['fx']

# --- 5. ANALYTICS (TAYLOR RULE) ---
# Filter data for calculations
calc_df = df_master.dropna(subset=[m['cpi'], m['rate'], m['gdp']])
latest = calc_df.iloc[-1]

inf = latest[m['cpi']]
repo = latest[m['rate']]
gdp_act = latest[m['gdp']]

# Output Gap Assumption: Potential growth (India 6%, DM 2%)
pot_gdp = 6.0 if country == "India" else 2.0
fair_val = p['r_star'] + inf + 0.5*(inf - p['target']) + 0.5*(gdp_act - pot_gdp)
gap_bps = (fair_val - repo) * 100

# --- 6. EXECUTIVE DASHBOARD ---
st.title(f"🏛️ Policy Intelligence Terminal | {country}")
st.caption(f"Strategy: {scen} — {p['desc']}")

# Metrics Row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Current Rate", f"{repo:.2f}%")
c2.metric("CPI Inflation", f"{inf:.2f}%")
c3.metric("GDP Growth", f"{gdp_act:.1f}%")
c4.metric("Policy Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- 7. MULTIVARIATE RESEARCH CHART ---
st.subheader("Transmission Dynamics: Rates, Prices, Growth & FX")

fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add OG Data (Rates, CPI, GDP)
fig.add_trace(go.Scatter(x=df_master['Date'], y=df_master[m['rate']], name="Policy Rate", 
                         line=dict(color='#1e3a8a', width=3)))
fig.add_trace(go.Scatter(x=df_master['Date'], y=df_master[m['cpi']], name="CPI (YoY)", 
                         line=dict(color='#dc2626', dash='dot')))
fig.add_trace(go.Scatter(x=df_master['Date'], y=df_master[m['gdp']], name="GDP Growth", 
                         line=dict(color='#16a34a', dash='dash')))

# Add New FX Data (Secondary Axis)
fig.add_trace(go.Scatter(x=fx_df['date'], y=fx_df['val'], name="FX Rate (RHS)", 
                         line=dict(color='#ca8a04', width=1), opacity=0.4), secondary_y=True)

fig.update_layout(height=600, template="simple_white", hovermode="x unified",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

st.plotly_chart(fig, use_container_width=True)

# --- 8. RESEARCH NOTES ---
st.divider()
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("💹 Macro Resilience")
    real_rate = repo - inf
    st.write(f"- **Real Policy Rate:** {real_rate:.2f}%")
    st.write(f"- **FX Deviation:** {country} currency is currently at {fx_df.iloc[-1]['val']:.2f}")

with col_b:
    st.subheader("📑 Strategist Outlook")
    if abs(gap_bps) < 50:
        st.success("✅ Policy is currently aligned with the Taylor frontier.")
    elif gap_bps > 50:
        st.error("🚨 Model suggests a hawkish bias is required to cool inflation.")
    else:
        st.warning("⚖️ Policy headroom exists for monetary easing.")

st.caption("Terminal v11.0 | Integrated Macro-Financial Framework")
