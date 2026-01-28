import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 1. TERMINAL HUD (UI/UX) ---
st.set_page_config(page_title="Macro Policy Terminal", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0E1117; }
    .stMetric { background-color: #1A1C24; padding: 15px; border-radius: 8px; border: 1px solid #30363D; }
    [data-testid="stMetricValue"] { color: #00FF41 !important; font-family: 'Courier New', monospace; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    h1, h2, h3 { color: #F0F6FC !important; font-family: 'Inter', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (Optimized) ---
@st.cache_data
def load_terminal_data():
    # Load Macro Sheet
    df_macro = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
    df_macro['Date'] = pd.to_datetime(df_macro['Date'])
    
    def load_fx(file):
        # Using the logic that worked in v7.0 to bypass README sheets
        xl = pd.ExcelFile(file)
        sheet = 'observation' if 'observation' in xl.sheet_names else xl.sheet_names[-1]
        df = xl.parse(sheet)
        df.columns = ['date', 'val']
        df['val'] = pd.to_numeric(df['val'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df.dropna().sort_values('date')

    return {
        "Main": df_macro,
        "India": load_fx('DEXINUS.xlsx'),
        "UK": load_fx('DEXUSUK.xlsx'),
        "Singapore": load_fx('AEXSIUS.xlsx')
    }

data = load_terminal_data()

# --- 3. SIDEBAR: POLICY INPUTS ---
st.sidebar.title("🛂 Policy Control Panel")
market = st.sidebar.selectbox("Jurisdiction", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("📈 Taylor Rule Calibration")
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 4.0, 1.5, help="The interest rate that neither stimulates nor contracts the economy.")
inflation_target = st.sidebar.slider("Inflation Target (%)", 1.0, 5.0, 2.0)

st.sidebar.divider()
st.sidebar.subheader("🌍 External Stress Simulation")
fx_shock = st.sidebar.slider("FX Depreciation Stress (%)", 0.0, 20.0, 0.0)
beta = st.sidebar.slider("Pass-through Beta (β)", 0.0, 1.0, 0.3, help="How much currency depreciation leaks into Headline CPI.")

# --- 4. ANALYTICS ENGINE ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx": data["India"]},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx": data["UK"]},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx": data["Singapore"]}
}

m = m_map[market]
fx_df = m['fx']
latest_macro = data["Main"].dropna(subset=[m['cpi']]).iloc[-1]
latest_fx = fx_df.iloc[-1]

# Augmented Taylor Rule Calculation
# i = r* + pi + 0.5(pi - target) + 0.5(output_gap) + (FX_shock * Beta)
current_pi = latest_macro[m['cpi']]
current_policy = latest_macro[m['rate']]
implied_pi = current_pi + (fx_shock * beta)
fair_value = r_star + implied_pi + 0.5 * (implied_pi - inflation_target)
action_gap = (fair_value - current_policy) * 100

# --- 5. DASHBOARD HUD ---
st.title(f"🏛️ {market} Monetary Surveillance")
st.caption(f"Last Updated: {latest_macro['Date'].strftime('%Y-%m-%d')} | Data Source: FRED & Global Macro Database")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Spot FX Rate", f"{latest_fx['val']:.2f}", help="Current Exchange Rate vs USD")
c2.metric("Headline CPI", f"{current_pi:.2f}%", help="Last reported Year-on-Year Inflation")
c3.metric("Model Fair Value", f"{fair_value:.2f}%", help="Implied rate based on Open-Economy Taylor Rule")
c4.metric("Policy Gap", f"{action_gap:+.0f} bps", delta_color="inverse", help="Positive value suggests tightening is required")

# --- 6. ADVANCED CHARTING ---
st.subheader("Historical Policy & Exchange Rate Correlation")
fig = go.Figure()

# Plot Interest Rate (Primary Y)
fig.add_trace(go.Scatter(
    x=data["Main"]['Date'], y=data["Main"][m['rate']],
    name="Policy Rate (%)", line=dict(color='#00FF41', width=3),
    fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.1)'
))

# Plot FX Rate (Secondary Y)
fig.add_trace(go.Scatter(
    x=fx_df['date'], y=fx_df['val'],
    name="FX Rate (vs USD)", yaxis="y2",
    line=dict(color='#FFD700', width=1.5, dash='dot')
))

fig.update_layout(
    template="plotly_dark",
    hovermode="x unified",
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    yaxis=dict(title="Policy Rate (%)", gridcolor="#30363D", zeroline=False),
    yaxis2=dict(title="Exchange Rate", overlaying="y", side="right", showgrid=False),
    margin=dict(l=0, r=0, t=40, b=0),
    height=500
)

st.plotly_chart(fig, use_container_width=True)

# --- 7. MAS COMMENTARY MODULE ---
st.divider()
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("📝 Policy Assessment")
    status = "Hawkish" if action_gap > 50 else "Dovish" if action_gap < -50 else "Neutral"
    st.write(f"""
    The current policy stance for **{market}** is categorized as **{status}**. 
    Given an inflation target of {inflation_target}%, the model suggests that the central bank has 
    **{abs(action_gap):.0f} bps** of room to {"hike" if action_gap > 0 else "cut"} rates to reach equilibrium.
    """)

with col_b:
    st.subheader("🔍 Transmission Channels")
    st.write(f"""
    * **Currency Pass-through:** A {fx_shock}% depreciation contributes **{fx_shock * beta:.2f}%** to simulated inflation.
    * **Real Rate Buffer:** With a policy rate of {current_policy}% and CPI at {current_pi}%, the implied real rate is **{(current_policy - current_pi):.2f}%**.
    """)
