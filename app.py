import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- 1. SETTINGS ---
st.set_page_config(page_title="Macro Surveillance Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stWidgetLabel"] p, label p, h1, h2, h3 {
        color: #333333 !important; font-weight: 800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE ADAPTIVE DATA ENGINE ---
@st.cache_data
def load_and_clean_data():
    try:
        # 1. Main Macro File
        df_macro = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        
        # 2. Adaptive FX Loader
        # We target the specific sheet/file names found in your environment
        def load_fx(filename, sheet):
            # If the environment flattened the files, we use the specific sheet name
            df = pd.read_excel(filename, sheet_name=sheet)
            df.columns = ['date', 'val']
            df['val'] = pd.to_numeric(df['val'], errors='coerce')
            df['date'] = pd.to_datetime(df['date'])
            return df.dropna().reset_index(drop=True)

        # In your environment, the sheets are likely named after the frequency
        inr = load_fx('DEXINUS.xlsx', sheet='Daily')
        gbp = load_fx('DEXUSUK.xlsx', sheet='Daily')
        sgd = load_fx('AEXSIUS.xlsx', sheet='Annual')
        
        return (df_macro, inr, gbp, sgd), None
    except Exception as e:
        return None, str(e)

# Safe Unpacking
data_bundle, error_msg = load_and_clean_data()

if error_msg:
    st.error(f"🛠️ Connection Error: {error_msg}")
    st.info("Check if Excel files contain sheets named 'Daily' or 'Annual'.")
    st.stop()

df_macro, df_inr, df_gbp, df_sgd = data_bundle

# --- 3. UI & ANALYTICS ---
st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 External Toggles")
fx_shock = st.sidebar.slider("FX Depreciation (%)", 0.0, 15.0, 0.0)
beta = st.sidebar.slider("Pass-through (Beta)", 0.0, 1.0, 0.2)

m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx": df_inr},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx": df_gbp},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx": df_sgd}
}

m = m_map[market]
latest_macro = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
latest_fx = m['fx'].iloc[-1]

# Taylor Rule
r_star = 1.5
fair_value = r_star + latest_macro[m['cpi']] + 1.5*(latest_macro[m['cpi']] - 2.0) + (fx_shock * beta)
gap = (fair_value - latest_macro[m['rate']]) * 100

# --- 4. DISPLAY ---
st.title(f"{market} Surveillance Terminal")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest FX Rate", f"{latest_fx['val']:.2f}")
c2.metric("Headline CPI", f"{latest_macro[m['cpi']]:.2f}%")
c3.metric("Taylor Fair Value", f"{fair_value:.2f}%")
c4.metric("Action Gap", f"{gap:+.0f} bps", delta_color="inverse")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate (%)", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=m['fx']['date'], y=m['fx']['val'], name="Historical FX", yaxis="y2", line=dict(color="#BC6C25", dash='dot')))

fig.update_layout(
    yaxis=dict(title="Policy Rate (%)"),
    yaxis2=dict(title="FX Rate (vs USD)", overlaying="y", side="right"),
    legend=dict(orientation="h", y=-0.2),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
)
st.plotly_chart(fig, use_container_width=True)
