import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Policy Lab", layout="wide", page_icon="📈")

@st.cache_data
def load_data():
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    if not os.path.exists(file_name):
        st.error(f"File '{file_name}' not found in the repository.")
        st.stop()

    xl = pd.ExcelFile(file_name)
    
    # STRATEGY: Prioritize the "Macro data" sheet as it is the cleanest
    target_sheet = "Macro data"
    if target_sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=target_sheet)
    else:
        # Fallback to the first sheet if "Macro data" isn't found
        df = pd.read_excel(xl, sheet_name=xl.sheet_names[0])
    
    # Clean column names (remove spaces)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Convert Date column safely
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date')
    else:
        st.error("Could not find a 'Date' column in the Excel sheet.")
        st.write("Available columns:", list(df.columns))
        st.stop()
        
    return df

# --- LOAD DATA ---
df = load_data()

# --- SIDEBAR ---
st.sidebar.title("🕹️ Control Panel")
market = st.sidebar.selectbox("Select Market", ["India", "UK", "Singapore"])

st.sidebar.divider()
st.sidebar.subheader("Taylor Rule Settings")
# Default targets based on typical central bank mandates
def_inf = 4.0 if market == "India" else 2.0
target_inf = st.sidebar.slider("Inflation Target (%)", 0.0, 6.0, def_inf)
r_star = st.sidebar.slider("Neutral Rate (r*)", 0.0, 5.0, 1.5)

st.sidebar.divider()
st.sidebar.subheader("⚠️ Stress Test")
oil_shock = st.sidebar.slider("Energy Price Spike (%)", 0, 100, 0)

# --- MODEL LOGIC ---
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "beta": 0.12},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "beta": 0.07},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "beta": 0.10}
}
m = m_map[market]

# Verify columns exist
if m['cpi'] not in df.columns or m['rate'] not in df.columns:
    st.error(f"Required columns ({m['cpi']}, {m['rate']}) not found in the data.")
    st.write("Columns found:", list(df.columns))
    st.stop()

# Calculations
current_inf = df[m['cpi']].iloc[-1]
shock_impact = oil_shock * m['beta']
adj_inf = current_inf + shock_impact
current_rate = df[m['rate']].iloc[-1]

# Taylor Rule: i = r* + pi + 0.5(pi - target)
suggested_rate = r_star + adj_inf + 0.5 * (adj_inf - target_inf)

# --- DASHBOARD LAYOUT ---
st.title(f"🏦 {market}: Monetary Policy Analysis")
st.caption("Quantitative Research Terminal for Interest Rate Projections")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Headline CPI", f"{current_inf:.2f}%")
col2.metric("Adj. CPI (Shock)", f"{adj_inf:.2f}%", 
            delta=f"+{shock_impact:.2f}%" if oil_shock > 0 else None, delta_color="inverse")
col3.metric("Actual Policy Rate", f"{current_rate:.2f}%")
col4.metric("Taylor Fair Value", f"{suggested_rate:.2f}%", 
            delta=f"{(suggested_rate-current_rate):.2f}%", delta_color="inverse")

# --- CHART ---
fig = go.Figure()

# Historical Inflation
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="Inflation", 
                         line=dict(color="#d32f2f", width=1.5, dash='dot')))
# Historical Policy Rate
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['rate']], name="Actual Policy Rate", 
                         line=dict(color="#002d72", width=3)))
# Model Projection Point
fig.add_trace(go.Scatter(x=[df['Date'].iloc[-1]], y=[suggested_rate], 
                         mode='markers', marker=dict(size=15, color='#ff9800', symbol='star'), 
                         name='Model Suggested Rate'))

fig.update_layout(
    height=450, 
    margin=dict(l=0, r=0, t=30, b=0), 
    legend=dict(orientation="h", y=1.1), 
    plot_bgcolor="white",
    hovermode="x unified"
)
st.plotly_chart(fig, use_container_width=True)

# --- ANALYSIS SECTION ---
st.subheader("🧐 Analyst Assessment")
gap = (suggested_rate - current_rate) * 100

if gap > 50:
    signal, color = "HAWKISH", "red"
    note = f"The model indicates a significant 'Policy Gap' of {gap:.0f} bps. The central bank is likely 'behind the curve'."
elif gap < -50:
    signal, color = "DOVISH", "green"
    note = f"The current stance appears overly restrictive by {abs(gap):.0f} bps. Conditions favor a pivot toward easing."
else:
    signal, color = "NEUTRAL", "gray"
    note = "Policy is currently well-aligned with the Taylor Rule fair value."

st.markdown(f"""
<div style="background-color: #ffffff; padding: 20px; border-left: 5px solid {color}; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
    <strong>Strategic Bias: <span style="color:{color};">{signal}</span></strong><br><br>
    {note}<br><br>
    <em><strong>Interactivity:</strong> Adjust the 'Energy Price Spike' slider to simulate supply-side shocks and watch the Taylor Fair Value (orange star) react.</em>
</div>
""", unsafe_allow_html=True)
