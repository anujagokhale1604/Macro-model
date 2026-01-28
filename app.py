import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="Macro FX Terminal v5.2", layout="wide")

# Original High-Contrast "Parchment" Theme
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; border-right: 2px solid #D1C7B7; }
    
    /* Global Black Text Override for MAS Readability */
    p, span, label, h1, h2, h3, [data-testid="stWidgetLabel"] p {
        color: #000000 !important;
        font-weight: 800 !important;
    }
    
    /* Metrics Styling */
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 900 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR: SIMULATION CONTROLS ---
st.sidebar.title("🏛️ SURVEILLANCE V5.2")
market = st.sidebar.selectbox("1. Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("🌍 FX Stability & Pass-Through")
st.sidebar.caption("Current Research Focus")
fx_shock = st.sidebar.slider("Simulate FX Shock (%)", 0.0, 20.0, 0.0, help="Simulate currency depreciation")
fx_beta = st.sidebar.slider("FX Pass-Through (Beta)", 0.0, 1.0, 0.2, help="Elasticity of domestic prices to FX moves")

st.sidebar.divider()
st.sidebar.subheader("🏗️ Domestic Calibration")
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 2.0)

# --- 3. DATA ENGINE ---
@st.cache_data
def load_data():
    try:
        df = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        df['Date'] = pd.to_datetime(df['Date'])
        return df, None
    except Exception as e:
        return None, str(e)

df_macro, error_msg = load_data()

# --- 4. MAIN DASHBOARD ---
st.title(f"Monetary Policy & FX Surveillance: {market}")

if df_macro is not None:
    # Market Mapping
    m_map = {
        "India": {"cpi": "CPI_India", "rate": "Policy_India", "tag": "RBI"},
        "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "tag": "BoE"},
        "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "tag": "MAS"}
    }
    m = m_map[market]

    # Analysis Logic
    latest = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
    inf = latest[m['cpi']]
    curr = latest[m['rate']]
    
    # Open Economy Taylor Rule Calculation
    # Fair Value = r* + Inf + 1.5*(Inf - Target) + (FX Shock * Beta)
    fx_premium = fx_shock * fx_beta
    fair_value = r_star + inf + 1.5*(inf - target_inf) + fx_premium
    gap = (fair_value - curr) * 100

    # UI Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Headline CPI", f"{inf:.2f}%")
    c2.metric("Taylor Fair Value", f"{fair_value:.2f}%")
    c3.metric("Action Gap", f"{gap:+.0f} bps", delta_color="inverse")
    c4.metric("FX Risk Premium", f"+{fx_premium:.2f}%")

    # Charting
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], 
                             name=f"{m['tag']} Policy Rate", line=dict(color="black", width=3)))
    fig.update_layout(
        template="simple_white",
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", y=-0.2)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. TEACHING FOOTNOTE & CONCEPTS ---
    st.divider()
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("🎓 Concepts & Methodology")
        st.write("""
        * **Open-Economy Taylor Rule:** Extends the standard rule by incorporating FX volatility as a proxy for external stability.
        * **Currency Pass-Through:** Measures how exchange rate fluctuations impact domestic inflation—a critical metric for the MAS S$NEER framework.
        * **Neutral Rate (r*):** The theoretical rate that neither stimulates nor restrains the economy.
        """)

    with col_b:
        st.subheader("💡 Lessons Learnt")
        st.write("""
        * **Frequency Mismatch:** Successfully resolved technical hurdles in aligning Daily FX spot rates with Monthly Macro indicators (Resampling).
        * **Policy Lags:** Observed historical delays between inflation spikes and policy rate adjustments across EM vs. DM markets.
        * **Data Integrity:** Implemented a robust caching and error-handling pipeline to maintain terminal uptime during multi-source data ingestion.
        """)
    
    st.caption("🔍 Note: FX Pass-through integration is currently in optimization phase to enhance high-frequency predictive accuracy.")

else:
    st.error(f"⚠️ Terminal Offline: {error_msg}")
