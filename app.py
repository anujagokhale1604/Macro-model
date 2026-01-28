import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="📜")

# --- RESILIENT CSS (Works in Light & Dark Mode) ---
st.markdown("""
    <style>
    /* 1. Define a Mid-Tone color for visibility in both modes */
    :root {
        --resilient-teal: #2E5077;
    }

    /* 2. Force the App Background for a consistent "Paper" feel */
    .stApp {
        background-color: #F2EBE3 !important;
    }

    /* 3. The Multi-Mode Label Fix */
    /* Using a specific hex code that is visible on both dark and light surfaces */
    [data-testid="stWidgetLabel"] p, 
    .stSelectbox label p, 
    .stSlider label p, 
    .stRadio label p,
    label p {
        color: #2E5077 !important; 
        font-weight: 800 !important;
        font-size: 1.1rem !important;
        forced-color-adjust: none !important;
    }

    /* 4. Global Text - Deep Slate (Readable everywhere) */
    html, body, .stMarkdown, p, li, span {
        color: #1A1C1E !important;
        font-family: 'Georgia', serif !important;
    }

    /* 5. Sidebar separation */
    [data-testid="stSidebar"] {
        background-color: #E8E0D5 !important;
        border-right: 2px solid #D1C7B7 !important;
    }

    /* 6. Metrics */
    [data-testid="stMetricValue"] {
        color: #2E5077 !important;
        font-weight: 800 !important;
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

# --- SIDEBAR: CONTROLS ---
st.sidebar.title("📜 Policy Lab")

if st.sidebar.button("🔄 Reset to Baseline"):
    st.rerun()

market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("⚡ Macro Scenarios")
scenario = st.sidebar.selectbox("Choose a Scenario", 
    ["Current Baseline", "Soft Landing", "Stagflation Shock", "Global Recession"])

# Scenario Presets
if scenario == "Soft Landing":
    r_star_init, target_inf_init, gap_init, phil_idx = 1.5, 2.0, 0.5, 0
elif scenario == "Stagflation Shock":
    r_star_init, target_inf_init, gap_init, phil_idx = 2.5, 2.0, -2.5, 1
elif scenario == "Global Recession":
    r_star_init, target_inf_init, gap_init, phil_idx = 0.5, 2.0, -4.0, 2
else: 
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

# --- ANALYTICS ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])
latest_date = valid_df['Date'].max()
filtered_df = valid_df[valid_df['Date'] >= (latest_date - timedelta(days=5*365))]
latest = valid_df.iloc[-1]

base_inf = latest[m['cpi']]
curr_rate = latest[m['rate']]
raw_fv = r_star + base_inf + inf_weight * (base_inf - target_inf) + 0.5 * output_gap
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Intelligence")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Target Level", f"{target_inf:.1f}%")
c3.metric("Current Rate", f"{curr_rate:.2f}%")
c4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="Inflation (YoY)", line=dict(color="#A68A64", width=2, dash='dot')))
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=14, color='#BC6C25', symbol='diamond', line=dict(width=2, color='#1A1C1E')),
                         name="Model Fair Value"))

fig.update_layout(
    height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(t=30, b=100),
    legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center", font=dict(size=14, color="#1A1C1E")),
    xaxis=dict(showgrid=True, gridcolor="#D1C7B7", tickfont=dict(color='#1A1C1E')), 
    yaxis=dict(showgrid=True, gridcolor="#D1C7B7", title="Rate (%)", tickfont=dict(color='#1A1C1E'))
)
st.plotly_chart(fig, use_container_width=True)

# --- INSIGHTS ---
st.divider()
st.markdown(f"""
    <div style="background-color: #E8E0D5; border-left: 10px solid #2E5077; padding: 25px; border-radius: 4px;">
        <h3 style="color: #2E5077; margin-top: 0;">Analysis: {gap_bps:+.0f} bps Deviation</h3>
        <p style="font-size: 1.15rem; color: #1A1C1E;">
            Under the current <b>{philosophy}</b> mandate, the model suggests an interest rate anchor of <b>{fair_value:.2f}%</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)
