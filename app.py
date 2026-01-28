import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 1. SETTINGS & INSTITUTIONAL STYLE ---
st.set_page_config(page_title="Macro Policy Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stMetricValue"] { color: #1e3a8a; font-weight: 700; }
    .stSidebar { background-color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE REWRITTEN DATA ENGINE (FIXED) ---
@st.cache_data
def load_and_merge_fixed():
    try:
        # A. Load Macro Data (Monthly)
        df_macro = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - Macro data.csv')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'])
        df_macro['Year'] = df_macro['Date'].dt.year

        # B. Load GDP Data (Fixing the "Unnamed" Header Issue)
        df_gdp_raw = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - GDP_Growth.csv')
        
        # Based on file inspection:
        # Col 0 = Year | Col 2 = India | Col 3 = Singapore | Col 4 = UK
        df_gdp = df_gdp_raw.iloc[1:, [0, 2, 3, 4]].copy()
        df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        
        # Clean numerical values
        df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')
        for col in ['GDP_India', 'GDP_Singapore', 'GDP_UK']:
            df_gdp[col] = pd.to_numeric(df_gdp[col], errors='coerce')
        
        # C. Merge (Joining Monthly Macro with Annual GDP)
        df_merged = pd.merge(df_macro, df_gdp.dropna(subset=['Year']), on='Year', how='left')
        return df_merged, None
    except Exception as e:
        return None, str(e)

df, err = load_and_merge_fixed()

if err:
    st.error(f"📡 System Integration Error: {err}")
    st.stop()

# --- 3. SCENARIO & JURISDICTION CONTROLS ---
st.sidebar.title("🛂 Policy Control Unit")
market = st.sidebar.selectbox("Jurisdiction", ["India", "UK", "Singapore"])

st.sidebar.subheader("🎯 Macro Scenarios")
scen = st.sidebar.radio("Policy Stance", ["Hawkish", "Neutral", "Dovish"])

# Central Bank Scenarios
params = {
    "Hawkish": {"r_star": 2.5, "target": 2.0, "note": "Aggressive Inflation-Targeting"},
    "Neutral": {"r_star": 1.5, "target": 2.5, "note": "Equilibrium Policy Path"},
    "Dovish":  {"r_star": 0.5, "target": 3.5, "note": "Growth-Supportive/Accommodative"}
}
p = params[scen]

# --- 4. EXACT COLUMN MAPPING ---
# This ensures the code finds "CPI_India" and "Policy_India" correctly
mapping = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India", "gdp": "GDP_India", "pot": 5.5},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "gdp": "GDP_UK", "pot": 2.0},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "gdp": "GDP_Singapore", "pot": 2.5}
}
m = mapping[market]

# --- 5. ANALYTICS (TAYLOR RULE) ---
# Get latest non-null data
latest = df.dropna(subset=[m['cpi'], m['rate'], m['gdp']]).iloc[-1]

inf = latest[m['cpi']]
repo = latest[m['rate']]
gdp_act = latest[m['gdp']]
pot_gdp = m['pot']

# Taylor Rule: Rate = r* + pi + 0.5(pi - target) + 0.5(GDP - Potential)
implied = p['r_star'] + inf + 0.5*(inf - p['target']) + 0.5*(gdp_act - pot_gdp)
gap_bps = (implied - repo) * 100

# --- 6. EXECUTIVE HUD ---
st.title(f"🏛️ Policy Intelligence Terminal | {market}")
st.write(f"**Current Strategy:** `{p['note']}`")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current Rate", f"{repo:.2f}%")
c2.metric("CPI Inflation", f"{inf:.2f}%")
c3.metric("GDP Growth", f"{gdp_act:.1f}%")
c4.metric("Taylor Implied", f"{implied:.2f}%", delta=f"{gap_bps:+.0f} bps", delta_color="inverse")

# --- 7. CORE MACRO CHART ---
st.subheader("Policy vs. Macro Fundamentals")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['rate']], name="Policy Rate", line=dict(color='#1e3a8a', width=4)))
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="Inflation", line=dict(color='#dc2626', dash='dot')))
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['gdp']], name="GDP Growth", line=dict(color='#16a34a', dash='dash')))

fig.update_layout(template="simple_white", height=500, hovermode="x unified",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)

# --- 8. STRATEGIST NOTES & METHODOLOGY ---
st.divider()
la, lb = st.columns(2)

with la:
    st.subheader("📑 Strategist Lean Note")
    if gap_bps > 75:
        st.error(f"**Action: HAWKISH LEAN.** Model suggests the central bank is significantly behind the curve by **{gap_bps:+.0f} bps**.")
    elif gap_bps < -75:
        st.success(f"**Action: DOVISH LEAN.** Substantial room for monetary easing detected.")
    else:
        st.info("**Action: NEUTRAL LEAN.** Current policy is appropriately positioned.")
    
    st.markdown(f"""
    **Deep Dive:**
    - Real Rate Buffer: **{(repo-inf):.2f}%**
    - Output Gap: **{(gdp_act - pot_gdp):.1f}%**
    """)

with lb:
    st.subheader("📝 Taylor Method Explanation")
    
    st.write("The Taylor Rule provides a benchmark for the 'Neutral' interest rate level based on economic deviations:")
    st.latex(r"i = r^* + \pi + 0.5(\pi - \pi^*) + 0.5(y - y^*)")
    st.markdown("""
    - **Neutral Real Rate ($r^*$):** {rstar}% (Set by sidebar stance).
    - **Inflation Target ($\pi^*$):** {target}% (Set by sidebar stance).
    - **Output Gap ($y - y^*$):** Actual Growth vs. Potential (Assumed {pot}% for {country}).
    """.format(rstar=p['r_star'], target=p['target'], pot=pot_gdp, country=market))

st.caption("Terminal v9.5 | Macro Core Edition | Powered by Unified Analytics")
