import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. Setup
st.set_page_config(page_title="MAS Terminal v5.1", layout="wide")

# 2. Sidebar (Your working toggles)
st.sidebar.title("🏛️ SURVEILLANCE TERMINAL V5.1")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 FX Stability (Work-in-Progress)")
fx_shock = st.sidebar.slider("Simulate FX Shock (%)", 0.0, 20.0, 0.0)
fx_beta = st.sidebar.slider("FX Pass-Through (Beta)", 0.0, 1.0, 0.2)

st.sidebar.divider()
st.sidebar.subheader("🏗️ Domestic Calibration")
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 2.0)

# 3. Data Loading (With Safety Check)
st.title("Monetary Policy & FX Surveillance")

@st.cache_data
def load_data():
    try:
        # Ensure openpyxl is in your requirements.txt
        df = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df['Date'] = pd.to_datetime(df['Date'])
        return df, None
    except Exception as e:
        return None, str(e)

df_macro, error_msg = load_data()

if df_macro is not None:
    # Mapping for the markets
    m_map = {
        "India": {"cpi": "CPI_India", "rate": "Policy_India"},
        "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
        "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
    }
    m = m_map[market]

    # Analytics
    latest = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
    inf = latest[m['cpi']]
    curr = latest[m['rate']]
    
    # Open Economy Taylor Rule Logic
    # Adding the FX shock to the inflation gap
    fx_premium = fx_shock * fx_beta
    fair_value = r_star + inf + 1.5*(inf - target_inf) + fx_premium
    gap = (fair_value - curr) * 100

    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Headline CPI", f"{inf:.2f}%")
    c2.metric("Taylor Fair Value", f"{fair_value:.2f}%")
    c3.metric("Action Gap", f"{gap:+.0f} bps", delta_color="inverse")

    # Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate", line=dict(color="black")))
    fig.update_layout(template="simple_white", hovermode="x unified", title=f"Historical Policy Path: {market}")
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("Note: FX data integration is currently being optimized for high-frequency resampling.")

else:
    st.error(f"Data Connection Error: {error_msg}")
    st.info("Check if 'EM_Macro_Data_India_SG_UK.xlsx' is in your GitHub root folder.")
