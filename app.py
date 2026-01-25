import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="🏛️")

# --- REFINED PROFESSIONAL CSS (Soft & Crisp) ---
st.markdown("""
    <style>
    /* Soft Background */
    .main { background-color: #FDFDFD !important; }
    
    /* Global Text Visibility Fix */
    html, body, [class*="css"], .stMarkdown, p, label {
        color: #2C3E50 !important; 
        font-family: 'Inter', sans-serif !important;
    }

    /* Professional Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E9ECEF;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    [data-testid="stMetricLabel"] { font-size: 0.9rem !important; font-weight: 500 !important; color: #64748B !important; }
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: 700 !important; color: #1E293B !important; }

    /* Sidebar - Clean Slate */
    section[data-testid="stSidebar"] {
        background-color: #F1F5F9 !important;
        border-right: 1px solid #E2E8F0;
    }
    
    /* Heading Colors */
    h1, h2, h3 { color: #0F172A !important; letter-spacing: -0.02em; }

    /* Slider & Widget Label Specific Fix */
    .stWidgetLabel p, label {
        color: #334155 !important;
        font-weight: 600 !important;
        margin-bottom: 8px !important;
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

# --- SIDEBAR: INTERACTIVE TEACHING TOOLS ---
st.sidebar.title("👨‍🏫 Lab Controls")

st.sidebar.subheader("📍 Target Economy")
market = st.sidebar.selectbox("Select Country", ["India", "UK", "Singapore"], label_visibility="collapsed")

st.sidebar.divider()
st.sidebar.subheader("📅 Observation Window")
horizon = st.sidebar.radio("Timeline", ["1 Year", "5 Years", "Full History"], index=1, horizontal=True)

st.sidebar.divider()
st.sidebar.subheader("🏗️ Model Framework")
philosophy = st.sidebar.selectbox("Central Bank Stance", 
    ["Neutral / Standard", "Aggressive Hawk", "Growth Oriented (Dovish)", "Custom"])

if philosophy == "Aggressive Hawk":
    inf_weight, y_weight, smoothing = 2.0, 0.2, 0.1
elif philosophy == "Growth Oriented (Dovish)":
    inf_weight, y_weight, smoothing = 1.0, 1.2, 0.5
else:
    inf_weight = st.sidebar.slider("Inflation Response (λπ)", 0.5, 2.5, 1.5)
    y_weight = st.sidebar.slider("Output Gap Response (λy)", 0.0, 1.5, 0.5)
    smoothing = st.sidebar.slider("Policy Inertia (Smoothing)", 0.0, 1.0, 0.2)

st.sidebar.divider()
st.sidebar.subheader("⚡ External Variables")
oil_shock = st.sidebar.slider("Imported Energy Shock (%)", -50, 100, 0)
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, 1.5)

# --- ANALYTICS ENGINE ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "beta": 0.12, "target": 4.0},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "beta": 0.07, "target": 2.0},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "beta": 0.10, "target": 2.0}
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
shock_impact = (oil_shock * m['beta'])
adj_inf = base_inf + shock_impact
curr_rate = latest[m['rate']]
target_inf = m['target']

# Taylor Formula
raw_fv = r_star + adj_inf + inf_weight * (adj_inf - target_inf)
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"🏛️ {market} Policy Intelligence")
st.markdown(f"**Framework:** {philosophy} | **Data Current To:** {latest['Date'].strftime('%B %Y')}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Shock-Adj. CPI", f"{adj_inf:.2f}%", f"{shock_impact:+.2f}%" if oil_shock != 0 else None, delta_color="inverse")
c3.metric("Policy Rate", f"{curr_rate:.2f}%")
c4.metric("Model Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART (Soft Professional Palette) ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#475569", width=2.5)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="CPI (YoY)", line=dict(color="#94A3B8", width=1.5, dash='dot')))
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=14, color='#F59E0B', symbol='diamond', line=dict(width=1, color='black')),
                         name="Model Projection"))

fig.update_layout(
    height=450, template="simple_white", margin=dict(l=10, r=10, t=20, b=10),
    legend=dict(orientation="h", y=1.1, x=0),
    xaxis=dict(showgrid=True, gridcolor="#F1F5F9"), yaxis=dict(showgrid=True, gridcolor="#F1F5F9", title="Rate (%)")
)
st.plotly_chart(fig, use_container_width=True)

# --- TEACHING INSIGHTS ---
st.divider()
left, right = st.columns([2, 1])

with left:
    status = "RESTRICTIVE" if gap_bps > 50 else "ACCOMMODATIVE" if gap_bps < -50 else "ALIGNED"
    color = "#B91C1C" if status == "RESTRICTIVE" else "#15803D" if status == "ACCOMMODATIVE" else "#334155"
    bg = "#FEF2F2" if status == "RESTRICTIVE" else "#F0FDF4" if status == "ACCOMMODATIVE" else "#F8F9FA"

    st.markdown(f"""
    <div style="background-color: {bg}; border: 1px solid {color}33; border-left: 8px solid {color}; padding: 25px; border-radius: 8px;">
        <h3 style="color: {color}; margin-top: 0; font-size: 1.25rem;">Policy Stance: {status}</h3>
        <p style="font-size: 1.05rem; line-height: 1.6; color: #334155;">
            Our simulation estimates a <b>{gap_bps:+.0f} basis point</b> deviation from the fair-value baseline. 
            Under the current selection, the terminal rate is projected at <b>{fair_value:.2f}%</b>.
        </p>
        <div style="background: #ffffffaa; padding: 12px; border-radius: 6px; font-size: 0.9rem; border: 1px dashed #CBD5E1;">
            <strong>Teaching Insight:</strong> Observe the 'Policy Inertia' (Smoothing) slider. In real-world economics, 
            central banks rarely move rates to the full 'Fair Value' instantly. They move in increments (e.g., 25bps) 
            to ensure financial stability.
        </div>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("📚 The Policy Trilemma")
    st.markdown(f"""
    In open-market economies like **{market}**, policymakers face a trade-off. They can only choose two of the following:
    * **Fixed Exchange Rate**
    * **Free Capital Movement**
    * **Independent Monetary Policy**
    
    This simulation focuses on **Monetary Independence**. If you apply a large shock, you see how internal rates must react to protect the domestic economy, even if it risks currency volatility.
    """)

st.caption("Advanced Policy Research Lab | Institutional Analytics Portfolio")
