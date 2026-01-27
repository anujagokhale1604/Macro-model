import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# 1. Page Config
st.set_page_config(page_title="Macro FX Policy Lab", layout="wide")

# 2. Force Black Text CSS
st.markdown("""
    <style>
    .stApp { background-color: #F2EBE3 !important; }
    [data-testid="stSidebar"] { background-color: #E8E0D5 !important; }
    p, span, label, h1, h2, h3, .stWidgetLabel p {
        color: #000000 !important;
        font-weight: 700 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. Sidebar - FX TOGGLES ARE HERE
st.sidebar.title("🏛️ Policy Lab")
market = st.sidebar.selectbox("1. Select Market", ["India", "UK", "Singapore"])

st.sidebar.header("🌍 2. External Stability (FX)")
# IF YOU SEE THESE TWO, IT WORKED:
fx_deprec = st.sidebar.slider("Simulate FX Depreciation (%)", 0.0, 20.0, 0.0)
fx_beta = st.sidebar.slider("FX Sensitivity (Pass-through)", 0.0, 1.0, 0.2)

st.sidebar.header("🏗️ 3. Model Calibration")
r_star = st.sidebar.slider("Neutral Real Rate (r*)", 0.0, 5.0, 1.5)
target_inf = st.sidebar.slider("Inflation Target (%)", 1.0, 6.0, 2.0)

# 4. Data Loading (Safe Wrapper)
@st.cache_data
def load_data():
    try:
        df = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name="Macro data")
        inr = pd.read_csv('DEXINUS.xlsx - Daily.csv', parse_dates=['observation_date'])
        gbp = pd.read_csv('DEXUSUK.xlsx - Daily.csv', parse_dates=['observation_date'])
        sgd = pd.read_csv('AEXSIUS.xlsx - Annual.csv', parse_dates=['observation_date'])
        return df, inr, gbp, sgd
    except Exception as e:
        st.error(f"Data loading failed: {e}")
        return None, None, None, None

df_macro, df_inr, df_gbp, df_sgd = load_data()

# 5. Dashboard Logic
if df_macro is not None:
    m_map = {
        "India": {"cpi": "CPI_India", "rate": "Policy_India", "fx": df_inr, "col": "DEXINUS"},
        "UK": {"cpi": "CPI_UK", "rate": "Policy_UK", "fx": df_gbp, "col": "DEXUSUK"},
        "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore", "fx": df_sgd, "col": "AEXSIUS"}
    }
    m = m_map[market]
    
    # Calculate Taylor Rule + FX Premium
    base_inf = df_macro.dropna(subset=[m['cpi']]).iloc[-1][m['cpi']]
    curr_rate = df_macro.dropna(subset=[m['rate']]).iloc[-1][m['rate']]
    fair_value = r_star + base_inf + 1.5*(base_inf - target_inf) + (fx_deprec * fx_beta)
    
    st.title(f"{market} Policy Intelligence")
    c1, c2, c3 = st.columns(3)
    c1.metric("Headline CPI", f"{base_inf:.2f}%")
    c2.metric("Taylor Fair Value", f"{fair_value:.2f}%")
    c3.metric("Current Rate", f"{curr_rate:.2f}%")

    # Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_macro['Date'], y=df_macro[m['rate']], name="Policy Rate", line=dict(color="black")))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)
