import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="Macro FX Lab", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stWidgetLabel"] p, label p, h1, h2, h3 {
        color: #333333 !important;
        font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (With Debugging) ---
@st.cache_data
def load_all_data():
    # Helper to check file existence
    def get_path(filename):
        if os.path.exists(filename):
            return filename
        # If exact match fails, try to find a similar name
        files = os.listdir('.')
        for f in files:
            if filename.split('.')[0] in f:
                return f
        return None

    try:
        # Load primary macro data
        df = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Load FX Data with flexible naming
        # These names match your previous error log exactly
        inr_df = pd.read_csv('DEXINUS.xlsx - Daily.csv', parse_dates=['observation_date'])
        gbp_df = pd.read_csv('DEXUSUK.xlsx - Daily.csv', parse_dates=['observation_date'])
        sgd_df = pd.read_csv('AEXSIUS.xlsx - Annual.csv', parse_dates=['observation_date'])
        
        return df, inr_df, gbp_df, sgd_df, None
    except Exception as e:
        return None, None, None, None, str(e)

df_macro, df_inr, df_gbp, df_sgd, error_msg = load_all_data()

# --- 3. ERROR HANDLING UI ---
if error_msg:
    st.error(f"🛠️ **Data Link Broken:** {error_msg}")
    st.info("Searching for files in your repository...")
    st.write("Found these files on GitHub:", os.listdir('.'))
    st.stop()

# --- 4. SIDEBAR ---
st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 External Stability Toggles")
fx_shock = st.sidebar.slider("Simulate FX Depreciation (%)", 0.0, 15.0, 0.0)
pass_through = st.sidebar.slider("Pass-through to Rates (Beta)", 0.0, 1.0, 0.2)

# --- 5. ANALYTICS ENGINE ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx": df_inr, "fx_col": "DEXINUS"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx": df_gbp, "fx_col": "DEXUSUK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx": df_sgd, "fx_col": "AEXSIUS"}
}

m = m_map[market]
latest_macro = df_macro.dropna(subset=[m['cpi']]).iloc[-1]
latest_fx = m['fx'].dropna(subset=[m['fx_col']]).iloc[-1]

base_inf = latest_macro[m['cpi']]
curr_rate = latest_macro[m['rate']]
fx_val = latest_fx[m['fx_col']]

# FX-Adjusted Taylor Rule
fair_value = 1.5 + base_inf + 1.5*(base_inf - 2.0) + (fx_shock * pass_through)
gap_bps = (fair_value - curr_rate) * 100

# --- 6. DASHBOARD ---
st.title(f"{market} Policy & FX Terminal")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current FX Rate", f"{fx_val:.2f}")
col2.metric("Headline CPI", f"{base_inf:.2f}%")
col3.metric("Model Fair Value", f"{fair_value:.2f}%")
col4.metric("Action Gap", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- 7. DUAL AXIS CHART ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=m['fx']['observation_date'], y=m['fx'][m['fx_col']], 
                         name="FX Rate (vs USD)", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    yaxis=dict(title="Policy Rate (%)"),
    yaxis2=dict(title="FX Rate", overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig, use_container_width=True)

if fx_shock > 0:
    st.warning(f"⚠️ **External Risk:** A {fx_shock}% currency depreciation requires an additional {fx_shock * pass_through:.2f}% rate hike to maintain capital parity.")
