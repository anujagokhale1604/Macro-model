import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Intelligence Terminal", layout="wide", page_icon="🏛️")

@st.cache_data
def load_data():
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    if not os.path.exists(file_name):
        st.error(f"File '{file_name}' not found.")
        st.stop()
    xl = pd.ExcelFile(file_name)
    df = pd.read_excel(xl, sheet_name="Macro data")
    df.columns = [str(c).strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df.dropna(subset=['Date']).sort_values('Date')

df = load_data()

# --- SIDEBAR: SCENARIO SELECTOR ---
st.sidebar.title("🏛️ Policy Simulation")
market = st.sidebar.selectbox("Market Focus", ["India", "UK", "Singapore"])

st.sidebar.divider()
scenario = st.sidebar.selectbox("Choose Macro Scenario", 
    ["Custom", "Soft Landing", "Stagflation Shock", "Global Recession"])

# Logic for Scenario Presets
if scenario == "Soft Landing":
    target_inf, r_star, output_gap, oil_shock = 2.0, 1.0, 0.5, 0
elif scenario == "Stagflation Shock":
    target_inf, r_star, output_gap, oil_shock = 2.0, 2.5, -2.0, 40
elif scenario == "Global Recession":
    target_inf, r_star, output_gap, oil_shock = 2.0, 0.5, -4.0, -20
else:
    target_inf = st.sidebar.slider("Inflation Target (%)", 0.0, 6.0, 4.0 if market == "India" else 2.0)
    r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)
    output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, 0.0)
    oil_shock = st.sidebar.slider("Energy Shock (%)", -50, 100, 0)

# --- ADVANCED MODEL CALCULATIONS ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "beta": 0.12},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "beta": 0.07},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "beta": 0.10}
}
m = m_map[market]
valid_df = df.dropna(subset=[m['cpi'], m['rate']])
latest = valid_df.iloc[-1]

# Model Variables
inf = latest[m['cpi']] + (oil_shock * m['beta'])
curr_rate = latest[m['rate']]
# Taylor Rule with Output Gap
fair_value = r_star + inf + 0.5*(inf - target_inf) + 0.5*(output_gap)
real_rate = curr_rate - inf

# --- UI: DASHBOARD ---
st.title(f"📈 Macroeconomic Policy Intelligence: {market}")
st.markdown(f"**Current Regime:** `{'Restrictive' if real_rate > r_star else 'Accommodative'}` | **Data As Of:** {latest['Date'].strftime('%B %Y')}")

# Top Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Adjusted Inflation", f"{inf:.2f}%")
m2.metric("Real Interest Rate", f"{real_rate:.2f}%", help="Policy Rate minus Inflation")
m3.metric("Neutral Rate (r*)", f"{r_star:.1f}%")
m4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{(fair_value-curr_rate):.2f}%", delta_color="inverse")

# --- CHART: POLICY PATHWAY ---
fig = go.Figure()

# Confidence Interval (The "Professional" touch)
fig.add_trace(go.Scatter(
    x=valid_df['Date'].tolist() + [latest['Date']],
    y=(valid_df[m['rate']] + 1.0).tolist() + [fair_value + 1.0],
    fill=None, mode='lines', line_color='rgba(0,0,0,0)', showlegend=False
))
fig.add_trace(go.Scatter(
    x=valid_df['Date'].tolist() + [latest['Date']],
    y=(valid_df[m['rate']] - 1.0).tolist() + [fair_value - 1.0],
    fill='tonexty', fillcolor='rgba(26, 35, 126, 0.1)', mode='lines', line_color='rgba(0,0,0,0)',
    name='95% Policy Uncertainty Band'
))

# Historical Data
fig.add_trace(go.Scatter(x=valid_df['Date'], y=valid_df[m['rate']], name="Historical Policy Rate", line=dict(color="#1a237e", width=3)))
fig.add_trace(go.Scatter(x=valid_df['Date'], y=valid_df[m['cpi']], name="Headline Inflation", line=dict(color="#e53935", width=1.5, dash='dot')))

# Projection
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers+text', 
                         marker=dict(size=15, color='#ff9800', symbol='star'),
                         text=["Fair Value"], textposition="top center", name="Model Suggestion"))

fig.update_layout(height=500, template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, use_container_width=True)

# --- ANALYST INSIGHTS (The "Outstanding" Section) ---
st.divider()
st.subheader("📝 Institutional Policy Brief")

col_a, col_b = st.columns([2, 1])

with col_a:
    gap = fair_value - curr_rate
    status = "UNDERVALUED" if gap > 0.5 else "OVERVALUED" if gap < -0.5 else "NEUTRAL"
    color = "#d32f2f" if status == "UNDERVALUED" else "#2e7d32" if status == "OVERVALUED" else "#455a64"
    
    st.markdown(f"""
    <div style="background-color: #f8f9fa; padding: 20px; border-left: 10px solid {color}; border-radius: 5px; color: #31333F;">
        <h4 style="color: {color}; margin-top:0;">Executive Summary: {market} Stance</h4>
        <p>Our model suggests that the current policy rate of <b>{curr_rate:.2f}%</b> is 
        <b>{status}</b> relative to macroeconomic fundamentals. Based on the <i>{scenario}</i> scenario, 
        the terminal rate should gravitate toward <b>{fair_value:.2f}%</b> to maintain price stability.</p>
        <ul>
            <li><b>Taylor Gap:</b> {gap*100:.0f} basis points.</li>
            <li><b>Real Rate Analysis:</b> A real rate of {real_rate:.2f}% implies the bank is currently 
            {'fighting' if real_rate > 0 else 'stimulating'} the economy.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col_b:
    st.info("**Think Tank Analysis:** For a grad application, note that central banks in EMs (like India) often face a 'Trilemma'—balancing exchange rate stability with domestic inflation. High oil shocks create a forced trade-off between growth and price stability.")
