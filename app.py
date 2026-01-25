import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="📜")

# --- GENTLE RESEARCH THEME CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stAppViewContainer"] { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; border-right: 1px solid #D1C7B7; }

    /* Global Text Visibility */
    html, body, [class*="css"], .stMarkdown, p, label, li, span {
        color: #2C333F !important; 
        font-family: 'Georgia', serif !important;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #F9F7F2;
        border: 1px solid #D1C7B7;
        padding: 1.5rem;
        border-radius: 4px;
    }
    [data-testid="stMetricLabel"] { color: #6B5E53 !important; font-weight: 600 !important; font-size: 0.85rem !important; }
    [data-testid="stMetricValue"] { color: #3E362E !important; font-family: serif !important; font-weight: 700 !important; }

    /* Sidebar Labels */
    .stWidgetLabel p, label { color: #3E362E !important; font-weight: 600 !important; font-size: 0.95rem !important; }
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

# --- SIDEBAR: CONTROLS ---
st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("⚡ Macro Scenarios")
scenario = st.sidebar.selectbox("Choose a Scenario", 
    ["Current Baseline", "Soft Landing", "Stagflation Shock", "Global Recession"])

# Logic for Scenario Presets
if scenario == "Soft Landing":
    r_star_init, target_inf_init, gap_init, phil_idx = 1.5, 2.0, 0.5, 0
elif scenario == "Stagflation Shock":
    r_star_init, target_inf_init, gap_init, phil_idx = 2.5, 2.0, -2.5, 1
elif scenario == "Global Recession":
    r_star_init, target_inf_init, gap_init, phil_idx = 0.5, 2.0, -4.0, 2
else: # Baseline
    r_star_init, target_inf_init, gap_init, phil_idx = 1.5, 4.0 if market == "India" else 2.0, 0.0, 0

st.sidebar.divider()
st.sidebar.subheader("🏗️ Model Calibration")
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, r_star_init)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, target_inf_init)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, gap_init)

st.sidebar.divider()
st.sidebar.subheader("🧠 Banking Stance")
philosophy = st.sidebar.selectbox("Framework", ["Standard", "Hawk", "Dovish", "Custom"], index=phil_idx)

if philosophy == "Hawk":
    inf_weight, smoothing = 2.2, 0.1
elif philosophy == "Dovish":
    inf_weight, smoothing = 1.0, 0.5
elif philosophy == "Standard":
    inf_weight, smoothing = 1.5, 0.2
else:
    inf_weight = st.sidebar.slider("Inflation Response", 0.5, 3.0, 1.5)
    smoothing = st.sidebar.slider("Policy Inertia (Smoothing)", 0.0, 1.0, 0.2)

st.sidebar.divider()
horizon = st.sidebar.radio("Time Horizon", ["1 Year", "5 Years", "History"], index=1, horizontal=True)

# --- ANALYTICS ENGINE ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "beta": 0.12},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "beta": 0.07},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "beta": 0.10}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])

latest_date = valid_df['Date'].max()
if horizon == "1 Year": start_point = latest_date - timedelta(days=365)
elif horizon == "5 Years": start_point = latest_date - timedelta(days=5*365)
else: start_point = valid_df['Date'].min()

filtered_df = valid_df[valid_df['Date'] >= start_point]
latest = valid_df.iloc[-1]

# Math
base_inf = latest[m['cpi']]
curr_rate = latest[m['rate']]
raw_fv = r_star + base_inf + inf_weight * (base_inf - target_inf) + 0.5 * output_gap
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Intelligence")
st.markdown(f"**Scenario Mode:** `{scenario}`")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Target Level", f"{target_inf:.1f}%")
c3.metric("Current Rate", f"{curr_rate:.2f}%")
c4.metric("Model Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART (Overlap Fixed) ---
fig = go.Figure()

fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], 
                         name="Policy Rate", line=dict(color="#4F5D75", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], 
                         name="Inflation (YoY)", line=dict(color="#A68A64", width=2, dash='dot')))
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=14, color='#BC6C25', symbol='diamond', line=dict(width=1.5, color='#1A1C1E')),
                         name="Fair Value Projection"))

fig.update_layout(
    title=dict(
        text=f"Historical Framework vs. Model Projection",
        font=dict(size=20, color='#1A1C1E', family="Georgia"),
        y=0.95 # Move title higher
    ),
    height=500,
    template="simple_white",
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=80, b=80), # Increased top and bottom margins
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.25, # Move legend below the x-axis
        xanchor="center",
        x=0.5,
        font=dict(size=13, color='#1A1C1E', family="Georgia")
    ),
    xaxis=dict(showgrid=True, gridcolor="#D1C7B7", tickfont=dict(color='#3E362E')), 
    yaxis=dict(showgrid=True, gridcolor="#D1C7B7", title="Rate (%)", tickfont=dict(color='#3E362E'))
)
st.plotly_chart(fig, use_container_width=True)

# --- INSIGHTS ---
st.divider()
left, right = st.columns([2, 1])

with left:
    if gap_bps > 50:
        sig, col, bg = "RESTRICTIVE LEAN", "#7B3F00", "#EBDCCB"
    elif gap_bps < -50:
        sig, col, bg = "ACCOMMODATIVE LEAN", "#3A5A40", "#DAE1D7"
    else:
        sig, col, bg = "STABLE / ALIGNED", "#493D31", "#E8E0D5"

    st.markdown(f"""
    <div style="background-color: {bg}; border-left: 10px solid {col}; padding: 25px; border-radius: 4px; color: #3E362E;">
        <h3 style="color: {col}; margin-top: 0;">Result: {sig}</h3>
        <p style="font-size: 1.1rem; line-height: 1.7;">
            The simulation reveals a <b>{gap_bps:+.0f} basis point</b> policy gap. 
            Under a <i>{philosophy}</i> mandate, the target rate is <b>{fair_value:.2f}%</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("Teaching Moment")
    st.markdown("""
    **The Taylor Rule** is a key teaching tool for understanding how central banks respond to inflation and growth. 
    
    * **Inflation Gap:** (Actual Inflation - Target)
    * **Output Gap:** (Actual GDP - Potential GDP)
    
    When inflation is high, the rule dictates raising rates to cool the economy.
    """)
    

st.caption("Quantitative Policy Lab | Graduate Portfolio")
