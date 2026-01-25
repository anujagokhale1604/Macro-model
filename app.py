import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide", page_icon="🏛️")

# Custom CSS for "Bright & Crisp" Professional Look
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    .stMetric { background-color: #ffffff; border: 1px solid #ececec; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }
    div[data-testid="stMetricValue"] { color: #1a237e; font-weight: 700; }
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
st.sidebar.title("🏛️ Policy Lab")
market = st.sidebar.selectbox("Market Focus", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("📅 Timeline Horizon")
horizon = st.sidebar.radio("View Period", ["Last 1 Year", "Last 5 Years", "Full History"], index=1)

st.sidebar.divider()
st.sidebar.subheader("🛠️ Model Adjustments")
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 5.0, 4.0 if market == "India" else 2.0)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, 0.0)

# --- DATA PROCESSING ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])

# Apply Timeline Filter
latest_date = valid_df['Date'].max()
if horizon == "Last 1 Year":
    start_date = latest_date - timedelta(days=365)
elif horizon == "Last 5 Years":
    start_date = latest_date - timedelta(days=5*365)
else:
    start_date = valid_df['Date'].min()

filtered_df = valid_df[valid_df['Date'] >= start_date]
latest = valid_df.iloc[-1]

# Calculations
inf = latest[m['cpi']]
curr_rate = latest[m['rate']]
fair_value = r_star + inf + 0.5*(inf - target_inf) + 0.5*(output_gap)

# --- DASHBOARD UI ---
st.title(f"🚀 {market} Macro-Policy Terminal")
st.markdown(f"**Research Status:** `Live Analysis` | **Last Update:** {latest['Date'].strftime('%d %B, %Y')}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Headline Inflation", f"{inf:.2f}%")
m2.metric("Target Inflation", f"{target_inf:.1f}%")
m3.metric("Effective Policy Rate", f"{curr_rate:.2f}%")
m4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{fair_value-curr_rate:+.2f}%", delta_color="inverse")

# --- CHART ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#007bff", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="CPI (YoY)", line=dict(color="#ff4b4b", width=1.5, dash='dot')))
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers+text', 
                         marker=dict(size=15, color='#f9a825', symbol='star', line=dict(width=2, color='black')),
                         text=["MODEL FV"], textposition="top center", name="Fair Value"))

fig.update_layout(
    height=450, template="plotly_white", margin=dict(l=0, r=0, t=20, b=0),
    legend=dict(orientation="h", y=1.1),
    xaxis=dict(gridcolor="#f0f0f0"), yaxis=dict(gridcolor="#f0f0f0")
)
st.plotly_chart(fig, use_container_width=True)

# --- PROFESSIONAL ASSESSMENT ---
st.divider()
gap = fair_value - curr_rate
if gap > 0.5:
    signal, signal_col, bg_col = "HAWKISH RE-RATING", "#dc3545", "#fff5f5"
    desc = "The policy rate is trailing fundamentals. Data suggests a tightening bias is required to anchor inflation expectations."
elif gap < -0.5:
    signal, signal_col, bg_col = "DOVISH PIVOT", "#28a745", "#fafffa"
    desc = "Current rates are restrictive relative to the model. Conditions support a transition toward monetary easing."
else:
    signal, signal_col, bg_col = "NEUTRAL / CALIBRATED", "#6c757d", "#f8f9fa"
    desc = "The current policy stance is appropriately calibrated to the prevailing inflation and growth outlook."

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown(f"""
    <div style="background-color: {bg_col}; padding: 30px; border-radius: 15px; border: 1px solid {signal_col}; color: #31333F;">
        <h3 style="color: {signal_col}; margin-top: 0;">Signal: {signal}</h3>
        <p style="font-size: 1.15rem; line-height: 1.6;">{desc}</p>
        <p style="font-size: 0.95rem; color: #555;"><b>Quantitative Gap:</b> {gap*100:.0f} basis points vs. {market} benchmark.</p>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.markdown("""
    #### 🏛️ Institutional Note: The Trilemma
    For your grad application: Central banks in Emerging Markets (like **India**) often navigate the <b>'Policy Trilemma'</b>—the impossibility of having a fixed exchange rate, free capital flow, and independent monetary policy simultaneously. 
    
    *High oil shocks often force a 'growth vs. stability' trade-off, making the Taylor Rule a baseline, but not the final word.*
    """)

st.caption("Developed for Quantitative Macro Research Portfolios | Data: Bloomberg/Refinitiv Synthetic")
