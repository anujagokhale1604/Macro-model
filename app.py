import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="📜")

# --- ABSOLUTE CONTRAST OVERRIDE ---
st.markdown("""
    <style>
    /* 1. Universal Background */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F2EBE3 !important;
    }
    
    /* 2. Sidebar Background & Border */
    [data-testid="stSidebar"] {
        background-color: #E8E0D5 !important;
        border-right: 3px solid #D1C7B7 !important;
    }

    /* 3. FORCING ALL LABELS TO BLACK - Nuclear Option */
    /* This targets the actual label containers for Sliders, Selectboxes, and Radios */
    .stWidgetLabel p, 
    label, 
    div[data-testid="stWidgetLabel"] p,
    .stSelectbox label p,
    .stSlider label p,
    .stRadio label p {
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 1.1rem !important;
        opacity: 1 !important;
    }

    /* 4. Global Text Styling */
    html, body, .stMarkdown, p, li, span {
        color: #1A1C1E !important; 
        font-family: 'Georgia', serif !important;
    }

    /* 5. Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #FAF9F6;
        border: 2px solid #D1C7B7;
        padding: 1.5rem;
        border-radius: 4px;
    }
    [data-testid="stMetricLabel"] { 
        color: #493D31 !important; 
        font-weight: 700 !important; 
    }
    [data-testid="stMetricValue"] { 
        color: #000000 !important; 
        font-weight: 800 !important;
    }

    /* 6. Headers */
    h1, h2, h3 { 
        color: #000000 !important; 
        font-weight: 900 !important;
        border-bottom: 2px solid #D1C7B7;
    }
    
    /* 7. Radio Button Options Text */
    div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    # Use the filename you provided
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
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "beta": 0.12},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "beta": 0.07},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "beta": 0.10}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])

latest_date = valid_df['Date'].max()
filtered_df = valid_df[valid_df['Date'] >= (latest_date - timedelta(days=5*365))]
latest = valid_df.iloc[-1]

# Math
base_inf = latest[m['cpi']]
curr_rate = latest[m['rate']]
raw_fv = r_star + base_inf + inf_weight * (base_inf - target_inf) + 0.5 * output_gap
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Intelligence")
st.markdown(f"**Mode:** `{scenario}` | **Targeting:** `{philosophy}`")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Target Level", f"{target_inf:.1f}%")
c3.metric("Current Rate", f"{curr_rate:.2f}%")
c4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#000000", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="Inflation (YoY)", line=dict(color="#A68A64", width=2, dash='dot')))
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=14, color='#BC6C25', symbol='diamond', line=dict(width=2, color='#000000')),
                         name="Model Fair Value"))

fig.update_layout(
    title=dict(text="Historical Trend vs. Model Projection", font=dict(size=22, color='#000000')),
    height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(t=80, b=100),
    legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center", font=dict(size=14, color="#000000")),
    xaxis=dict(showgrid=True, gridcolor="#D1C7B7", tickfont=dict(color='#000000')), 
    yaxis=dict(showgrid=True, gridcolor="#D1C7B7", title="Rate (%)", tickfont=dict(color='#000000'))
)
st.plotly_chart(fig, use_container_width=True)

# --- INSIGHTS ---
st.divider()
st.markdown(f"""
    <div style="background-color: #E8E0D5; border-left: 10px solid #BC6C25; padding: 25px; border-radius: 4px;">
        <h3 style="color: #000000; margin-top: 0;">Analysis: {gap_bps:+.0f} bps Deviation</h3>
        <p style="font-size: 1.15rem; color: #000000;">
            The simulation indicates that under the <b>{philosophy}</b> mandate, the interest rate should gravitate 
            toward <b>{fair_value:.2f}%</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)
