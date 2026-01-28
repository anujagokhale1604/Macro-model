import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- 1. SETTINGS ---
st.set_page_config(page_title="Macro FX Lab", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stWidgetLabel"] p, label p, h1, h2, h3 {
        color: #333333 !important; font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE AUTO-SCANNER ENGINE ---
@st.cache_data
def load_all_data():
    try:
        # 1. Load Primary Macro Data
        df = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df['Date'] = pd.to_datetime(df['Date'])
        
        # 2. Intelligent FRED Excel Scanner
        def scan_excel(filename):
            # Load the whole sheet to find the header
            raw = pd.read_excel(filename, header=None)
            # Find row index where 'observation_date' or 'date' exists
            header_row = 0
            for i, row in raw.iterrows():
                if any('date' in str(cell).lower() for cell in row):
                    header_row = i
                    break
            # Reload with the correct header row
            return pd.read_excel(filename, skiprows=header_row)

        inr_df = scan_excel('DEXINUS.xlsx')
        gbp_df = scan_excel('DEXUSUK.xlsx')
        sgd_df = scan_excel('AEXSIUS.xlsx')
        
        return df, inr_df, gbp_df, sgd_df, None
    except Exception as e:
        return None, None, None, None, str(e)

df_macro, df_inr, df_gbp, df_sgd, error_msg = load_all_data()

# --- 3. ERROR HANDLING ---
if error_msg:
    st.error(f"🛠️ **Data Link Broken:** {error_msg}")
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
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx": df_inr},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx": df_gbp},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx": df_sgd}
}

m = m_map[market]
fx_df = m['fx'].copy()

# Robust Column Identification
if len(fx_df.columns) < 2:
    st.error(f"⚠️ FX file for {market} is missing columns. Check file formatting.")
    st.stop()

date_col = next((c for c in fx_df.columns if 'date' in str(c).lower()), fx_df.columns[0])
val_col = next((c for c in fx_df.columns if c != date_col), fx_df.columns[1])

# Data Cleaning
fx_df[val_col] = pd.to_numeric(fx_df[val_col], errors='coerce')
fx_df[date_col] = pd.to_datetime(fx_df[date_col], errors='coerce')
fx_final = fx_df.dropna(subset=[val_col, date_col])

if fx_final.empty:
    st.warning(f"⚠️ No numeric FX data found for {market}. Verify the Excel sheet contains data rows.")
    st.stop()

current_fx = fx_final.iloc[-1]
latest_macro = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]

# Calculations
base_inf = latest_macro[m['cpi']]
curr_rate = latest_macro[m['rate']]
fx_val = current_fx[val_col]

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
fig.add_trace(go.Scatter(x=fx_final[date_col], y=fx_final[val_col], 
                         name="FX Rate (vs USD)", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    yaxis=dict(title="Policy Rate (%)"),
    yaxis2=dict(title="FX Rate", overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig, use_container_width=True)
