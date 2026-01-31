import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. PREMIUM TYPOGRAPHY & ICON ENGINE ---
st.set_page_config(page_title="Macro Intel Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    
    /* GLOBAL FONT & COLOR RESET */
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #F5F5DC; color: #1a1a1a; }
    
    /* SIDEBAR - HIGH CONTRAST DARK MODE */
    section[data-testid="stSidebar"] { background-color: #111827 !important; border-right: 2px solid #d4af37; }
    section[data-testid="stSidebar"] .stWidgetLabel p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span { 
        color: #ffffff !important; 
        font-weight: 900 !important;
        font-size: 0.95rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* METRIC & NOTE STYLING */
    [data-testid="stMetricValue"] { font-weight: 900 !important; color: #002366 !important; }
    .note-box { 
        padding: 20px; border-radius: 10px; border: 1px solid #d4af37; 
        background-color: #ffffff; margin-bottom: 25px; color: #2c3e50; 
        line-height: 1.6; font-size: 0.95rem;
    }
    .recommendation-card {
        padding: 24px; border-radius: 10px; border-left: 8px solid #d4af37;
        background-color: #002366; color: white; margin-bottom: 25px;
    }
    
    .main-title { font-size: 32px; font-weight: 900; color: #002366; border-bottom: 3px solid #d4af37; padding-bottom: 8px; margin-bottom: 25px; }
    .header-gold { color: #b8860b; font-weight: 700; font-size: 16px; margin: 25px 0 10px 0; text-transform: uppercase; display: flex; align-items: center; gap: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (XLSX ONLY) ---
@st.cache_data
def load_data():
    files = {"workbook": 'EM_Macro_Data_India_SG_UK.xlsx', "inr": 'DEXINUS.xlsx', "gbp": 'DEXUSUK.xlsx', "sgd": 'AEXSIUS.xlsx'}
    if not all(os.path.exists(f) for f in files.values()): return None
    try:
        df_m = pd.read_excel(files["workbook"], sheet_name='Macro data')
        df_m['Date'] = pd.to_datetime(df_m['Date'], errors='coerce')
        df_g = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
        df_g.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']

        def clean_fx(path, out_name):
            try:
                xls = pd.ExcelFile(path)
                sheet = [s for s in xls.sheet_names if 'README' not in s.upper()][0]
                f = pd.read_excel(path, sheet_name=sheet)
                d_col = [c for c in f.columns if 'date' in str(c).lower()][0]
                v_col = [c for c in f.columns if c != d_col][0]
                f[d_col] = pd.to_datetime(f[d_col], errors='coerce')
                f[v_col] = pd.to_numeric(f[v_col].replace(0, pd.NA), errors='coerce')
                return f.dropna(subset=[d_col]).resample('MS', on=d_col).mean().ffill().bfill().reset_index().rename(columns={d_col:'Date', v_col:out_name})
            except: return pd.DataFrame(columns=['Date', out_name])

        fx_i, fx_g, fx_s = clean_fx(files["inr"], 'FX_India'), clean_fx(files["gbp"], 'FX_UK'), clean_fx(files["sgd"], 'FX_Singapore')
        df_m['Year'] = df_m['Date'].dt.year
        df = df_m.merge(df_g, on='Year', how='left').merge(fx_i, on='Date', how='left').merge(fx_g, on='Date', how='left').merge(fx_s, on='Date', how='left')
        return df.sort_values('Date').ffill().bfill()
    except: return None

# --- 3. SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("<div style='text-align:center;'><i class='fa-solid fa-gauge-high fa-2x' style='color:#d4af37;'></i></div>", unsafe_allow_html=True)
    st.markdown("<h2 style='color:white; text-align:center;'>TERMINAL OPS</h2>", unsafe_allow_html=True)
    market = st.selectbox("SELECT MARKET", ["India", "UK", "Singapore"])
    horizon = st.radio("TIME HORIZON", ["Historical", "10 Years", "5 Years"], index=1)
    st.divider()
    scenario = st.selectbox("SCENARIO ENGINE", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    severity = st.slider("INTENSITY (%)", 0, 100, 50)
    st.divider()
    view_real = st.toggle("REAL RATES VIEW")
    rate_intervention = st.slider("MANUAL ADJ (BPS)", -200, 200, 0, step=25)
    lag = st.selectbox("TRANSMISSION LAG", [0, 3, 6, 12])
    show_taylor = st.toggle("SHOW TAYLOR RULE")

# --- 4. ANALYTICS ENGINE ---
df_raw = load_data()
if df_raw is not None:
    m_map = {
        "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR", "t": 4.0, "n": 4.5, "flag": "🇮🇳"},
        "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP", "t": 2.0, "n": 2.5, "flag": "🇬🇧"},
        "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD", "t": 2.0, "n": 2.5, "flag": "🇸🇬"}
    }
    m = m_map[market]
    df = df_raw.copy()

    # Time Filter
    if horizon == "10 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
    elif horizon == "5 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

    # Simulations
    mult = severity / 100
    df[m['p']] += (rate_intervention / 100)
    if scenario == "Stagflation 🌪️": df[m['cpi']] += (5.0 * mult); df[m['gdp']] -= (3.0 * mult)
    elif scenario == "Depression 📉": df[m['gdp']] -= (8.0 * mult); df[m['cpi']] -= (2.0 * mult)
    elif scenario == "High Growth 🚀": df[m['gdp']] += (4.0 * mult); df[m['cpi']] -= (1.0 * mult)

    avg_g = df[m['gdp']].mean()
    df['Taylor'] = m['n'] + 0.5*(df[m['cpi']] - m['t']) + 0.5*(df[m['gdp']] - avg_g)
    if view_real: df[m['p']] -= df[m['cpi']]
    if lag > 0: df[m['cpi']] = df[m['cpi']].shift(lag); df[m['gdp']] = df[m['gdp']].shift(lag)

    # --- 5. UI DISPLAY ---
    st.markdown(f"<div class='main-title'>{m['flag']} {market.upper()} STRATEGIC TERMINAL</div>", unsafe_allow_html=True)
    
    def get_v(s): return s.dropna().iloc[-1] if not s.dropna().empty else 0
    lp, lc, lg, lt = get_v(df[m['p']]), get_v(df[m['cpi']]), get_v(df[m['gdp']]), get_v(df['Taylor'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("POLICY RATE", f"{lp:.2f}%")
    c2.metric("CPI INFLATION", f"{lc:.2f}%")
    c3.metric("GDP GROWTH", f"{lg:.1f}%")
    c4.metric(f"{m['sym']} FX", f"{get_v(df[m['fx']]):.2f}")

    # --- GRAPHS (FIXED HEIGHT) ---
    st.markdown("<div class='header-gold'><i class='fa-solid fa-chart-line'></i> I. Monetary Transmission</div>", unsafe_allow_html=True)
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Nominal Rate", line=dict(color='#1f77b4', width=3)), secondary_y=False)
    if show_taylor: fig1.add_trace(go.Scatter(x=df['Date'], y=df['Taylor'], name="Taylor Rule", line=dict(color='orange', dash='dash')), secondary_y=False)
    if m['fx'] in df.columns: fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="FX Spot", line=dict(color='#d4af37')), secondary_y=True)
    fig1.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=10), template="plotly_white", paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("<div class='header-gold'><i class='fa-solid fa-layer-group'></i> II. Real Economy Activity</div>", unsafe_allow_html=True)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(x=df['Date'], y=df[m['gdp']], name="GDP Growth", marker_color='#2ecc71', opacity=0.7), secondary_y=False)
    fig2.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="Inflation", line=dict(color='#e74c3c', width=3)), secondary_y=True)
    fig2.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=10), template="plotly_white", paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig2, use_container_width=True)

    # --- 6. CORRELATION & NOTES ---
    st.divider()
    st.markdown("<div class='header-gold'><i class='fa-solid fa-table-list'></i> III. Matrix Analysis</div>", unsafe_allow_html=True)
    corr_matrix = df[[m['p'], m['cpi'], m['gdp'], m['fx']]].corr()
    cm, cn = st.columns([1, 1])
    with cm: st.dataframe(corr_matrix.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}"), use_container_width=True)
    with cn:
        r_f = corr_matrix.loc[m['p'], m['fx']]
        st.markdown(f"""<div class='note-box'>
            <b>Matrix Interpreter:</b> The <b>{r_f:.2f}</b> correlation between Policy Rates and Currency Spot indicates a 
            <b>{'positive' if r_f > 0 else 'negative'}</b> pressure. In {market}, as rates rise, the currency 
            tends to <b>{'strengthen' if r_f > 0 else 'weaken'}</b> based on historical data.
        </div>""", unsafe_allow_html=True)

    # --- 7. LAYMAN RECOMMENDATION ---
    st.divider()
    st.markdown("<div class='header-gold'><i class='fa-solid fa-lightbulb'></i> IV. Personal Finance Impact</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='recommendation-card'>
        <h3>What this means for you:</h3>
        <p>• <b>Savings:</b> {'Rates are high! Keep money in FDs/Savings to earn more interest.' if lp > 4 else 'Rates are low. Your bank savings won\'t grow much; look at other investments.'}<br>
        • <b>Loans:</b> {'Borrowing is EXPENSIVE. Try to pay off debt early.' if lp > 4 else 'Loans are CHEAP. Good time for home or car financing.'}<br>
        • <b>Purchasing Power:</b> {'Inflation is HIGH ({lc:.1f}%). Prices are rising fast—spend carefully.' if lc > 3 else 'Prices are STABLE. Your monthly budget is safe.'}</p>
        <p><i><b>Strategic Verdict:</b> The stance is <b>{'HAWKISH' if lp > lt else 'DOVISH'}</b> relative to the Taylor Rule.</i></p>
    </div>""", unsafe_allow_html=True)

else: st.error("Files Missing. Ensure all .xlsx files are in the repository.")
