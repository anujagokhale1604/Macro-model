import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="🏦")

@st.cache_data
def load_data():
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    if not os.path.exists(file_name):
        st.error(f"File '{file_name}' not found.")
        st.stop()

    xl = pd.ExcelFile(file_name)
    target_sheet = "Macro data"
    df = pd.read_excel(xl, sheet_name=target_sheet if target_sheet in xl.sheet_names else xl.sheet_names[0])
    
    df.columns = [str(c).strip() for c in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    return df.dropna(subset=['Date']).sort_values('Date')

# --- LOAD DATA ---
df = load_data()

# --- SIDEBAR: ADVANCED CONTROLS ---
st.sidebar.title("🎮 Model Parameters")
market = st.sidebar.selectbox("Select Market", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("Taylor Rule Inputs")
target_inf = st.sidebar.slider("Inflation Target (%)", 0.0, 6.0, 4.0 if market == "India" else 2.0)
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, 1.5)
output_gap = st.sidebar.slider("Output Gap (%)", -5.0, 5.0, 0.0, help="Positive = Economy is overheating")

st.sidebar.divider()
st.sidebar.subheader("Policy Sensitivity")
inf_weight = st.sidebar.slider("Inflation Weight (λπ)", 0.5, 2.0, 1.5)
ygap_weight = st.sidebar.slider("Output Weight (λy)", 0.0, 1.0, 0.5)
smoothing = st.sidebar.slider("Interest Rate Smoothing", 0.0, 1.0, 0.0, help="High = Bank moves slowly")

# --- MODEL LOGIC ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}
m = m_map[market]

# DATA SANITIZATION: Find the last valid row for this specific country
valid_df = df.dropna(subset=[m['cpi'], m['rate']])

if valid_df.empty:
    st.error(f"No valid data found for {market}. Check your Excel columns.")
    st.stop()

# Get latest valid data points
latest_row = valid_df.iloc[-1]
current_inf = latest_row[m['cpi']]
current_rate = latest_row[m['rate']]
as_of_date = latest_row['Date'].strftime('%b %Y')

# Taylor Rule Calculation: i = r* + pi + λπ(pi - target) + λy(output_gap)
raw_suggested = r_star + current_inf + inf_weight * (current_inf - target_inf) + ygap_weight * (output_gap)

# Apply Smoothing: New Rate = (1-ρ)*Suggested + ρ*Current
suggested_rate = ( (1 - smoothing) * raw_suggested ) + (smoothing * current_rate)

# --- DASHBOARD ---
st.title(f"🏦 {market} Policy Terminal")
st.caption(f"Last Full Data Entry: {as_of_date}")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current Inflation", f"{current_inf:.2f}%")
c2.metric("Output Gap", f"{output_gap:+.1f}%")
c3.metric("Current Policy Rate", f"{current_rate:.2f}%")
c4.metric("Taylor Fair Value", f"{suggested_rate:.2f}%", f"{(suggested_rate-current_rate):.2f}%", delta_color="inverse")

# --- CHART ---
fig = go.Figure()

# Historical Lines
fig.add_trace(go.Scatter(x=valid_df['Date'], y=valid_df[m['cpi']], name="Inflation", line=dict(color="#e53935", width=1.5, dash='dot')))
fig.add_trace(go.Scatter(x=valid_df['Date'], y=valid_df[m['rate']], name="Policy Rate", line=dict(color="#1a237e", width=3)))

# Model Fair Value Star (Pinned to the last valid date)
fig.add_trace(go.Scatter(
    x=[latest_row['Date']], 
    y=[suggested_rate], 
    mode='markers', 
    marker=dict(size=18, color='#ff9800', symbol='star', line=dict(width=2, color='white')),
    name='Fair Value Projection'
))

fig.update_layout(
    height=450, 
    template="plotly_white",
    hovermode="x unified",
    legend=dict(orientation="h", y=1.1, x=0),
    xaxis=dict(showgrid=False),
    yaxis=dict(title="Percent (%)", showgrid=True, gridcolor="#f0f0f0")
)
st.plotly_chart(fig, use_container_width=True)

# --- VISIBLE ASSESSMENT BOX ---
st.subheader("🧐 Model Assessment")
gap = (suggested_rate - current_rate) * 100

if gap > 75:
    signal, color, text_col = "STRONG HAWKISH", "#b71c1c", "#ffffff"
    note = "Policy is significantly behind the curve. The model suggests a major rate hike cycle is required to cool inflation."
elif gap > 20:
    signal, color, text_col = "HAWKISH BIAS", "#e53935", "#ffffff"
    note = "The suggested rate is above current levels. Tightening bias recommended."
elif gap < -75:
    signal, color, text_col = "STRONG DOVISH", "#1b5e20", "#ffffff"
    note = "Policy is overly restrictive. Conditions warrant immediate and significant easing to support growth."
elif gap < -20:
    signal, color, text_col = "DOVISH BIAS", "#43a047", "#ffffff"
    note = "Current rates are higher than the fair value estimate. A pivot toward cuts is likely."
else:
    signal, color, text_col = "NEUTRAL", "#455a64", "#ffffff"
    note = "The central bank's current stance is well-calibrated to the Taylor Rule fair value."

st.markdown(f"""
<div style="background-color: {color}; padding: 25px; border-radius: 12px; color: {text_col}; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h2 style="margin-top: 0; color: {text_col}; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 10px;">
        Signal: {signal}
    </h2>
    <p style="font-size: 1.2rem; font-weight: 500;">{note}</p>
    <div style="background-color: rgba(255,255,255,0.1); padding: 10px; border-radius: 5px; margin-top: 15px;">
        <small><strong>Data Note:</strong> This assessment is based on the <b>{as_of_date}</b> data print. 
        Adjust the <b>Output Gap</b> and <b>Smoothing</b> sliders in the sidebar to see how 'sticky' the policy should be.</small>
    </div>
</div>
""", unsafe_allow_html=True)
