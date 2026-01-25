import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="📜")

# --- EXPLICIT BACKGROUND COLOR OVERRIDE ---
st.markdown("""
    <style>
    /* 1. Force the entire background to a warm, soft parchment/sand color */
    [data-testid="stAppViewContainer"], .main, .stApp {
        background-color: #F2EBE3 !important;
    }
    
    /* 2. Style the Sidebar with a slightly darker 'Paper' tone */
    [data-testid="stSidebar"] {
        background-color: #E8E0D5 !important;
        border-right: 1px solid #D1C7B7;
    }

    /* 3. Text & Font: Deep Slate-Grey (Gentle on eyes) */
    html, body, [class*="css"], .stMarkdown, p, label, li, span {
        color: #434C5E !important; 
        font-family: 'Georgia', serif !important;
    }

    /* 4. Metric Cards: Muted Cream to stand out slightly from the sand */
    div[data-testid="stMetric"] {
        background-color: #F9F7F2;
        border: 1px solid #D1C7B7;
        padding: 1.5rem;
        border-radius: 2px; /* Sharp edges for a traditional look */
    }
    [data-testid="stMetricLabel"] { 
        color: #8C7D70 !important; 
        font-weight: 400 !important; 
        font-size: 0.8rem !important;
        text-transform: uppercase;
    }
    [data-testid="stMetricValue"] { 
        color: #5E503F !important; 
        font-family: serif !important;
    }

    /* 5. Headers: Deep Earthy Brown */
    h1, h2, h3 { 
        color: #493D31 !important; 
        font-weight: 600 !important;
    }

    /* 6. Slider visibility */
    .stWidgetLabel p, label {
        color: #493D31 !important;
        font-weight: 500 !important;
    }
    
    hr { border-top: 1px solid #D1C7B7 !important; }
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
st.sidebar.title("📜 Policy Archive")
market = st.sidebar.selectbox("Market Focus", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("Timeframe")
horizon = st.sidebar.radio("", ["1 Year", "5 Years", "History"], index=1, horizontal=True)

st.sidebar.divider()
st.sidebar.subheader("Model Variables")
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target", 1.0, 6.0, 4.0 if market == "India" else 2.0)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, 0.0)

st.sidebar.divider()
st.sidebar.subheader("Stance")
philosophy = st.sidebar.selectbox("Framework", ["Standard", "Hawk", "Dovish", "Custom"])

if philosophy == "Hawk":
    inf_weight, smoothing = 2.2, 0.1
elif philosophy == "Dovish":
    inf_weight, smoothing = 1.0, 0.5
else:
    inf_weight = st.sidebar.slider("Inflation Response", 0.5, 3.0, 1.5)
    smoothing = st.sidebar.slider("Gradualism", 0.0, 1.0, 0.2)

# --- ANALYTICS ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "target": 4.0},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "target": 2.0},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "target": 2.0}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])

latest_date = valid_df['Date'].max()
if horizon == "1 Year": start_point = latest_date - timedelta(days=365)
elif horizon == "5 Years": start_point = latest_date - timedelta(days=5*365)
else: start_point = valid_df['Date'].min()

filtered_df = valid_df[valid_df['Date'] >= start_point]
latest = valid_df.iloc[-1]

# Calculations
base_inf = latest[m['cpi']]
curr_rate = latest[m['rate']]
raw_fv = r_star + base_inf + inf_weight * (base_inf - target_inf) + 0.5 * output_gap
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Insight")
st.markdown(f"Analysis of the **{philosophy}** framework within the current macroeconomic cycle.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Target Level", f"{target_inf:.1f}%")
c3.metric("Current Rate", f"{curr_rate:.2f}%")
c4.metric("Model Estimate", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART (Earthy, Muted Tones) ---
fig = go.Figure()

# Slate for Rate, Muted Clay for CPI
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#4F5D75", width=2)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="Inflation", line=dict(color="#A68A64", width=1.5, dash='dot')))

# Earthy Terracotta for Projection
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=12, color='#BC6C25', symbol='diamond', line=dict(width=1, color='#FFF')),
                         name="Fair Value Estimate"))

fig.update_layout(
    height=400, template="simple_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=20, b=10),
    legend=dict(orientation="h", y=1.1, x=0),
    xaxis=dict(showgrid=True, gridcolor="#D1C7B7", tickfont=dict(color='#8C7D70')), 
    yaxis=dict(showgrid=True, gridcolor="#D1C7B7", title="Rate (%)", tickfont=dict(color='#8C7D70'))
)
st.plotly_chart(fig, use_container_width=True)

# --- EDUCATIONAL INSIGHTS ---
st.divider()
left, right = st.columns([2, 1])

with left:
    if gap_bps > 50:
        sig, col, bg = "Restrictive Lean", "#7B3F00", "#EBDCCB"
    elif gap_bps < -50:
        sig, col, bg = "Accommodative Lean", "#3A5A40", "#DAE1D7"
    else:
        sig, col, bg = "Equilibrium", "#493D31", "#E8E0D5"

    st.markdown(f"""
    <div style="background-color: {bg}; border: 1px solid {col}44; padding: 25px; border-radius: 4px; color: #493D31;">
        <h3 style="color: {col}; margin-top: 0; font-size: 1.1rem;">Observation: {sig}</h3>
        <p style="font-size: 1.05rem; line-height: 1.7;">
            The simulation reveals a <b>{gap_bps:+.0f} basis point</b> deviation from the fair-value benchmark. 
            Within the <i>{philosophy}</i> framework, the terminal rate should gravitate toward <b>{fair_value:.2f}%</b>.
        </p>
        <p style="font-size: 0.9rem; color: #7B6D5E; border-top: 1px solid {col}22; padding-top: 15px; margin-top: 15px;">
            <b>Educational Note:</b> This model illustrates the "Taylor Rule." Notice how 
            the <i>Neutral Rate (r*)</i> acts as the anchor—if inflation and output are at target, 
            the policy rate should equal r* + inflation.
        </p>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("The Policy Trilemma")
    st.markdown(f"""
    Central banks in economies like **{market}** must navigate the 'Impossible Trinity'—the inability to simultaneously have a fixed exchange rate, free capital flow, and independent monetary policy.
    """)
    

st.caption("Quantitative Policy Lab | Graduate Portfolio Project")
