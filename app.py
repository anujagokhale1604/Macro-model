import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="📜")

# --- STYLING (Paper Theme) ---
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; border-right: 2px solid #D1C7B7 !important; }
    [data-testid="stWidgetLabel"] p, label p { color: #2E5077 !important; font-weight: 800 !important; }
    [data-testid="stMetricValue"] { color: #2E5077 !important; font-weight: 800; }
    html, body, .stMarkdown, p, li, span { color: #1A1C1E !important; font-family: 'Georgia', serif !important; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_data():
    # 1. Load Macro Data
    df_macro = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - Macro data.csv')
    df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
    
    # 2. Load FX Data
    fx_files = {
        "India": 'DEXINUS.xlsx - Daily.csv',
        "UK": 'DEXUSUK.xlsx - Daily.csv',
        "Singapore": 'AEXSIUS.xlsx - Annual.csv'
    }
    fx_frames = {}
    for k, v in fx_files.items():
        try:
            temp_fx = pd.read_csv(v)
            temp_fx.columns = ['date', 'val']
            temp_fx['date'] = pd.to_datetime(temp_fx['date'], errors='coerce')
            fx_frames[k] = temp_fx.dropna()
        except: fx_frames[k] = pd.DataFrame(columns=['date', 'val'])

    return df_macro.dropna(subset=['Date']), fx_frames

df, fx_dict = load_data()

# --- SIDEBAR: CONTROLS ---
st.sidebar.title("📜 Policy Lab")
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

st.sidebar.subheader("🏗️ Model Calibration")
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, r_star_init)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, target_inf_init)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, gap_init)

st.sidebar.subheader("🧠 Banking Stance")
philosophy = st.sidebar.selectbox("Framework", ["Standard", "Hawk", "Dovish"], index=phil_idx)

# Philosophy logic
weights = {"Standard": (1.5, 0.2), "Hawk": (2.2, 0.1), "Dovish": (1.0, 0.5)}
inf_weight, smoothing = weights[philosophy]

# --- COLUMN FINDER (SOLVES THE ERROR) ---
# This looks for any column that contains BOTH the market name and the metric
def find_col(keyword, mkt):
    cols = [c for c in df.columns if mkt.lower() in c.lower() and keyword.lower() in c.lower()]
    return cols[0] if cols else None

cpi_col = find_col("CPI", market)
rate_col = find_col("Policy", market)

if not cpi_col or not rate_col:
    st.error(f"🔴 Missing Columns: Could not find CPI or Policy Rate for {market}")
    st.write("Available columns:", list(df.columns))
    st.stop()

# --- ANALYTICS ---
valid_df = df.dropna(subset=[cpi_col, rate_col])
latest_date = valid_df['Date'].max()
filtered_df = valid_df[valid_df['Date'] >= (latest_date - timedelta(days=5*365))]
latest = valid_df.iloc[-1]

base_inf = latest[cpi_col]
curr_rate = latest[rate_col]
raw_fv = r_star + base_inf + inf_weight * (base_inf - target_inf) + 0.5 * output_gap
fair_value = ( (1 - smoothing) * raw_fv ) + (smoothing * curr_rate)
gap_bps = (fair_value - curr_rate) * 100

# --- DASHBOARD ---
st.title(f"{market} Policy Intelligence")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Headline CPI", f"{base_inf:.2f}%")
c2.metric("Target Level", f"{target_inf:.1f}%")
c3.metric("Current Rate", f"{curr_rate:.2f}%")
c4.metric("Taylor Fair Value", f"{fair_value:.2f}%", f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- CHART (WITH FX INTEGRATION) ---
fig = go.Figure()

# Policy & Inflation
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[rate_col], name="Policy Rate", line=dict(color="#2E5077", width=3)))
fig.add_trace(go.Scatter(x=filtered_df['Date'], y=filtered_df[cpi_col], name="Inflation (YoY)", line=dict(color="#A68A64", width=2, dash='dot')))

# FX Data (Secondary Axis)
fx_df = fx_dict[market]
if not fx_df.empty:
    fig.add_trace(go.Scatter(x=fx_df['date'], y=fx_df['val'], name="FX Rate (RHS)", 
                             line=dict(color="#BC6C25", width=1), opacity=0.4, yaxis="y2"))

# Taylor Marker
fig.add_trace(go.Scatter(x=[latest['Date']], y=[fair_value], mode='markers', 
                         marker=dict(size=14, color='#BC6C25', symbol='diamond', line=dict(width=2, color='#1A1C1E')),
                         name="Model Fair Value"))

fig.update_layout(
    height=550, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    margin=dict(t=30, b=100),
    legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
    yaxis=dict(title="Rate / Inflation (%)", showgrid=True, gridcolor="#D1C7B7"),
    yaxis2=dict(title="Exchange Rate", overlaying="y", side="right", showgrid=False),
    xaxis=dict(showgrid=True, gridcolor="#D1C7B7")
)
st.plotly_chart(fig, use_container_width=True)

# --- TAYLOR METHODOLOGY EXPLANATION ---
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.markdown(f"""
    <div style="background-color: #E8E0D5; border-left: 10px solid #2E5077; padding: 25px; border-radius: 4px;">
        <h3 style="color: #2E5077; margin-top: 0;">Strategist Lean: {gap_bps:+.0f} bps</h3>
        <p>Based on the <b>{philosophy}</b> framework, the policy rate is currently <b>{'undervalued' if gap_bps > 0 else 'overvalued'}</b>.</p>
        <ul>
            <li>Real Neutral Rate (r*): {r_star}%</li>
            <li>Inflation Gap: {base_inf - target_inf:.2f}%</li>
            <li>Output Gap: {output_gap}%</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.subheader("📝 Taylor Rule Methodology")
    st.latex(r"i_t = r^* + \pi_t + 0.5(\pi_t - \pi^*) + 0.5(y_t - \bar{y}_t)")
    
    st.info("The Taylor Rule is a guiding principle used by central banks to adjust interest rates in response to changes in inflation and economic output to stabilize the economy.")
