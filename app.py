import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. NEUTRAL-ADAPTIVE UI ---
st.set_page_config(page_title="Strategic Macro Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #fdfdfd; }
    [data-testid="stMetricValue"] { color: #1a365d; font-weight: 800; }
    .stSidebar { background-color: #f8fafc !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ROBUST DATA ENGINE ---
@st.cache_data
def load_and_map_data():
    try:
        # Load Files
        df_m = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx')
        df_m.columns = [str(c).strip() for c in df_m.columns]
        
        # Load FX
        def fetch_fx(f):
            xl = pd.ExcelFile(f)
            df = xl.parse(xl.sheet_names[-1])
            df.columns = ['date', 'val']
            df['date'] = pd.to_datetime(df['date'])
            return df.dropna()

        return {
            "Macro": df_m,
            "India": fetch_fx('DEXINUS.xlsx'),
            "UK": fetch_fx('DEXUSUK.xlsx'),
            "Singapore": fetch_fx('AEXSIUS.xlsx')
        }
    except Exception as e:
        st.error(f"⚠️ File Load Error: {e}")
        return None

data = load_and_map_data()

# --- 3. FUZZY MAPPING (JPMC Research Style) ---
def get_market_columns(market, columns):
    # Pattern matching for institutional data naming
    patterns = {
        "cpi": ["cpi", "inflation", "price index"],
        "gdp": ["gdp", "growth", "output"],
        "rate": ["repo", "policy", "rate", "interest"]
    }
    
    results = {}
    for key, keywords in patterns.items():
        # Priority 1: Market + Keyword (e.g., "CPI India")
        found = [c for c in columns if market.lower() in c.lower() and any(k in c.lower() for k in keywords)]
        # Priority 2: Just Keyword (e.g., "Inflation")
        if not found:
            found = [c for c in columns if any(k in c.lower() for k in keywords)]
        
        results[key] = found[0] if found else None
    return results

if data:
    st.sidebar.title("🛂 Macro Control Unit")
    market = st.sidebar.selectbox("Jurisdiction", ["India", "UK", "Singapore"])
    cols = get_market_columns(market, data["Macro"].columns)

    # 🛑 THE FIX: Check for missing columns before dropna
    missing = [k for k, v in cols.items() if v is None]
    if missing:
        st.error(f"🔴 Missing Data Columns for {market}: {', '.join(missing)}")
        st.info("Check your Excel headers for words like 'CPI', 'GDP', or 'Rate'.")
        st.stop()

    # --- 4. SCENARIO ENGINE ---
    st.sidebar.subheader("🎯 Policy Scenarios")
    scen = st.sidebar.select_slider("Macro Stance", options=["Dovish", "Neutral", "Hawkish"], value="Neutral")
    
    params = {
        "Hawkish": {"r_star": 2.5, "beta": 0.5, "target": 2.0, "desc": "Inflation-fighting mode"},
        "Neutral": {"r_star": 1.5, "beta": 0.3, "target": 2.5, "desc": "Equilibrium guidance"},
        "Dovish": {"r_star": 0.5, "beta": 0.1, "target": 3.0, "desc": "Growth-supportive mode"}
    }
    p = params[scen]

    # --- 5. ANALYTICS ---
    df = data["Macro"].dropna(subset=[cols['cpi'], cols['gdp'], cols['rate']])
    latest = df.iloc[-1]
    
    # Taylor Rule Equation Implementation
    # Interest Rate = r* + Inflation + 0.5(Inflation - Target) + 0.5(Output Gap)
    inf, gdp, curr_rate = latest[cols['cpi']], latest[cols['gdp']], latest[cols['rate']]
    target_rate = p['r_star'] + inf + 0.5*(inf - p['target']) + 0.5*(gdp - 3.0) 
    gap = (target_rate - curr_rate) * 100

    # --- 6. VISUAL TERMINAL ---
    st.title(f"🏛️ Institutional Policy Dashboard: {market}")
    st.markdown(f"**Strategy Focus:** `{p['desc']}`")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Actual Policy Rate", f"{curr_rate:.2f}%")
    c2.metric("CPI Inflation", f"{inf:.2f}%")
    c3.metric("GDP Growth", f"{gdp:.2f}%")
    c4.metric("Policy Gap", f"{gap:+.0f} bps", delta_color="inverse")

    # Multivariate Timeline
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    date_col = [c for c in df.columns if 'date' in c.lower()][0]

    fig.add_trace(go.Scatter(x=df[date_col], y=df[cols['rate']], name="Repo Rate", line=dict(color='#1e3a8a', width=3)))
    fig.add_trace(go.Scatter(x=df[date_col], y=df[cols['cpi']], name="CPI", line=dict(color='#dc2626', dash='dot')))
    fig.add_trace(go.Scatter(x=df[date_col], y=df[cols['gdp']], name="GDP", line=dict(color='#059669', dash='dash')))
    
    # Secondary Axis for FX
    fx_df = data[market]
    fig.add_trace(go.Scatter(x=fx_df['date'], y=fx_df['val'], name="FX Rate (RHS)", opacity=0.4), secondary_y=True)

    fig.update_layout(height=500, template="simple_white", hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    st.subheader("📑 Strategic Research Note")
    st.info(f"The current policy gap of **{gap:+.0f} bps** suggests that under a **{scen}** scenario, the central bank is {'behind the curve' if gap > 50 else 'ahead of the curve' if gap < -50 else 'well-positioned'}. "
            f"Note the transmission of FX volatility onto the {market} yield curve.")
