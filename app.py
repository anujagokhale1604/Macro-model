import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide", page_icon="🏛️")

# Custom Professional Styling
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #eeeeee;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .assessment-container {
        padding: 25px;
        border-radius: 12px;
        border-left: 8px solid;
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

# --- SIDEBAR ---
st.sidebar.title("🏛️ Strategic Analysis")
market = st.sidebar.selectbox("Market Focus", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("📅 Data Horizon")
horizon = st.sidebar.radio("View Period", ["Last 1 Year", "Last 5 Years", "Full History"], index=1)

st.sidebar.divider()
st.sidebar.subheader("⚙️ Model Parameters")
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 5.0, 4.0 if market == "India" else 2.0)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, 0.0)

# --- ANALYTICS ENGINE ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])

# Timeline Filtering
latest_date = valid_df['Date'].max()
if horizon == "Last 1 Year":
    start_point = latest_date - timedelta(days=365)
elif horizon == "Last 5 Years":
    start_point = latest_date - timedelta(days=5*365)
else:
    start_point = valid_df['Date'].min()

filtered_df = valid_df[valid_df['Date'] >= start_point]
latest = valid_df.iloc[-1]

# Calculations
inf = latest[m['cpi']]
curr_rate = latest[m['rate']]
fair_value = r_star + inf + 0.5*(inf - target_inf) + 0.5*(output_gap)
gap = fair_value - curr_rate

# --- DASHBOARD LAYOUT ---
st.title(f"🚀 {market} Monetary Policy Terminal")
st.caption(f"Active Analysis for {latest['Date'].strftime('%B %Y')} | Standard Taylor Rule Model")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Headline CPI", f"{inf:.2f}%")
m2.metric("Policy Rate", f"{curr_rate:.2f}%")
m3.metric("Model Fair Value", f"{fair_value:.2f}%")
m4.metric("Policy Gap", f"{gap*100:+.0f} bps", delta_color="inverse")

# Main Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['rate']], name="Policy Rate", line=dict(color="#0052cc", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[m['cpi']], name="CPI (YoY)", line=dict(color="#ff4b4b", width=1.5, dash='dot')))
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=18, color='#ffc107', symbol='star', line=dict(width=1, color='black')),
                         name="Terminal Rate Suggestion"))

fig.update_layout(
    height=400, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", y=1.1, x=0),
    xaxis=dict(showgrid=True, gridcolor="#f5f5f5"),
    yaxis=dict(showgrid=True, gridcolor="#f5f5f5", title="Percent (%)")
)
st.plotly_chart(fig, use_container_width=True)

# --- INSIGHTS SECTION ---
st.divider()

if gap > 0.5:
    sig, col, bg = "HAWKISH BIAS", "#d32f2f", "#fff5f5"
    msg = "The policy rate is trailing fundamentals. Tightening is recommended to anchor inflation expectations."
elif gap < -0.5:
    sig, col, bg = "DOVISH PIVOT", "#2e7d32", "#f5fff5"
    msg = "Current rates are restrictive relative to the model. Conditions support a transition toward monetary easing."
else:
    sig, col, bg = "NEUTRAL", "#455a64", "#f8f9fa"
    msg = "The current stance is appropriately calibrated to the prevailing inflation and growth outlook."

left, right = st.columns([2, 1])

with left:
    # Use Markdown for the box to ensure formatting (bolding/spacing) works
    st.markdown(f"""
    <div style="background-color: {bg}; border: 1px solid {col}; border-left: 8px solid {col}; padding: 25px; border-radius: 10px; color: #31333F;">
        <h3 style="color: {col}; margin-top: 0; font-family: sans-serif;">Signal: {sig}</h3>
        <p style="font-size: 1.1rem; line-height: 1.6;">{msg}</p>
        <hr style="opacity: 0.1; border-color: {col};">
        <p style="font-size: 0.9rem;"><strong>Quantitative Analysis:</strong> The Taylor Gap is currently <strong>{gap*100:.0f} basis points</strong>. 
        This is modeled using a neutral real rate (r*) of {r_star}% against a target inflation of {target_inf}%.</p>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.subheader("🏛️ Institutional Context")
    st.markdown(f"""
    **The Policy Trilemma**
    
    Central banks in Emerging Markets, particularly **{market}**, navigate a fundamental trade-off. It is theoretically impossible to maintain a fixed exchange rate, free capital movement, and independent monetary policy simultaneously.
    
    * **Growth vs. Stability:** High commodity or oil shocks often force a deviation from Taylor Rule prescriptions.
    * **Currency Protection:** Banks may maintain higher rates than the model suggests to prevent capital flight, even if domestic inflation is cooling.
    """)

st.caption("Quantitative Policy Lab | Data Source: EM Research Portfolio Analytics")
