import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="📜")

# --- REFINED GENTLE AESTHETIC CSS ---
st.markdown("""
    <style>
    /* 1. Explicitly Force Background to a Warm Parchment Color */
    .stApp {
        background-color: #F2EBE3 !important;
    }
    
    /* 2. Target the main content area specifically */
    [data-testid="stAppViewContainer"] {
        background-color: #F2EBE3 !important;
    }

    /* 3. Style the Sidebar with a slightly deeper 'Paper' tone */
    [data-testid="stSidebar"] {
        background-color: #E8E0D5 !important;
        border-right: 1px solid #D1C7B7;
    }

    /* 4. Text & Font: Deep Slate-Grey for high readability without being 'stark' */
    html, body, [class*="css"], .stMarkdown, p, label, li, span {
        color: #2C333F !important; 
        font-family: 'Georgia', serif !important;
    }

    /* 5. Metric Cards: Muted Cream */
    div[data-testid="stMetric"] {
        background-color: #F9F7F2;
        border: 1px solid #D1C7B7;
        padding: 1.5rem;
        border-radius: 4px;
    }
    [data-testid="stMetricLabel"] { 
        color: #6B5E53 !important; 
        font-weight: 600 !important; 
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] { 
        color: #3E362E !important; 
        font-family: serif !important;
        font-weight: 700 !important;
    }

    /* 6. Headers: Rich Earthy Brown */
    h1, h2, h3 { 
        color: #493D31 !important; 
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
    }

    /* 7. Ensure Sidebar Labels are Crisp */
    .stWidgetLabel p, label {
        color: #3E362E !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
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

# --- SIDEBAR: INTERACTIVE TEACHING LAB ---
st.sidebar.title("📜 Policy Lab")
market = st.sidebar.selectbox("Market Selection", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("📅 Time Horizon")
horizon = st.sidebar.radio("", ["1 Year", "5 Years", "History"], index=1, horizontal=True)

st.sidebar.divider()
st.sidebar.subheader("⚡ Macro Scenarios")
scenario = st.sidebar.selectbox("Choose a Scenario", 
    ["Current Baseline", "Soft Landing", "Stagflation Shock", "Global Recession"])

# Logic for Scenario Presets
if scenario == "Soft Landing":
    r_star_init, target_inf_init, output_gap_init, phil_init = 1.5, 2.0, 0.5, "Standard"
elif scenario == "Stagflation Shock":
    r_star_init, target_inf_init, output_gap_init, phil_init = 2.5, 2.0, -2.5, "Hawk"
elif scenario == "Global Recession":
    r_star_init, target_inf_init, output_gap_init, phil_init = 0.5, 2.0, -4.0, "Dovish"
else:
    r_star_init, target_inf_init, output_gap_init, phil_init = 1.5, 4.0 if market == "India" else 2.0, 0.0, "Standard"

st.sidebar.divider()
st.sidebar.subheader("🏗️ Model Calibration")
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, r_star_init)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, target_inf_init)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, output_gap_init)

st.sidebar.divider()
st.sidebar.subheader("🧠 Banking Stance")
philosophy = st.sidebar.selectbox("Framework", ["Standard", "Hawk", "Dovish", "Custom"], index=["Standard", "Hawk", "Dovish", "Custom"].index(phil_init) if phil_init in ["Standard", "Hawk", "Dovish"] else 0)

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
oil_shock = st.sidebar.slider("Supply-Side Shock (%)", -50, 100, 0)

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

# Calculations
base_inf = latest[m['cpi']]
shock_impact = (oil_shock * m['beta'])
adj_inf = base_inf + shock_impact
curr_rate = latest[m['rate']]

raw_fv = r_star + adj_inf + inf_weight * (adj_inf - target_inf) + 0.5 * output_gap
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Intelligence")
st.markdown(f"**Scenario:** `{scenario}` | **Stance:** `{philosophy}` | **Observation:** {latest['Date'].strftime('%B %Y')}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Adj. Inflation", f"{adj_inf:.2f}%", f"{shock_impact:+.2f}%" if oil_shock != 0 else None, delta_color="inverse")
c3.metric("Current Rate", f"{curr_rate:.2f}%")
c4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART (High Visibility Legend & Titles) ---
fig = go.Figure()

fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], 
                         name="Historical Policy Rate", 
                         line=dict(color="#4F5D75", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], 
                         name="Headline CPI Trend", 
                         line=dict(color="#A68A64", width=2, dash='dot')))
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=14, color='#BC6C25', symbol='diamond', line=dict(width=1.5, color='#1A1C1E')),
                         name="Model Fair Value Projection"))

fig.update_layout(
    title=dict(text=f"Monetary Policy vs. Inflation Over Time", font=dict(size=18, color='#1A1C1E', family="Georgia")),
    height=450, template="simple_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(l=10, r=10, t=50, b=10),
    legend=dict(
        orientation="h", y=1.1, x=0, 
        font=dict(size=12, color='#1A1C1E', family="Georgia"),
        bgcolor="rgba(255,255,255,0.5)"
    ),
    xaxis=dict(showgrid=True, gridcolor="#D1C7B7", tickfont=dict(color='#3E362E', size=11), title="Date"), 
    yaxis=dict(showgrid=True, gridcolor="#D1C7B7", title="Interest Rate (%)", tickfont=dict(color='#3E362E', size=11))
)
st.plotly_chart(fig, use_container_width=True)

# --- TEACHING INSIGHTS ---
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
    <div style="background-color: {bg}; border: 1px solid {col}44; border-left: 10px solid {col}; padding: 25px; border-radius: 4px; color: #3E362E;">
        <h3 style="color: {col}; margin-top: 0; font-size: 1.2rem; letter-spacing: 0.05em;">OBSERVATION: {sig}</h3>
        <p style="font-size: 1.08rem; line-height: 1.7;">
            The model suggests a <b>{gap_bps:+.0f} basis point</b> deviation from the calculated fair-value benchmark. 
            Under the current <i>{philosophy}</i> framework, the policy rate should ideally converge toward <b>{fair_value:.2f}%</b>.
        </p>
        <div style="background: #ffffff; padding: 15px; border-radius: 4px; font-size: 0.95rem; border: 1px dashed #D1C7B7; margin-top: 15px;">
            <strong>Simulation Note:</strong> Policy Inertia (currently {smoothing}) reflects how central banks prefer gradual 
            shifts to avoid market panic. A high value means the bank will be slower to react to the 'Fair Value' star.
        </div>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("The Policy Trilemma")
    st.markdown(f"""
    Economies like **{market}** must navigate the 'Impossible Trinity'. In this simulation, we isolate **Monetary Independence**.
    
    * **Scenario Impact:** Selecting 'Stagflation' simulates high inflation with weak growth, forcing the model to recommend higher rates despite economic pain.
    * **r* (Neutral Rate):** This is the 'interest rate speed limit'—the point where the economy is neither overheating nor slowing down.
    """)

st.caption("Quantitative Policy Lab | Strategic Portfolio Research")
