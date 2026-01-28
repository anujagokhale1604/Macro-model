import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="Macro Policy Terminal v5.5", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; border-right: 2px solid #D1C7B7; }
    p, span, label, h1, h2, h3, [data-testid="stWidgetLabel"] p {
        color: #000000 !important; font-weight: 800 !important;
    }
    [data-testid="stMetricValue"] { color: #000000 !important; font-weight: 900 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR: THE COMMAND CENTER ---
st.sidebar.title("🏛️ TERMINAL v5.5")

# Reset Button
if st.sidebar.button("🔄 Reset to Default"):
    st.rerun()

market = st.sidebar.selectbox("1. Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("📉 Scenario Engine")
scenario = st.sidebar.selectbox("Select Macro Environment", 
                                ["Base Case", "Stagflation", "Soft Landing", "Hard Landing"])

st.sidebar.divider()
st.sidebar.subheader("🌍 FX & External Stability")
fx_shock = st.sidebar.slider("FX Shock (%)", 0.0, 20.0, 0.0)
fx_beta = st.sidebar.slider("FX Pass-Through (Beta)", 0.0, 1.0, 0.2)

st.sidebar.divider()
st.sidebar.subheader("🏗️ Policy Calibration")
# Hawkish/Dovish bias (Shift r*)
bias = st.sidebar.select_slider("Policy Bias", options=["Dovish", "Neutral", "Hawkish"], value="Neutral")
bias_map = {"Dovish": -0.5, "Neutral": 0.0, "Hawkish": 0.5}

r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5) + bias_map[bias]
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 2.0)

# Timeframe Filter
st.sidebar.divider()
st.sidebar.subheader("📅 Timeframe")
start_year = st.sidebar.slider("Start Year", 2000, 2024, 2015)

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
st.title(f"Macro Policy Surveillance: {market}")
st.write(f"**Mode:** {scenario} | **Policy Bias:** {bias}")

if df_macro is not None:
    # Filter Data by Timeframe
    df_filtered = df_macro[df_macro['Date'].dt.year >= start_year]

    m_map = {
        "India": {"cpi": "CPI_India", "rate": "Policy_India", "tag": "RBI"},
        "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "tag": "BoE"},
        "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "tag": "MAS"}
    }
    m = m_map[market]

    # Scenario Logic Overlays
    scenario_adj = {"Base Case": 0.0, "Stagflation": 1.5, "Soft Landing": -0.5, "Hard Landing": -1.2}
    
    latest = df_macro.dropna(subset=[m['cpi'], m['rate']]).iloc[-1]
    inf = latest[m['cpi']] + scenario_adj[scenario]
    curr = latest[m['rate']]
    
    # Open Economy Taylor Rule calculation
    fx_premium = fx_shock * fx_beta
    fair_value = r_star + inf + 1.5*(inf - target_inf) + fx_premium
    gap = (fair_value - curr) * 100

    # UI Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Headline CPI", f"{inf:.2f}%", delta=f"{scenario_adj[scenario]:+.1f}" if scenario != "Base Case" else None)
    c2.metric("Taylor Fair Value", f"{fair_value:.2f}%")
    c3.metric("Action Gap", f"{gap:+.0f} bps", delta_color="inverse")
    c4.metric("FX Risk Premium", f"+{fx_premium:.2f}%")

    # The Original Graph with Policy Rate
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_filtered['Date'], y=df_filtered[m['rate']], 
                             name="Actual Policy Rate", line=dict(color="black", width=3)))
    
    # Add a horizontal line for the simulated Fair Value
    fig.add_hline(y=fair_value, line_dash="dash", line_color="red", 
                  annotation_text="Simulated Fair Value", annotation_position="top right")

    fig.update_layout(
        template="simple_white", hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", y=-0.2)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. TEACHING SECTION (From Resume) ---
    st.divider()
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("🎓 Concepts & Methodology")
        st.write("""
        * **Open-Economy Taylor Rule:** Incorporates FX Risk Premiums to account for the 'Impossible Trinity.'
        * **S$NEER Logic:** For Singapore, the simulation emphasizes FX pass-through as the primary inflation anchor.
        * **Policy Bias:** Simulates 'Hawkish' or 'Dovish' tilts by adjusting the Neutral Rate (r*) floor.
        """)

    with col_b:
        st.subheader("💡 Lessons Learnt")
        st.write("""
        * **Frequency Resampling:** Resolved technical glitches in daily FX vs. monthly macro data synchronization.
        * **Dynamic Scenarios:** Built a multi-state engine to test policy resilience under Stagflation and Hard Landing shocks.
        * **UI/UX for Policy:** Designed for high-contrast readability (Parchment Theme) preferred in executive briefings.
        """)
    
    st.caption("🔍 Project Status: Actively optimizing high-frequency FX integration pipeline.")

else:
    st.error(f"⚠️ Terminal Offline: {error_msg}")
