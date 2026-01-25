import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="🏛️")

# GLOBAL VISIBILITY CSS (Forces Light-Mode Readability)
st.markdown("""
    <style>
    /* Force Background and Text Contrast */
    .main { background-color: #FFFFFF !important; }
    
    /* Metrics: Label and Value Visibility */
    [data-testid="stMetricLabel"] { color: #5F6368 !important; font-size: 1rem !important; font-weight: 600 !important; }
    [data-testid="stMetricValue"] { color: #1A1C1E !important; font-weight: 800 !important; }
    
    /* Widget Labels (Sliders, Selectboxes, Radio) */
    .stWidgetLabel p, label {
        color: #1A1C1E !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] { background-color: #F8F9FA !important; border-right: 1px solid #E0E0E0; }
    
    /* Headers */
    h1, h2, h3, h4 { color: #1A237E !important; font-weight: 800 !important; }
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

# --- SIDEBAR: EDUCATIONAL CONTROLS ---
st.sidebar.title("👨‍🏫 Policy Simulator")
market = st.sidebar.selectbox("Select Economy", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("📅 Time Horizon")
horizon = st.sidebar.radio("Observation Window", ["Last 1 Year", "Last 5 Years", "Full History"], index=1)

st.sidebar.divider()
st.sidebar.subheader("🏗️ Model Calibration")
# Teaching Tool Feature: Philosophy Toggle
philosophy = st.sidebar.selectbox("Central Bank Philosophy", 
    ["Standard Taylor", "Inflation Hawk", "Dual Mandate (Growth Focus)", "Custom"],
    help="Hawks weigh inflation more. Dual Mandate balances growth/output gaps.")

if philosophy == "Inflation Hawk":
    inf_weight, y_weight, smoothing = 2.0, 0.2, 0.1
elif philosophy == "Dual Mandate (Growth Focus)":
    inf_weight, y_weight, smoothing = 1.0, 1.0, 0.4
else:
    inf_weight = st.sidebar.slider("Inflation Weight (λπ)", 0.5, 2.5, 1.5, help="Responsiveness to inflation deviations.")
    y_weight = st.sidebar.slider("Output Weight (λy)", 0.0, 1.5, 0.5, help="Responsiveness to GDP/Output Gap.")
    smoothing = st.sidebar.slider("Interest Rate Smoothing", 0.0, 1.0, 0.2, help="How slowly the bank moves rates.")

st.sidebar.divider()
st.sidebar.subheader("⚡ Shock Simulations")
oil_shock = st.sidebar.slider("Energy/Supply Shock (%)", -50, 100, 0, help="Simulates cost-push inflation from energy prices.")
r_star = st.sidebar.slider("Natural Real Rate (r*)", 0.0, 5.0, 1.5, help="The theoretical rate that neither stimulates nor contracts the economy.")

# --- ANALYTICS ENGINE ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "beta": 0.12, "target": 4.0},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "beta": 0.07, "target": 2.0},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "beta": 0.10, "target": 2.0}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])

# Timeline Filtering
latest_date = valid_df['Date'].max()
if horizon == "Last 1 Year": start_point = latest_date - timedelta(days=365)
elif horizon == "Last 5 Years": start_point = latest_date - timedelta(days=5*365)
else: start_point = valid_df['Date'].min()

filtered_df = valid_df[valid_df['Date'] >= start_point]
latest = valid_df.iloc[-1]

# Calculations
base_inf = latest[m['cpi']]
shock_impact = (oil_shock * m['beta'])
adj_inf = base_inf + shock_impact
curr_rate = latest[m['rate']]
target_inf = m['target']

# Formula: i = r* + pi + λπ(pi - target) + λy(output_gap)
# Assume neutral output gap (0) unless we add a slider
raw_fv = r_star + adj_inf + inf_weight * (adj_inf - target_inf)

# Apply Smoothing
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"🏛️ {market}: Policy Lab & Terminal")
st.markdown(f"**Current Regime:** `{philosophy}` | **Last Data Print:** {latest['Date'].strftime('%B %Y')}")

# Metrics Section (Forced visibility)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Shock-Adj. CPI", f"{adj_inf:.2f}%", f"{shock_impact:+.2f}%" if oil_shock != 0 else None, delta_color="inverse")
c3.metric("Current Policy Rate", f"{curr_rate:.2f}%")
c4.metric("Model Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#0052cc", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="Headline CPI", line=dict(color="#ff4b4b", width=1.5, dash='dot')))
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=18, color='#ffc107', symbol='star', line=dict(width=1, color='black')),
                         name="Terminal Rate Suggestion"))

fig.update_layout(
    height=400, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", y=1.1, x=0),
    xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0", title="Percent (%)")
)
st.plotly_chart(fig, use_container_width=True)

# --- TEACHING / INSIGHTS SECTION ---
st.divider()
left, right = st.columns([2, 1])

with left:
    # Assessment Box
    status = "HAWKISH" if gap_bps > 50 else "DOVISH" if gap_bps < -50 else "NEUTRAL"
    color = "#D32F2F" if status == "HAWKISH" else "#2E7D32" if status == "DOVISH" else "#455A64"
    bg = "#FFF5F5" if status == "HAWKISH" else "#F5FFF5" if status == "DOVISH" else "#F8F9FA"

    st.markdown(f"""
    <div style="background-color: {bg}; border: 2px solid {color}; border-left: 10px solid {color}; padding: 25px; border-radius: 10px; color: #1A1C1E;">
        <h3 style="color: {color}; margin-top: 0;">Market Stance: {status}</h3>
        <p style="font-size: 1.1rem; line-height: 1.6;">
            The model indicates a <b>{gap_bps:+.0f} basis point</b> deviation from the calculated fair value. 
            Under the <b>{philosophy}</b> framework, the central bank should ideally target a terminal rate of <b>{fair_value:.2f}%</b>.
        </p>
        <p style="font-size: 0.95rem; background: #ffffff; padding: 10px; border-radius: 5px; border: 1px solid #ddd;">
            <b>Teaching Note:</b> Notice how increasing the 'Smoothing Factor' in the sidebar keeps the suggested rate closer to the 
            actual current rate. This simulates a central bank that prefers gradual adjustments to avoid market volatility.
        </p>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("🏛️ Institutional Research")
    st.markdown(f"""
    **The Policy Trilemma**
    
    Central banks in economies like **{market}** navigate the 'Impossible Trinity.' They must balance:
    1. **Exchange Rate Stability**
    2. **Free Capital Flow**
    3. **Independent Monetary Policy**
    
    **Simulation Insight:** If you simulate a large **Supply Shock**, you will see the Fair Value rise. In reality, a bank might ignore this shock if growth is weak, highlighting the trade-off between fighting inflation and supporting the economy.
    """)

st.caption("Quantitative Policy Lab | Designed for Academic & Institutional Research")
