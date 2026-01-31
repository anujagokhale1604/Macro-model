import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. PREMIUM STYLING ---
st.set_page_config(page_title="Macro Intel Pro", layout="wide")

st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">', unsafe_allow_html=True)

st.markdown("""
    <style>
    .stApp { background-color: #F5F5DC; color: #2c3e50; }
    
    /* SIDEBAR - HIGH CONTRAST */
    section[data-testid="stSidebar"] { background-color: #2c3e50 !important; border-right: 2px solid #d4af37; }
    section[data-testid="stSidebar"] .stWidgetLabel p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span { 
        color: #ffffff !important; 
        font-weight: 900 !important;
        font-size: 1.05rem !important;
    }
    
    /* CHART SPACING FIX */
    .chart-container { margin-bottom: 40px; padding: 10px; background: #ffffff; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    
    .note-box { 
        padding: 20px; border-radius: 10px; border: 1px solid #d4af37; 
        background-color: #ffffff; margin-bottom: 25px; color: #2c3e50; 
        line-height: 1.6;
    }
    
    .main-title { font-size: 38px; font-weight: 900; color: #002366; border-bottom: 4px solid #d4af37; padding-bottom: 10px; margin-bottom: 25px; }
    .header-gold { color: #b8860b; font-weight: 900; font-size: 20px; margin-top: 20px; margin-bottom: 15px; text-transform: uppercase; display: flex; align-items: center; gap: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_data():
    files = {"workbook": 'EM_Macro_Data_India_SG_UK.xlsx', "inr": 'DEXINUS.xlsx', "gbp": 'DEXUSUK.xlsx', "sgd": 'AEXSIUS.xlsx'}
    if not all(os.path.exists(f) for f in files.values()): return None
    try:
        df_m = pd.read_excel(files["workbook"], sheet_name='Macro data')
        df_m['Date'] = pd.to_datetime(df_m['Date'], errors='coerce')
        df_g = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
        df_g.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']

        def robust_load_fx(path, out_name):
            try:
                xls = pd.ExcelFile(path)
                sheet = [s for s in xls.sheet_names if 'README' not in s.upper()][0]
                f = pd.read_excel(path, sheet_name=sheet)
                d_col = [c for c in f.columns if 'date' in str(c).lower() or pd.api.types.is_datetime64_any_dtype(f[c])][0]
                v_col = [c for c in f.columns if c != d_col][0]
                f[d_col] = pd.to_datetime(f[d_col], errors='coerce')
                f[v_col] = pd.to_numeric(f[v_col], errors='coerce')
                return f.dropna(subset=[d_col]).resample('MS', on=d_col).mean().reset_index().rename(columns={d_col:'Date', v_col:out_name})
            except: return pd.DataFrame(columns=['Date', out_name])

        fx_i, fx_g, fx_s = robust_load_fx(files["inr"], 'FX_India'), robust_load_fx(files["gbp"], 'FX_UK'), robust_load_fx(files["sgd"], 'FX_Singapore')
        df_m['Year'] = df_m['Date'].dt.year
        df = df_m.merge(df_g, on='Year', how='left').merge(fx_i, on='Date', how='left').merge(fx_g, on='Date', how='left').merge(fx_s, on='Date', how='left')
        return df.sort_values('Date').ffill().bfill()
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:white; font-weight:900;'>CONTROL PANEL</h2>", unsafe_allow_html=True)
    market = st.selectbox("SELECT MARKET", ["India", "UK", "Singapore"])
    horizon = st.radio("TIME HORIZON", ["Historical", "10 Years", "5 Years"], index=1)
    st.divider()
    scenario = st.selectbox("SCENARIO EVENT", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    severity = st.slider("INTENSITY (%)", 0, 100, 50)
    st.divider()
    view_real = st.toggle("USE REAL RATES")
    rate_intervention = st.slider("ADJUST RATES (BPS)", -200, 200, 0, step=25)
    lag = st.selectbox("TRANSMISSION LAG", [0, 3, 6, 12])
    st.divider()
    sentiment = st.select_slider("MARKET SENTIMENT", options=["Risk-Off", "Neutral", "Risk-On"], value="Neutral")
    show_taylor = st.toggle("TAYLOR RULE")

# --- 4. ENGINE ---
df_raw = load_data()
if df_raw is not None:
    m_map = {
        "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR", "t": 4.0, "n": 4.5, "flag": "🇮🇳"},
        "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP", "t": 2.0, "n": 2.5, "flag": "🇬🇧"},
        "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD", "t": 2.0, "n": 2.5, "flag": "🇸🇬"}
    }
    m = m_map[market]
    df = df_raw.copy()

    # Filters
    if horizon == "10 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
    elif horizon == "5 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

    # Sim logic
    mult = severity / 100
    df[m['p']] += (rate_intervention / 100)
    if scenario == "Stagflation 🌪️":
        df[m['cpi']] += (5.0 * mult); df[m['gdp']] -= (3.0 * mult)
    elif scenario == "Depression 📉":
        df[m['gdp']] -= (8.0 * mult); df[m['cpi']] -= (2.0 * mult)
    elif scenario == "High Growth 🚀":
        df[m['gdp']] += (4.0 * mult); df[m['cpi']] -= (1.0 * mult)

    if sentiment == "Risk-Off" and m['fx'] in df.columns: df[m['fx']] *= 1.05
    elif sentiment == "Risk-On" and m['fx'] in df.columns: df[m['fx']] *= 0.95

    avg_g = df[m['gdp']].mean() if not df[m['gdp']].empty else 0
    df['Taylor'] = m['n'] + 0.5*(df[m['cpi']] - m['t']) + 0.5*(df[m['gdp']] - avg_g)
    if view_real: df[m['p']] = df[m['p']] - df[m['cpi']]
    if lag > 0:
        df[m['cpi']] = df[m['cpi']].shift(lag); df[m['gdp']] = df[m['gdp']].shift(lag)

    # --- 5. UI DASHBOARD ---
    st.markdown(f"<div class='main-title'>{m['flag']} {market.upper()} STRATEGIC TERMINAL</div>", unsafe_allow_html=True)
    
    def get_v(s): return s.dropna().iloc[-1] if not s.dropna().empty else 0
    lp, lc, lg, lt = get_v(df[m['p']]), get_v(df[m['cpi']]), get_v(df[m['gdp']]), get_v(df['Taylor'])

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("RATE", f"{lp:.2f}%")
    with c2: st.metric("CPI", f"{lc:.2f}%")
    with c3: st.metric("GDP", f"{lg:.1f}%")
    with c4: st.metric(f"{m['sym']}", f"{get_v(df[m['fx']]):.2f}")

    # --- CHART 1: RATES ---
    st.markdown("<div class='header-gold'><i class='fa-solid fa-landmark'></i> I. Monetary Policy Corridor</div>", unsafe_allow_html=True)
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Policy Rate", line=dict(color='#1f77b4', width=3)), secondary_y=False)
    if show_taylor: fig1.add_trace(go.Scatter(x=df['Date'], y=df['Taylor'], name="Taylor Suggestion", line=dict(color='orange', dash='dash')), secondary_y=False)
    if m['fx'] in df.columns: fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="FX Level", line=dict(color='#d4af37', dash='dot')), secondary_y=True)
    fig1.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig1, use_container_width=True)

    # --- CHART 2: GDP & CPI (NEW ROW TO PREVENT CUTOFF) ---
    st.markdown("<div class='header-gold'><i class='fa-solid fa-chart-bar'></i> II. Real Economy: Growth vs Inflation</div>", unsafe_allow_html=True)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(x=df['Date'], y=df[m['gdp']], name="GDP Growth", marker_color='#2ecc71', opacity=0.6), secondary_y=False)
    fig2.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI Inflation", line=dict(color='#e74c3c', width=3)), secondary_y=True)
    fig2.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

    # --- 6. STATS & ANALYTICS ---
    st.divider()
    st.markdown("<div class='header-gold'><i class='fa-solid fa-square-poll-vertical'></i> III. Statistical Analysis</div>", unsafe_allow_html=True)
    
    corr_matrix = df[[m['p'], m['cpi'], m['gdp'], m['fx']]].corr()
    col_m, col_n = st.columns([1, 1])
    
    with col_m:
        st.dataframe(corr_matrix.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}"), use_container_width=True)
    with col_n:
        rate_fx_corr = corr_matrix.loc[m['p'], m['fx']]
        st.markdown(f"""<div class='note-box'>
            <b>Correlation Interpreter:</b><br>
            The current correlation between Policy Rates and Currency Spot is <b>{rate_fx_corr:.2f}</b>. 
            This indicates a <b>{'positive' if rate_fx_corr > 0 else 'negative'}</b> market sensitivity, 
            meaning currency value tends to {'strengthen' if rate_fx_corr > 0 else 'weaken'} as rates rise.
        </div>""", unsafe_allow_html=True)

    # --- 7. VERDICT ---
    st.markdown("<div class='header-gold'><i class='fa-solid fa-clipboard-check'></i> IV. Strategic Verdict</div>", unsafe_allow_html=True)
    v_status = "HAWKISH" if lp > lt else "DOVISH"
    st.markdown(f"""<div class='note-box'>
        <b>Analyst Conclusion:</b> The {market} Central Bank stance is <b>{v_status}</b>. 
        There is a <b>{abs(lp-lt):.2f}%</b> gap between the simulated rate and Taylor Rule equilibrium. 
        In the <b>{scenario}</b> scenario, the primary risk factor is the {lag}-month policy transmission lag.
    </div>""", unsafe_allow_html=True)

else:
    st.error("Terminal Offline: Check GitHub Excel files.")
