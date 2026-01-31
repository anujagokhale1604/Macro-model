import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. PREMIUM STYLING (FIXED FOR DARK SIDEBAR) ---
st.set_page_config(page_title="Macro Intel Pro", layout="wide")

# Force Font Awesome and Custom CSS
st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">', unsafe_allow_html=True)

st.markdown("""
    <style>
    .stApp { background-color: #F5F5DC; color: #2c3e50; }
    
    /* SIDEBAR TEXT VISIBILITY FIX */
    section[data-testid="stSidebar"] { background-color: #2c3e50 !important; border-right: 2px solid #d4af37; }
    section[data-testid="stSidebar"] .stWidgetLabel, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] h2 { 
        color: #ffffff !important; 
        font-weight: 700 !important;
        font-size: 1rem !important;
    }
    
    .metric-card {
        background-color: #ffffff; padding: 15px; border-radius: 10px;
        border-left: 5px solid #d4af37; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); text-align: center;
    }
    .main-title { font-size: 38px; font-weight: 900; color: #002366; border-bottom: 4px solid #d4af37; padding-bottom: 10px; margin-bottom: 25px; }
    .header-gold { color: #b8860b; font-weight: bold; font-size: 18px; margin-bottom: 8px; text-transform: uppercase; }
    .note-box { padding: 18px; border-radius: 8px; border: 1px solid #d4af37; background-color: #ffffff; margin-bottom: 20px; color: #2c3e50; }
    .corr-brief { font-size: 0.9em; color: #555; font-style: italic; margin-top: 10px; }
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
    st.markdown("<div style='text-align: center; color: white;'><i class='fa-solid fa-chart-line fa-3x' style='color: #d4af37;'></i><h2 style='color:white;'>MACRO INTEL</h2></div>", unsafe_allow_html=True)
    market = st.selectbox("Market Focus", ["India", "UK", "Singapore"])
    horizon = st.radio("Lookback Window", ["Historical", "10 Years", "5 Years"], index=1)
    st.divider()
    st.markdown("⚠️ SCENARIO ANALYSIS")
    scenario = st.selectbox("Global Event", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    severity = st.slider("Scenario Severity (%)", 0, 100, 50)
    st.divider()
    st.markdown("🛠️ ADVANCED LEVERS")
    view_real = st.toggle("View 'Real' Interest Rates")
    rate_intervention = st.slider("Manual Rate Intervention (bps)", -200, 200, 0, step=25)
    lag = st.selectbox("Transmission Lag (Months)", [0, 3, 6, 12])
    st.divider()
    st.markdown("📈 MARKET SENSITIVITY")
    sentiment = st.select_slider("Global Sentiment", options=["Risk-Off", "Neutral", "Risk-On"], value="Neutral")
    show_taylor = st.toggle("Overlay Taylor Rule")

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

    # Apply Filtering & Scenarios
    if horizon == "10 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
    elif horizon == "5 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

    mult = severity / 100
    df[m['p']] += (rate_intervention / 100)
    if scenario == "Stagflation 🌪️":
        df[m['cpi']] += (5.0 * mult); df[m['gdp']] -= (3.0 * mult)
    elif scenario == "Depression 📉":
        df[m['gdp']] -= (8.0 * mult); df[m['cpi']] -= (2.0 * mult)
    elif scenario == "High Growth 🚀":
        df[m['gdp']] += (4.0 * mult); df[m['cpi']] -= (1.0 * mult)

    if m['fx'] in df.columns:
        if sentiment == "Risk-Off": df[m['fx']] *= 1.05
        elif sentiment == "Risk-On": df[m['fx']] *= 0.95

    avg_g = df[m['gdp']].mean() if not df[m['gdp']].empty else 0
    df['Taylor'] = m['n'] + 0.5*(df[m['cpi']] - m['t']) + 0.5*(df[m['gdp']] - avg_g)
    if view_real: df[m['p']] = df[m['p']] - df[m['cpi']]
    if lag > 0:
        df[m['cpi']] = df[m['cpi']].shift(lag)
        df[m['gdp']] = df[m['gdp']].shift(lag)

    # --- 5. UI DASHBOARD ---
    st.markdown(f"<div class='main-title'>{m['flag']} {market.upper()} STRATEGIC TERMINAL</div>", unsafe_allow_html=True)
    
    def get_v(s): return s.dropna().iloc[-1] if not s.dropna().empty else 0
    lp, lc, lg, lt = get_v(df[m['p']]), get_v(df[m['cpi']]), get_v(df[m['gdp']]), get_v(df['Taylor'])

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f"<div class='metric-card'><i class='fa-solid fa-building-columns' style='color:#002366'></i><br><b>Rate</b><br><h3>{lp:.2f}%</h3></div>", unsafe_allow_html=True)
    with c2: st.markdown(f"<div class='metric-card'><i class='fa-solid fa-fire-flame-curved' style='color:#002366'></i><br><b>CPI</b><br><h3>{lc:.2f}%</h3></div>", unsafe_allow_html=True)
    with c3: st.markdown(f"<div class='metric-card'><i class='fa-solid fa-seedling' style='color:#002366'></i><br><b>GDP</b><br><h3>{lg:.1f}%</h3></div>", unsafe_allow_html=True)
    with c4: st.markdown(f"<div class='metric-card'><i class='fa-solid fa-coins' style='color:#002366'></i><br><b>{m['sym']}</b><br><h3>{get_v(df[m['fx']]):.2f}</h3></div>", unsafe_allow_html=True)

    # Charts
    st.divider()
    st.markdown("<div class='header-gold'><i class='fa-solid fa-chart-area'></i> I. Monetary Corridor</div>", unsafe_allow_html=True)
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Interest Rate", line=dict(color='#1f77b4', width=3)), secondary_y=False)
    if show_taylor: fig1.add_trace(go.Scatter(x=df['Date'], y=df['Taylor'], name="Taylor Rule", line=dict(color='orange', dash='dash')), secondary_y=False)
    if m['fx'] in df.columns: fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="Exchange Rate", line=dict(color='#d4af37', dash='dot')), secondary_y=True)
    fig1.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=350)
    st.plotly_chart(fig1, use_container_width=True)

    # --- 6. STATS & CORRELATION ---
    st.divider()
    colA, colB = st.columns([1, 1.5])
    
    with colA:
        st.markdown("<div class='header-gold'><i class='fa-solid fa-table-list'></i> Correlation Matrix</div>", unsafe_allow_html=True)
        # Selecting variables that exist in df
        corr_data = df[[m['p'], m['cpi'], m['gdp']]]
        if m['fx'] in df.columns: corr_data = df[[m['p'], m['cpi'], m['gdp'], m['fx']]]
        
        st.dataframe(corr_data.corr().style.background_gradient(cmap='RdYlGn'))
        st.markdown("""<div class='corr-brief'>
            <b>Analyst Note:</b> Correlation measures how variables move together. 
            A value near 1.0 indicates a strong positive relationship (e.g., Rates rising with Inflation).
        </div>""", unsafe_allow_html=True)

    with colB:
        st.markdown("<div class='header-gold'><i class='fa-solid fa-gavel'></i> Strategic Verdict</div>", unsafe_allow_html=True)
        v_msg = "The Central Bank is <b>Hawkish</b> (Restrictive) relative to output gaps." if lp > lt else "The Central Bank is <b>Dovish</b> (Accommodative) relative to inflation targets."
        st.markdown(f"<div class='note-box'><b>Current Logic:</b> {scenario}.<br><br><b>Insight:</b> {v_msg}</div>", unsafe_allow_html=True)

else:
    st.error("Data Load Failed. Check Excel file paths.")
