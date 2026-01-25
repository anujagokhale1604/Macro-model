import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="🕊️")

# --- GENTLE RESEARCH CSS (Linen & Slate) ---
st.markdown("""
    <style>
    /* Warm Paper Background */
    .main { background-color: #FAF9F6 !important; }
    
    /* Global Text: Soft Slate (No pure black) */
    html, body, [class*="css"], .stMarkdown, p, label {
        color: #475569 !important; 
        font-family: 'Georgia', serif !important;
    }

    /* Soft Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #F1F5F9;
        padding: 1.5rem;
        border-radius: 4px; /* Slightly sharper for a 'printed' look */
        box-shadow: 0 2px 4px rgba(0,0,0,0.01);
    }
    [data-testid="stMetricLabel"] { 
        color: #94A3B8 !important; 
        font-weight: 400 !important; 
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    [data-testid="stMetricValue"] { 
        color: #334155 !important; 
        font-weight: 500 !important; 
        font-family: sans-serif !important;
    }

    /* Sidebar - Muted Slate */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0;
    }
    
    /* Headers - Elegant & Deep */
    h1, h2, h3 { 
        color: #1E293B !important; 
        font-weight: 600 !important;
        font-family: 'Georgia', serif !important;
    }

    /* Labels - High Contrast but Muted */
    .stWidgetLabel p, label {
        color: #475569 !important;
        font-weight: 500 !important;
        font-family: sans-serif !important;
    }
    
    /* Custom divider color */
    hr { border-top: 1px solid #E2E8F0 !important; }
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

# --- SIDEBAR: GENTLE CONTROLS ---
st.sidebar.title("🕊️ Policy Simulation")
market = st.sidebar.selectbox("Market Select", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("Timeframe")
horizon = st.sidebar.radio("", ["1 Year", "5 Years", "History"], index=1, horizontal=True)

st.sidebar.divider()
st.sidebar.subheader("Model Variables")
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target", 1.0, 6.0, 4.0 if market == "India" else 2.0)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, 0.0)

st.sidebar.divider()
st.sidebar.subheader("Framework")
philosophy = st.sidebar.selectbox("Banking Stance", ["Standard Taylor", "Inflation Hawk", "Dual Mandate", "Custom"])

if philosophy == "Inflation Hawk":
    inf_weight, smoothing = 2.2, 0.1
elif philosophy == "Dual Mandate":
    inf_weight, smoothing = 1.2, 0.4
else:
    inf_weight = st.sidebar.slider("Inflation Sensitivity", 0.5, 3.0, 1.5)
    smoothing = st.sidebar.slider("Gradualism (Smoothing)", 0.0, 1.0, 0.2)

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
st.title(f"{market} Policy Insight")
st.markdown(f"**Scenario:** {philosophy} framework with {r_star}% neutral rate expectation.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Target Level", f"{target_inf:.1f}%")
c3.metric("Current Rate", f"{curr_rate:.2f}%")
c4.metric("Model Estimate", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART (Muted Mosaics) ---
fig = go.Figure()

# Gentle Muted Lines
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#64748B", width=2)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="Inflation", line=dict(color="#94A3B8", width=1.5, dash='dot')))

# Soft Projection Marker
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=12, color='#D97706', symbol='circle', line=dict(width=1, color='#FFF')),
                         name="Fair Value"))

fig.update_layout(
    height=400, template="simple_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=20, b=10),
    legend=dict(orientation="h", y=1.1, x=0),
    xaxis=dict(showgrid=True, gridcolor="#F1F5F9", tickfont=dict(color='#94A3B8')), 
    yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Rate (%)", tickfont=dict(color='#94A3B8'))
)
st.plotly_chart(fig, use_container_width=True)

# --- EDUCATIONAL INSIGHTS ---
st.divider()
left, right = st.columns([2, 1])

with left:
    if gap_bps > 50:
        sig, col, bg = "HAWKISH RE-RATING", "#991B1B", "#FEF2F2"
    elif gap_bps < -50:
        sig, col, bg = "DOVISH RE-RATING", "#166534", "#F0FDF4"
    else:
        sig, col, bg = "EQUILIBRIUM", "#475569", "#F8FAFC"

    st.markdown(f"""
    <div style="background-color: {bg}; border: 1px solid {col}22; padding: 30px; border-radius: 4px; color: #334155;">
        <h3 style="color: {col}; margin-top: 0; font-size: 1.1rem; letter-spacing: 0.05em;">OBSERVATION: {sig}</h3>
        <p style="font-size: 1.05rem; line-height: 1.7;">
            The simulation reveals a <b>{gap_bps:+.0f} basis point</b> deviation from the fair-value benchmark. 
            Within the <i>{philosophy}</i> model, the terminal rate should gravitate toward <b>{fair_value:.2f}%</b> 
            to balance the current macro profile.
        </p>
        <p style="font-size: 0.9rem; color: #64748B; border-top: 1px solid {col}22; padding-top: 15px; margin-top: 15px;">
            <b>Note on Gradualism:</b> The Smoothing Factor (currently {smoothing}) represents the policy lag typical in 
            institutional decision-making. High smoothing suggests a bank that values market stability over immediate target convergence.
        </p>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("The Policy Trilemma")
    st.markdown(f"""
    Central banks in open economies like **{market}** operate under the 'Impossible Trinity' constraint. 
    
    This lab assumes an **Independent Monetary Policy**. In practice, large currency fluctuations often force banks to deviate from these Taylor Rule projections to protect the exchange rate and capital accounts.
    """)

st.caption("Quantitative Policy Lab | Institutional Macro Portfolio")
