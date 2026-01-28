import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Strategic Macro Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #fdfdfd; }
    [data-testid="stMetricValue"] { color: #1a365d; font-weight: 800; }
    .stSidebar { background-color: #f8fafc !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (MULTI-SHEET SUPPORT) ---
@st.cache_data
def load_all_data():
    try:
        # A. LOAD MACRO DATA (Monthly CPI & Policy Rates)
        macro_xl = pd.ExcelFile('EM_Macro_Data_India_SG_UK.xlsx')
        df_macro = macro_xl.parse('Macro data')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        df_macro['Year'] = df_macro['Date'].dt.year

        # B. LOAD & CLEAN GDP GROWTH (Annual Data)
        df_gdp_raw = macro_xl.parse('GDP_Growth')
        # Based on your file: Col 0=Year, Col 2=IND, Col 3=SGP, Col 4=GBR
        df_gdp = df_gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
        df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')
        df_gdp = df_gdp.dropna(subset=['Year'])

        # C. MERGE GDP INTO MACRO (Join by Year)
        df_master = pd.merge(df_macro, df_gdp, on='Year', how='left')

        # D. LOAD FX FILES
        def load_fx(f):
            xl = pd.ExcelFile(f)
            # Take the last sheet (usually contains the data)
            df = xl.parse(xl.sheet_names[-1])
            # Standardize names
            df.columns = ['date', 'val']
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['val'] = pd.to_numeric(df['val'], errors='coerce')
            return df.dropna().sort_values('date')

        return {
            "Master": df_master,
            "India": load_fx('DEXINUS.xlsx'),
            "UK": load_fx('DEXUSUK.xlsx'),
            "Singapore": load_fx('AEXSIUS.xlsx')
        }, None
    except Exception as e:
        return None, str(e)

data, error = load_all_data()

if error:
    st.error(f"⚠️ Error Loading Data: {error}")
    st.info("Ensure all 4 Excel files (EM_Macro, DEXINUS, DEXUSUK, AEXSIUS) are in the same folder.")
    st.stop()

# --- 3. COLUMN MAPPING & SELECTION ---
st.sidebar.title("🛂 Macro Control Unit")
market = st.sidebar.selectbox("Jurisdiction", ["India", "UK", "Singapore"])

# Explicit mapping based on your actual Excel headers
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "gdp": "GDP_India", "fx": data["India"]},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "gdp": "GDP_UK", "fx": data["UK"]},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "gdp": "GDP_Singapore", "fx": data["Singapore"]}
}

m = m_map[market]
df = data["Master"]

# --- 4. POLICY SCENARIOS ---
st.sidebar.subheader("🎯 Policy Scenarios")
scen = st.sidebar.select_slider("Macro Stance", options=["Dovish", "Neutral", "Hawkish"], value="Neutral")
params = {
    "Hawkish": {"r_star": 2.5, "target": 2.0, "desc": "Inflation-targeting focus"},
    "Neutral": {"r_star": 1.5, "target": 2.5, "desc": "Equilibrium guidance"},
    "Dovish": {"r_star": 0.5, "target": 3.0, "desc": "Growth-supportive mode"}
}
p = params[scen]

# --- 5. ANALYTICS ---
# Check if selected columns exist
if m['cpi'] not in df.columns or m['rate'] not in df.columns or m['gdp'] not in df.columns:
    st.error(f"❌ Column headers mismatch for {market}.")
    st.write("Headers found:", list(df.columns))
    st.stop()

# Get latest data points
df_valid = df.dropna(subset=[m['cpi'], m['rate'], m['gdp']])
latest = df_valid.iloc[-1]

# Taylor Rule: Rate = r* + Inflation + 0.5(Inflation - Target) + 0.5(GDP - 3.0)
inf, curr_rate, gdp_val = latest[m['cpi']], latest[m['rate']], latest[m['gdp']]
target_rate = p['r_star'] + inf + 0.5*(inf - p['target']) + 0.5*(gdp_val - 3.0)
gap_bps = (target_rate - curr_rate) * 100

# --- 6. VISUAL DASHBOARD ---
st.title(f"🏛️ Institutional Policy Terminal: {market}")
st.markdown(f"**Strategy Focus:** `{p['desc']}`")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Actual Policy Rate", f"{curr_rate:.2f}%")
c2.metric("CPI Inflation", f"{inf:.2f}%")
c3.metric("Annual GDP Growth", f"{gdp_val:.2f}%")
c4.metric("Policy Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

# Main Multivariate Plot
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add Rates, CPI, and GDP
fig.add_trace(go.Scatter(x=df_valid['Date'], y=df_valid[m['rate']], name="Repo Rate", line=dict(color='#1e3a8a', width=3)))
fig.add_trace(go.Scatter(x=df_valid['Date'], y=df_valid[m['cpi']], name="CPI (YoY)", line=dict(color='#dc2626', dash='dot')))
fig.add_trace(go.Scatter(x=df_valid['Date'], y=df_valid[m['gdp']], name="GDP Growth", line=dict(color='#059669', dash='dash')))

# Add FX Rate on Secondary Axis
fx_df = m['fx']
fig.add_trace(go.Scatter(x=fx_df['date'], y=fx_df['val'], name="FX Rate (RHS)", opacity=0.3, line=dict(color='gray')), secondary_y=True)

fig.update_layout(height=500, template="simple_white", hovermode="x unified",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

# --- 7. STRATEGIC INSIGHT ---
st.divider()
st.subheader("📑 Macro Research Note")
stance = "behind the curve" if gap_bps > 50 else "ahead of the curve" if gap_bps < -50 else "appropriately positioned"
st.info(f"Analysis for **{market}**: The current policy gap of **{gap_bps:+.0f} bps** suggests the central bank is **{stance}** relative to a {scen.lower()} Taylor Rule benchmark.")
