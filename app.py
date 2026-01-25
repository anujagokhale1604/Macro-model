import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="🏦")

# --- SOFTER PROFESSIONAL CSS (Slate, Sage, and Off-White) ---
st.markdown("""
    <style>
    /* Global Background */
    .main { background-color: #fdfdfd !important; }
    
    /* Widget Labels & Text Visibility */
    .stWidgetLabel p, label, .stMarkdown p, .stCaption {
        color: #334155 !important; 
        font-weight: 600 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }

    /* Professional Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    [data-testid="stMetricLabel"] { 
        color: #64748b !important; 
        font-weight: 500 !important; 
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] { 
        color: #1e293b !important; 
        font-weight: 700 !important; 
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f1f5f9 !important;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Headers */
    h1, h2, h3 { 
        color: #0f172a !important; 
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }
    
    /* Slider & Radio Selection Highlighting */
    .stSlider > div > div > div > div { background-color: #64748b !important; }
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

# --- SIDEBAR: INTERACTIVE TEACHING LAB ---
st.sidebar.title("👨‍🏫 Policy Simulation Lab")

st.sidebar.subheader("📍 Target Economy")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"], label_visibility="collapsed")

st.sidebar.divider()
st.sidebar.subheader("📅 Observation Window")
horizon = st.sidebar.radio("Timeline View", ["1 Year", "5 Years", "Full History"], index=1, horizontal=True)

st.sidebar.divider()
st.sidebar.subheader("🏗️ Structural Parameters")
# Re-adding the key toggles for interactivity
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, 1.5, help="The real interest rate that is neither expansionary nor contractionary.")
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 4.0 if market == "India" else 2.0)
output_gap = st.sidebar.slider("Simulated Output Gap (%)", -5.0, 5.0, 0.0, help="Positive = Overheating; Negative = Recessionary Gap.")

st.sidebar.divider()
st.sidebar.subheader("🧠 Behavioral Calibration")
philosophy = st.sidebar.selectbox("Central Bank Philosophy", ["Standard Taylor", "Inflation Hawk", "Dual Mandate", "Custom"])

if philosophy == "Inflation Hawk":
    inf_weight, y_weight, smoothing = 2.2, 0.1, 0.1
elif philosophy == "Dual Mandate":
    inf_weight, y_weight, smoothing = 1.2, 1.2, 0.4
elif philosophy == "Neutral / Standard":
    inf_weight, y_weight, smoothing = 1.5, 0.5, 0.2
else:
    inf_weight = st.sidebar.slider("Inflation Sensitivity (λπ)", 0.5, 3.0, 1.5)
    y_weight = st.sidebar.slider("Growth Sensitivity (λy)", 0.0, 2.0, 0.5)
    smoothing = st.sidebar.slider("Policy Inertia (Smoothing)", 0.0, 1.0, 0.2)

st.sidebar.divider()
st.sidebar.subheader("⚡ Shock Testing")
oil_shock = st.sidebar.slider("Supply-Side Shock (%)", -50, 100, 0, help="Simulates an energy price spike impacting headline inflation.")

# --- ANALYTICS ENGINE ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "beta": 0.12},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "beta": 0.07},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "beta": 0.10}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])

# Filtering
latest_date = valid_df['Date'].max()
if horizon == "1 Year": start_point = latest_date - timedelta(days=365)
elif horizon == "5 Years": start_point = latest_date - timedelta(days=5*365)
else: start_point = valid_df['Date'].min()

filtered_df = valid_df[valid_df['Date'] >= start_point]
latest = valid_df.iloc[-1]

# Calculations
base_inf = latest[m['cpi']]
shock_impact = (oil_shock * m['beta'])
adj_inf = base_inf + shock_impact
curr_rate = latest[m['rate']]

# Advanced Taylor Formula: i = r* + pi + λπ(pi - target) + λy(output_gap)
raw_fv = r_star + adj_inf + inf_weight * (adj_inf - target_inf) + y_weight * output_gap
# Smoothing: (1-ρ)*FV + ρ*Current
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"🏛️ {market} Policy Terminal")
st.caption(f"Framework: {philosophy} Model | Analysis Period: {latest['Date'].strftime('%B %Y')}")

# Metrics Layout
c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Adj. Inflation", f"{adj_inf:.2f}%", f"{shock_impact:+.2f}%" if oil_shock != 0 else None, delta_color="inverse")
c3.metric("Current Rate", f"{curr_rate:.2f}%")
c4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART (Soft Slate & Muted Colors) ---
fig = go.Figure()

# Background area for context
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#475569", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="Inflation Trend", line=dict(color="#94a3b8", width=1.5, dash='dot')))

# Highlight Model Suggestion
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=15, color='#d97706', symbol='diamond', line=dict(width=1, color='#000')),
                         name="Fair Value Estimate"))

fig.update_layout(
    height=450, template="simple_white", margin=dict(l=10, r=10, t=20, b=10),
    legend=dict(orientation="h", y=1.1, x=0),
    xaxis=dict(showgrid=True, gridcolor="#f1f5f9"), 
    yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Interest Rate (%)")
)
st.plotly_chart(fig, use_container_width=True)

# --- EDUCATIONAL INSIGHTS ---
st.divider()
left, right = st.columns([2, 1])

with left:
    # Color logic for assessment
    if gap_bps > 50:
        sig, col, bg = "RESTRICTIVE BIAS", "#991b1b", "#fef2f2"
    elif gap_bps < -50:
        sig, col, bg = "ACCOMMODATIVE BIAS", "#166534", "#f0fdf4"
    else:
        sig, col, bg = "NEUTRAL / ALIGNED", "#334155", "#f8f9fa"

    st.markdown(f"""
    <div style="background-color: {bg}; border: 1px solid {col}44; border-left: 10px solid {col}; padding: 25px; border-radius: 8px;">
        <h3 style="color: {col}; margin-top: 0; font-size: 1.2rem;">Simulation Result: {sig}</h3>
        <p style="font-size: 1.05rem; line-height: 1.6; color: #334155;">
            The model identifies a <b>{gap_bps:+.0f} basis point</b> deviation from the fair-value benchmark. 
            Under the <i>{philosophy}</i> framework, a terminal rate of <b>{fair_value:.2f}%</b> is suggested to stabilize price levels.
        </p>
        <div style="background: #ffffff; padding: 12px; border-radius: 6px; font-size: 0.9rem; border: 1px dashed #cbd5e1; margin-top: 15px;">
            <strong>Lab Note:</strong> Interest Rate Smoothing (currently set to {smoothing}) represents the central bank's preference 
            for gradualism. High inertia prevents market shocks but can lead to the bank being 'behind the curve' during rapid inflation spikes.
        </div>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("📚 Policy Context")
    st.markdown(f"""
    **The Impossible Trinity**
    
    Economies like **{market}** must balance the trade-offs of the 'Policy Trilemma.' In this lab, we focus on **Monetary Independence**.
    
    * **Simulated Shocks:** Adjusting the 'Supply Shock' slider demonstrates how cost-push inflation forces a central bank to raise rates even if growth is stagnant.
    * **The Mandate:** Inflation Hawks prioritize the {target_inf}% target above all else, while a 'Dual Mandate' approach would tolerate higher inflation to close a negative Output Gap.
    """)

st.caption("Advanced Policy Simulation Lab | Institutional Portfolio Framework")
