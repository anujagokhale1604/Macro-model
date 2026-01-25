import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide", page_icon="🏛️")

# FORCED VISIBILITY & CLEAN UI CSS
st.markdown("""
    <style>
    /* Force Widget Labels to be Dark/Visible */
    .stWidgetLabel p, .stSlider label, .stSelectbox label, .stRadio label {
        color: #1A1C1E !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }
    .main { background-color: #fcfcfc; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #eeeeee;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    if not os.path.exists(file_name):
        st.error("Data source missing."); st.stop()
    xl = pd.ExcelFile(file_name)
    df = pd.read_excel(xl, sheet_name="Macro data")
    df.columns = [str(c).strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df.dropna(subset=['Date']).sort_values('Date')

df = load_data()

# --- SIDEBAR: POLICY CONTROLS ---
st.sidebar.title("🎮 Policy Simulation")
market = st.sidebar.selectbox("Market Focus", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("📅 Data Horizon")
horizon = st.sidebar.radio("View Period", ["Last 1 Year", "Last 5 Years", "Full History"], index=1)

st.sidebar.divider()
scenario = st.sidebar.selectbox("Macro Scenario Presets", 
    ["Custom", "Soft Landing", "Stagflation Shock", "Global Recession"])

# Logic for Scenario Presets
if scenario == "Soft Landing":
    r_star, target_inf, output_gap, inf_weight, smoothing = 1.5, 2.0, 0.5, 1.2, 0.3
elif scenario == "Stagflation Shock":
    r_star, target_inf, output_gap, inf_weight, smoothing = 2.5, 2.0, -2.0, 2.0, 0.1
elif scenario == "Global Recession":
    r_star, target_inf, output_gap, inf_weight, smoothing = 0.5, 2.0, -4.0, 0.8, 0.5
else:
    # Custom Toggles
    r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)
    target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 4.0 if market == "India" else 2.0)
    output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, 0.0)
    inf_weight = st.sidebar.slider("Inflation Weight (λπ)", 0.5, 2.0, 1.5)
    smoothing = st.sidebar.slider("Rate Smoothing Factor", 0.0, 1.0, 0.2)

# --- ANALYTICS ENGINE ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])

# Timeline Filtering
latest_date = valid_df['Date'].max()
if horizon == "Last 1 Year":
    start_point = latest_date - timedelta(days=365)
elif horizon == "Last 5 Years":
    start_point = latest_date - timedelta(days=5*365)
else:
    start_point = valid_df['Date'].min()

filtered_df = valid_df[valid_df['Date'] >= start_point]
latest = valid_df.iloc[-1]

# Calculations
inf = latest[m['cpi']]
curr_rate = latest[m['rate']]

# Advanced Taylor Rule with Weights: i = r* + pi + λπ(pi - target) + 0.5(output_gap)
raw_fv = r_star + inf + inf_weight * (inf - target_inf) + 0.5 * (output_gap)

# Apply Smoothing: (1-ρ)*FV + ρ*Current
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap = fair_value - curr_rate

# --- DASHBOARD LAYOUT ---
st.title(f"🚀 {market} Policy Terminal")
st.markdown(f"**Scenario:** `{scenario}` | **Smoothing:** `{smoothing}` | **As Of:** {latest['Date'].strftime('%B %Y')}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Headline CPI", f"{inf:.2f}%")
m2.metric("Policy Rate", f"{curr_rate:.2f}%")
m3.metric("Taylor Fair Value", f"{fair_value:.2f}%")
m4.metric("Policy Gap", f"{gap*100:+.0f} bps", delta_color="inverse")

# Main Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Historical Policy Rate", line=dict(color="#0052cc", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="Headline CPI", line=dict(color="#ff4b4b", width=1.5, dash='dot')))
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=18, color='#ffc107', symbol='star', line=dict(width=1, color='black')),
                         name="Terminal Rate Suggestion"))

fig.update_layout(
    height=420, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", y=1.1, x=0),
    xaxis=dict(showgrid=True, gridcolor="#f5f5f5"),
    yaxis=dict(showgrid=True, gridcolor="#f5f5f5", title="Percent (%)")
)
st.plotly_chart(fig, use_container_width=True)

# --- INSIGHTS SECTION ---
st.divider()

if gap > 0.5:
    sig, col, bg = "HAWKISH BIAS", "#d32f2f", "#fff5f5"
    msg = "The policy rate is trailing fundamentals. Data suggests a tightening bias is required to anchor inflation expectations."
elif gap < -0.5:
    sig, col, bg = "DOVISH PIVOT", "#2e7d32", "#f5fff5"
    msg = "Current rates are restrictive relative to the model. Conditions support a transition toward monetary easing."
else:
    sig, col, bg = "NEUTRAL / CALIBRATED", "#455a64", "#f8f9fa"
    msg = "The current stance is appropriately calibrated to the prevailing inflation and growth outlook."

left, right = st.columns([2, 1])

with left:
    st.markdown(f"""
    <div style="background-color: {bg}; border: 1px solid {col}; border-left: 10px solid {col}; padding: 25px; border-radius: 10px; color: #1A1C1E;">
        <h3 style="color: {col}; margin-top: 0;">Market Stance: {sig}</h3>
        <p style="font-size: 1.15rem; line-height: 1.6;">{msg}</p>
        <hr style="opacity: 0.2;">
        <p style="font-size: 0.95rem;"><strong>Quantitative Assessment:</strong> The gap is <strong>{gap*100:.0f} basis points</strong>. 
        This is modeled using a {inf_weight}x weight on inflation deviations and a {smoothing} smoothing factor.</p>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("🏛️ Institutional Context")
    st.markdown(f"""
    **The Policy Trilemma**
    
    Central banks in Emerging Markets, particularly **{market}**, navigate a fundamental trade-off. It is theoretically impossible to maintain a fixed exchange rate, free capital movement, and independent monetary policy simultaneously.
    
    * **Growth vs. Stability:** Large external shocks often force a deviation from Taylor Rule prescriptions to manage capital flows.
    * **Currency Protection:** In volatile regimes, rates may be held higher than the domestic model suggests to prevent currency depreciation.
    """)

st.caption("Quantitative Policy Lab | Strategic Research Analytics")
