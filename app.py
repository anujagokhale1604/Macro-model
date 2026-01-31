import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. PREMIUM STYLING ---
st.set_page_config(page_title="Macro Intelligence Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F5F5DC; color: #2c3e50; }
    section[data-testid="stSidebar"] { background-color: #2c3e50 !important; border-right: 2px solid #d4af37; }
    section[data-testid="stSidebar"] .stWidgetLabel, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span { color: #ffffff !important; font-weight: 600 !important; }
    .main-title { font-size: 38px; font-weight: 900; color: #002366; border-bottom: 4px solid #d4af37; padding-bottom: 10px; margin-bottom: 25px; }
    .note-box { padding: 18px; border-radius: 8px; border: 1px solid #d4af37; background-color: #ffffff; margin-bottom: 20px; color: #2c3e50; }
    .header-gold { color: #b8860b; font-weight: bold; font-size: 18px; margin-bottom: 8px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE SMARTER DATA ENGINE ---
@st.cache_data
def load_data():
    files = {"workbook": 'EM_Macro_Data_India_SG_UK.xlsx', "inr": 'DEXINUS.xlsx', "gbp": 'DEXUSUK.xlsx', "sgd": 'AEXSIUS.xlsx'}
    
    # Check physical existence
    for label, path in files.items():
        if not os.path.exists(path):
            st.error(f"Missing File: {path}")
            return None

    try:
        # 1. Load Main Macro Data
        df_m = pd.read_excel(files["workbook"], sheet_name='Macro data')
        df_m['Date'] = pd.to_datetime(df_m['Date'], errors='coerce')
        
        # 2. Load GDP
        df_g = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
        df_g.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        df_g['Year'] = pd.to_numeric(df_g['Year'], errors='coerce')

        # 3. Robust FX Loader (Searches for columns instead of assuming index)
        def robust_load_fx(path, out_name):
            try:
                xls = pd.ExcelFile(path)
                # Use the first sheet that isn't a 'README'
                sheet = [s for s in xls.sheet_names if 'README' not in s.upper()][0]
                f = pd.read_excel(path, sheet_name=sheet)
                
                # Logic: Find a column that looks like a date
                date_col = None
                val_col = None
                
                for col in f.columns:
                    # Check if column name has 'date' or if first value is a timestamp
                    if 'date' in str(col).lower():
                        date_col = col
                    elif pd.api.types.is_datetime64_any_dtype(f[col]):
                        date_col = col
                
                # If no date col found by name, assume first column
                if date_col is None: date_col = f.columns[0]
                
                # The value column is usually the one that ISN'T the date
                remaining_cols = [c for c in f.columns if c != date_col]
                val_col = remaining_cols[0] if remaining_cols else f.columns[0]

                f[date_col] = pd.to_datetime(f[date_col], errors='coerce')
                f[val_col] = pd.to_numeric(f[val_col], errors='coerce')
                
                return f.dropna(subset=[date_col]).resample('MS', on=date_col).mean().reset_index().rename(columns={date_col:'Date', val_col:out_name})
            except Exception as e:
                st.warning(f"Note: Issues processing {path}: {e}")
                return pd.DataFrame(columns=['Date', out_name])

        fx_i = robust_load_fx(files["inr"], 'FX_India')
        fx_g = robust_load_fx(files["gbp"], 'FX_UK')
        fx_s = robust_load_fx(files["sgd"], 'FX_Singapore')
        
        # 4. Merge
        df_m['Year'] = df_m['Date'].dt.year
        df = df_m.merge(df_g, on='Year', how='left')
        
        # Merge FX only if they aren't empty
        for fx_df in [fx_i, fx_g, fx_s]:
            if not fx_df.empty:
                df = df.merge(fx_df, on='Date', how='left')
        
        return df.sort_values('Date').ffill().bfill()
    
    except Exception as e:
        st.error(f"Critical Merger Error: {e}")
        return None

# --- 3. SIDEBAR & LOGIC ---
with st.sidebar:
    st.markdown("<h2 style='color:white;'>TERMINAL CONTROL</h2>", unsafe_allow_html=True)
    market = st.selectbox("Market Focus", ["India", "UK", "Singapore"])
    horizon = st.radio("Lookback Window", ["Historical", "10 Years", "5 Years"], index=1)
    st.divider()
    scenario = st.selectbox("Global Event", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    severity = st.slider("Scenario Severity (%)", 0, 100, 50)
    st.divider()
    view_real = st.toggle("View 'Real' Interest Rates")
    rate_intervention = st.slider("Manual Rate Intervention (bps)", -200, 200, 0, step=25)
    lag = st.selectbox("Transmission Lag (Months)", [0, 3, 6, 12])
    st.divider()
    sentiment = st.select_slider("Global Sentiment", options=["Risk-Off", "Neutral", "Risk-On"], value="Neutral")
    show_taylor = st.toggle("Overlay Taylor Rule")

# --- 4. EXECUTION ---
df_raw = load_data()

if df_raw is not None:
    m_map = {
        "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR", "t": 4.0, "n": 4.5},
        "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP", "t": 2.0, "n": 2.5},
        "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD", "t": 2.0, "n": 2.5}
    }
    m = m_map[market]
    df = df_raw.copy()

    # Time Filter
    if horizon == "10 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
    elif horizon == "5 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

    # Simulations
    mult = severity / 100
    df[m['p']] = df[m['p']] + (rate_intervention / 100)
    
    if scenario == "Stagflation 🌪️":
        df[m['cpi']] += (5.0 * mult); df[m['gdp']] -= (3.0 * mult)
    elif scenario == "Depression 📉":
        df[m['gdp']] -= (8.0 * mult); df[m['cpi']] -= (2.0 * mult)
    elif scenario == "High Growth 🚀":
        df[m['gdp']] += (4.0 * mult); df[m['cpi']] -= (1.0 * mult)

    if sentiment == "Risk-Off" and m['fx'] in df.columns: df[m['fx']] *= 1.05
    elif sentiment == "Risk-On" and m['fx'] in df.columns: df[m['fx']] *= 0.95

    # Taylor Rule
    avg_g = df[m['gdp']].mean() if not df[m['gdp']].empty else 0
    df['Taylor'] = m['n'] + 0.5*(df[m['cpi']] - m['t']) + 0.5*(df[m['gdp']] - avg_g)

    if view_real: df[m['p']] = df[m['p']] - df[m['cpi']]
    if lag > 0:
        df[m['cpi']] = df[m['cpi']].shift(lag)
        df[m['gdp']] = df[m['gdp']].shift(lag)

    # --- 5. UI DASHBOARD ---
    st.markdown(f"<div class='main-title'>{market.upper()} // STRATEGIC MACRO TERMINAL</div>", unsafe_allow_html=True)
    
    def get_v(s): 
        valid = s.dropna()
        return valid.iloc[-1] if not valid.empty else 0
        
    lp, lc, lg, lt = get_v(df[m['p']]), get_v(df[m['cpi']]), get_v(df[m['gdp']]), get_v(df['Taylor'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Policy Rate", f"{lp:.2f}%")
    c2.metric("Inflation", f"{lc:.2f}%")
    c3.metric("GDP Growth", f"{lg:.1f}%")
    if m['fx'] in df.columns:
        c4.metric(f"FX Spot ({m['sym']})", f"{get_v(df[m['fx']]):.2f}")

    # Charts
    st.markdown("<div class='header-gold'>I. Monetary Corridor & Policy Stance</div>", unsafe_allow_html=True)
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Interest Rate", line=dict(color='#1f77b4', width=3)), secondary_y=False)
    if show_taylor:
        fig1.add_trace(go.Scatter(x=df['Date'], y=df['Taylor'], name="Taylor Rule", line=dict(color='orange', width=2, dash='dash')), secondary_y=False)
    if m['fx'] in df.columns:
        fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="Exchange Rate", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
    fig1.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=400)
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("<div class='header-gold'>II. Economic Health: Growth vs Inflation</div>", unsafe_allow_html=True)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(x=df['Date'], y=df[m['gdp']], name="GDP Growth (%)", marker_color='#2ecc71', opacity=0.7), secondary_y=False)
    fig2.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI Inflation (%)", line=dict(color='#e74c3c', width=3)), secondary_y=True)
    fig2.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=400)
    st.plotly_chart(fig2, use_container_width=True)

    # --- 6. NOTES ---
    st.divider()
    colA, colB = st.columns(2)
    with colA:
        st.markdown("<div class='header-gold'>Analyst Verdict</div>", unsafe_allow_html=True)
        v_msg = "Policy is <b>restrictive</b>." if lp > lt else "Policy is <b>accommodative</b>."
        st.markdown(f"<div class='note-box'>{v_msg}<br>Sentiment: {sentiment}</div>", unsafe_allow_html=True)
        if st.button("📊 Correlation Matrix"):
            st.table(df[[m['p'], m['cpi'], m['gdp']]].corr())
    with colB:
        st.markdown("<div class='header-gold'>Methodology</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='note-box'>Real-time synthesis of {market} macro indicators.</div>", unsafe_allow_html=True)
