import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- 1. DATA ENGINE (High-Fidelity Processing) ---
@st.cache_data
def load_and_process_intelligence():
    # Load Primary Macro Data
    try:
        policy_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Policy_Rate', engine='openpyxl')
        cpi_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Macro data', engine='openpyxl')
    except Exception as e:
        st.error(f"Data Connection Error: {e}")
        return pd.DataFrame()

    # Reconstruct Policy Dates
    current_year, cleaned_rows = None, []
    months_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                  'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    
    for _, row in policy_raw.iterrows():
        val = str(row['Date']).strip().split('.')[0]
        if val.isdigit() and len(val) == 4: current_year = int(val)
        elif val in months_map and current_year:
            dt = pd.Timestamp(year=current_year, month=months_map[val], day=1)
            cleaned_rows.append({'Date': dt, 'India_Policy': row['India'], 'UK_Policy': row['UK'], 'SG_Policy': row['Singapore']})
    
    df = pd.DataFrame(cleaned_rows)

    # Process FX (Daily to Monthly Averages)
    def get_fx(file, col, label):
        try:
            f_df = pd.read_excel(file, sheet_name='Daily', engine='openpyxl')
            f_df['observation_date'] = pd.to_datetime(f_df['observation_date'])
            f_df[col] = pd.to_numeric(f_df[col], errors='coerce')
            return f_df.resample('MS', on='observation_date').mean().reset_index().rename(columns={'observation_date': 'Date', col: label})
        except: return pd.DataFrame(columns=['Date', label])

    inr = get_fx('DEXINUS.xlsx', 'DEXINUS', 'USDINR')
    gbp = get_fx('DEXUSUK.xlsx', 'DEXUSUK', 'USDGBP')

    # Master Join
    df = df.merge(inr, on='Date', how='left').merge(gbp, on='Date', how='left')
    return df.sort_values('Date')

# --- 2. EXECUTIVE UI SETUP ---
st.set_page_config(page_title="Global Macro Insights | Alpha Terminal", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏛️ Global Macro-Financial Intelligence Terminal")
st.caption("Strategic Analysis for Institutional Decision Making | JPMC, MAS, BCG Data Standard")

df = load_and_process_intelligence()

# --- 3. THE "IMPRESSION" LAYER: SIDEBAR CONTROLS ---
with st.sidebar:
    st.header("Terminal Controls")
    selected_market = st.selectbox("Market Focus", ["India (Emerging)", "UK (Developed)"])
    
    st.subheader("Data Toggles")
    show_policy = st.toggle("Interest Rate Path", value=True)
    show_fx = st.toggle("FX Spot (Monthly Avg)", value=True)
    
    st.subheader("Advanced Analytics")
    calc_corr = st.checkbox("Show Correlation Matrix")
    show_vol = st.checkbox("Show Volatility (Standard Deviation)")
    
    st.divider()
    st.markdown("**Note:** This terminal reconciles human-readable institutional datasets with daily market spot rates via high-frequency resampling.")

# Market Logic
if "India" in selected_market:
    policy_col, fx_col, label = 'India_Policy', 'USDINR', 'INR'
else:
    policy_col, fx_col, label = 'UK_Policy', 'USDGBP', 'GBP'

# --- 4. EXECUTIVE DASHBOARD ---
if not df.empty:
    # Row 1: Key Metrics (The "Consultancy" Look)
    m1, m2, m3, m4 = st.columns(4)
    curr_policy = df[policy_col].iloc[-1]
    prev_policy = df[policy_col].iloc[-12] if len(df)>12 else 0
    curr_fx = df[fx_col].iloc[-1]
    
    m1.metric(f"Current {label} Policy Rate", f"{curr_policy}%", f"{round(curr_policy - prev_policy, 2)}% YoY")
    m2.metric(f"USD/{label} Spot", f"{round(curr_fx, 2)}")
    
    # Row 2: The Core Visualization
    st.subheader(f"Strategic View: {selected_market}")
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if show_policy:
        fig.add_trace(go.Scatter(x=df['Date'], y=df[policy_col], name="Policy Rate (%)", 
                                line=dict(color='#1f77b4', width=3)), secondary_y=False)
    
    if show_fx:
        fig.add_trace(go.Scatter(x=df['Date'], y=df[fx_col], name=f"USD/{label} FX", 
                                line=dict(color='#ff7f0e', width=3, dash='dot')), secondary_y=True)

    fig.update_layout(height=550, template="plotly_white", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_yaxes(title_text="Policy Rate (%)", secondary_y=False)
    fig.update_yaxes(title_text=f"FX Rate (USD/{label})", secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)

    # Row 3: Advanced Intelligence (The "Think Tank" Look)
    col_left, col_right = st.columns(2)
    
    with col_left:
        if calc_corr:
            st.write("### 📊 Market Correlation Matrix")
            corr = df[[policy_col, fx_col]].corr()
            st.dataframe(corr.style.background_gradient(cmap='RdYlGn'))
            st.caption("Measures the strength of the relationship between Central Bank moves and Currency value.")

    with col_right:
        if show_vol:
            st.write("### 📉 Realized Volatility")
            vol = df[[policy_col, fx_col]].rolling(window=12).std()
            st.line_chart(vol)
            st.caption("12-Month Rolling Standard Deviation (Market Stability Index).")

else:
    st.error("System Offline: Ensure .xlsx source files are in the repository root.")
