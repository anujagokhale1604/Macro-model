import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="🌿")

# --- EXPLICIT "GENTLE" COLOR PALETTE ---
# Background: #F8F9F3 (Creamy Sage)
# Text: #4A4E4D (Soft Charcoal)
# Sidebar: #F1F3EE (Light Moss)
# Accents: #A3B18A (Sage), #D4A373 (Dusty Gold)

st.markdown("""
    <style>
    /* Global Background - Creamy Sage */
    .main { background-color: #F8F9F3 !important; }
    
    /* Global Text - Soft Charcoal (No pure black/blue) */
    html, body, [class*="css"], .stMarkdown, p, label, li {
        color: #4A4E4D !important; 
        font-family: 'Georgia', serif !important;
    }

    /* Metric Cards - Clean White on Cream */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E2DB;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.02);
    }
    [data-testid="stMetricLabel"] { 
        color: #8B948E !important; 
        font-weight: 400 !important; 
        font-size: 0.8rem !important;
        letter-spacing: 0.15em;
    }
    [data-testid="stMetricValue"] { 
        color: #588157 !important; /* Sage Green Value */
        font-weight: 500 !important; 
        font-family: sans-serif !important;
    }

    /* Sidebar - Muted Green Tint */
    section[data-testid="stSidebar"] {
        background-color: #F1F3EE !important;
        border-right: 1px solid #E0E2DB;
    }
    
    /* Headers - Earthy Tone */
    h1, h2, h3 { 
        color: #3A5A40 !important; 
        font-weight: 600 !important;
    }

    /* Slider & Toggle Labels */
    .stWidgetLabel p, label {
        color: #5F6B61 !important;
        font-weight: 500 !important;
        font-family: sans-serif !important;
    }

    /* Custom Divider */
    hr { border-top: 1px solid #DAD7CD !important; }
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

# --- SIDEBAR ---
st.sidebar.title("🌿 Research Lab")
market = st.sidebar.selectbox("Market Select", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("Time Horizon")
horizon = st.sidebar.radio("", ["1 Year", "5 Years", "History"], index=1, horizontal=True)

st.sidebar.divider()
st.sidebar.subheader("Scenario Parameters")
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target", 1.0, 6.0, 4.0 if market == "India" else 2.0)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, 0.0)

st.sidebar.divider()
st.sidebar.subheader("Banking Stance")
philosophy = st.sidebar.selectbox("Framework", ["Balanced", "Inflation Hawk", "Dovish / Growth", "Custom"])

if philosophy == "Inflation Hawk":
    inf_weight, smoothing = 2.2, 0.1
elif philosophy == "Dovish / Growth":
    inf_weight, smoothing = 1.0, 0.5
else:
    inf_weight = st.sidebar.slider("Inflation Sensitivity", 0.5, 3.0, 1.5)
    smoothing = st.sidebar.slider("Smoothing (Inertia)", 0.0, 1.0, 0.2)

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

# Taylor Rule Math
base_inf = latest[m['cpi']]
curr_rate = latest[m['rate']]
raw_fv = r_star + base_inf + inf_weight * (base_inf - target_inf) + 0.5 * output_gap
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Insight")
st.markdown(f"A simulated analysis using the **{philosophy}** framework.")

# Metrics (Moss & Sage)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Target Inflation", f"{target_inf:.1f}%")
c3.metric("Policy Rate", f"{curr_rate:.2f}%")
c4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART (Muted Earth Tones) ---
fig = go.Figure()

# Moss Green for Policy Rate, Muted Gray for CPI
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#588157", width=2.5)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="Inflation", line=dict(color="#A3B18A", width=1.5, dash='dot')))

# Dusty Gold for Projection
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=12, color='#D4A373', symbol='circle', line=dict(width=1, color='#FFF')),
                         name="Fair Value Estimate"))

fig.update_layout(
    height=400, template="simple_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=20, b=10),
    legend=dict(orientation="h", y=1.1, x=0),
    xaxis=dict(showgrid=True, gridcolor="#E0E2DB", tickfont=dict(color='#8B948E')), 
    yaxis=dict(showgrid=True, gridcolor="#E0E2DB", title="Rate (%)", tickfont=dict(color='#8B948E'))
)
st.plotly_chart(fig, use_container_width=True)

# --- EDUCATIONAL INSIGHTS ---
st.divider()
left, right = st.columns([2, 1])

with left:
    # Gentle Conditional Coloring
    if gap_bps > 50:
        sig, col, bg = "Restrictive Bias", "#6B4D4D", "#F4EAEA" # Muted Rose
    elif gap_bps < -50:
        sig, col, bg = "Accommodative Bias", "#3A5A40", "#E9F5EB" # Muted Sage
    else:
        sig, col, bg = "Equilibrium Stance", "#4A4E4D", "#F1F3EE" # Muted Gray

    st.markdown(f"""
    <div style="background-color: {bg}; border: 1px solid {col}33; padding: 30px; border-radius: 8px; color: #4A4E4D;">
        <h3 style="color: {col}; margin-top: 0; font-size: 1.1rem; letter-spacing: 0.05em;">OBSERVATION: {sig}</h3>
        <p style="font-size: 1.05rem; line-height: 1.7;">
            The simulation reveals a <b>{gap_bps:+.0f} basis point</b> deviation from the model baseline. 
            Under the current calibration, the terminal rate should gravitate toward <b>{fair_value:.2f}%</b> 
            to balance the domestic price profile.
        </p>
        <div style="font-size: 0.9rem; color: #64748B; border-top: 1px solid {col}22; padding-top: 15px; margin-top: 15px;">
            <strong>Teaching Insight:</strong> Interest Rate Smoothing (currently {smoothing}) represents the 
            historical 'inertia' found in central bank decisions. This prevents abrupt market shocks but can 
            create a lag in reaching inflation targets.
        </div>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("The Policy Trilemma")
    st.markdown(f"""
    Central banks in open economies like **{market}** navigate the 'Impossible Trinity.' 
    
    This simulation assumes an independent monetary stance. In real-world application, external shocks or currency volatility may force policy deviations to protect capital flows, regardless of what the Taylor Rule suggests.
    """)

st.caption("Quantitative Policy Lab | Strategic Portfolio Analytics")
