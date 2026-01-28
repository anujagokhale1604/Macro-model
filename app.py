import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- 1. SETTINGS ---
st.set_page_config(page_title="Macro FX Lab", layout="wide")

# High-contrast styling for MAS readability
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stWidgetLabel"] p, label p, h1, h2, h3 {
        color: #333333 !important; font-weight: 700 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE BRUTE-FORCE CLEANER ---
@st.cache_data
def load_all_data():
    try:
        # 1. Load Primary Macro Data
        df = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df['Date'] = pd.to_datetime(df['Date'])
        
        # 2. Intelligent Header & Data Cleaner
        def clean_excel_robust(filename):
            # Read everything
            raw = pd.read_excel(filename, header=None)
            
            # Find the header row (searching for 'date')
            header_row = 0
            for i, row in raw.iterrows():
                if any('date' in str(cell).lower() for cell in row):
                    header_row = i
                    break
            
            # Reload from that row
            df_temp = pd.read_excel(filename, skiprows=header_row)
            
            # Standardize column names
            date_col = next((c for c in df_temp.columns if 'date' in str(c).lower()), df_temp.columns[0])
            val_col = next((c for c in df_temp.columns if c != date_col), df_temp.columns[1])
            
            # BRUTE FORCE: Convert value column, forcing strings like 'ND' to NaN
            df_temp[val_col] = pd.to_numeric(df_temp[val_col], errors='coerce')
            df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors='coerce')
            
            # Drop any row that doesn't have a valid number AND a valid date
            df_clean = df_temp.dropna(subset=[val_col, date_col]).reset_index(drop=True)
            return df_clean, date_col, val_col

        inr_df, inr_d, inr_v = clean_excel_robust('DEXINUS.xlsx')
        gbp_df, gbp_d, gbp_v = clean_excel_robust('DEXUSUK.xlsx')
        sgd_df, sgd_d, sgd_v = clean_excel_robust('AEXSIUS.xlsx')
        
        return df, (inr_df, inr_d, inr_v), (gbp_df, gbp_d, gbp_v), (sgd_df, sgd_d, sgd_v), None
    except Exception as e:
        return None, None, None, None, str(e)

df_macro, inr_pkg, gbp_pkg, sgd_pkg, error_msg = load_all_data()

# --- 3. ERROR HANDLING ---
if error_msg:
    st.error(f"🛠️ **Critical Data Error:** {error_msg}")
    st.stop()

# --- 4. SIDEBAR ---
st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 External Stability Toggles")
fx_shock = st.sidebar.slider("Simulate FX Depreciation (%)", 0.0, 15.0, 0.0)
pass_through = st.sidebar.slider("Pass-through to Rates (Beta)", 0.0, 1.0, 0.2)

# --- 5. ANALYTICS ENGINE ---
# Extracting the packages
m_data = {"India": inr_pkg, "UK": gbp_pkg, "Singapore": sgd_pkg}
m_cols = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}

fx_df, date_col, val_col = m_data[market]
m = m_cols[market]

if fx_df.empty:
    st.error(f"⚠️ **Data Empty:** The cleaned dataset for {market} has 0 rows. This indicates the numeric data is not in the expected column.")
    st.stop()

# Get Latest Points
current_fx = fx_df.iloc[-1]
latest_macro = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]

base_inf = latest_macro[m['cpi']]
curr_rate = latest_macro[m['rate']]
fx_val = current_fx[val_col]

# Logic
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
fig.add_trace(go.Scatter(x=fx_df[date_col], y=fx_df[val_col], 
                         name="FX Rate (vs USD)", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    yaxis=dict(title="Policy Rate (%)"),
    yaxis2=dict(title="FX Rate", overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig, use_container_width=True)
