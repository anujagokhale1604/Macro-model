import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. PREMIUM STYLING & ICON ENGINE ---
st.set_page_config(page_title="Macro Intel Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">

    /* Global Typography */
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #F8F9FA; color: #111827; }

    /* SIDEBAR FONT FIX - FORCING WHITE ON ALL LABELS & TOGGLES */
    section[data-testid="stSidebar"] .stWidgetLabel p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] { 
        color: #FFFFFF !important; 
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* BOX STYLING */
    .analyst-card { 
        padding: 20px; border-radius: 8px; border: 1px solid #E5E7EB; 
        background-color: #FFFFFF; margin-bottom: 20px; 
        border-left: 5px solid #002366;
    }
    .layman-card {
        padding: 20px; border-radius: 8px; background-color: #002366; 
        color: #FFFFFF; margin-bottom: 25px; border-left: 10px solid #B8860B;
    }
    .method-card { 
        padding: 20px; border-radius: 8px; background-color: #F3F4F6; 
        color: #374151; font-size: 0.9rem; border-left: 5px solid #6B7280;
    }
    .main-title { 
        font-size: 32px; font-weight: 800; color: #002366; 
        border-bottom: 3px solid #B8860B; padding-bottom: 10px; margin-bottom: 30px; 
    }
    .section-header { 
        color: #B8860B; font-weight: 700; font-size: 1.1rem; 
        margin-top: 30px; margin-bottom: 15px; text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (XLSX) ---
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
                xls = pd.ExcelFile(path); sheet = [s for s in xls.sheet_names if 'README' not in s.upper()][0]
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

# --- 3. SIDEBAR (FULL TOGGLES RESTORED) ---
with st.sidebar:
    st.markdown("<h2 style='color:white;'><i class='fa-solid fa-sliders'></i> CONTROL PANEL</h2>", unsafe_allow_html=True)
    market = st.selectbox("SELECT MARKET", ["India", "UK", "Singapore"])
    horizon = st.radio("TIME HORIZON", ["Historical", "10 Years", "5 Years"], index=1)
    st.divider()
    scenario = st.selectbox("SCENARIO ENGINE", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    severity = st.slider("SEVERITY (%)", 0, 100, 50)
    st.divider()
    view_real = st.toggle("VIEW REAL RATES")
    show_taylor = st.toggle("SHOW TAYLOR RULE")
    rate_intervention = st.slider("ADJUST RATES (BPS)", -200, 200, 0, step=25)
    lag = st.selectbox("TRANSMISSION LAG (MO)", [0, 3, 6, 12])
    st.divider()
    sentiment = st.select_slider("MARKET SENTIMENT", options=["Risk-Off", "Neutral", "Risk-On"], value="Neutral")

# --- 4. ANALYTICS ---
df_raw = load_data()
if df_raw is not None:
    m_map = {
        "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR", "t": 4.0, "n": 4.5},
        "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP", "t": 2.0, "n": 2.5},
        "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD", "t": 2.0, "n": 2.5}
    }
    m = m_map[market]; df = df_raw.copy()

    if horizon == "10 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
    elif horizon == "5 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

    mult = severity / 100
    df[m['p']] += (rate_intervention / 100)
    if scenario == "Stagflation 🌪️": df[m['cpi']] += (5.0 * mult); df[m['gdp']] -= (3.0 * mult)
    elif scenario == "Depression 📉": df[m['gdp']] -= (8.0 * mult); df[m['cpi']] -= (2.0 * mult)
    elif scenario == "High Growth 🚀": df[m['gdp']] += (4.0 * mult); df[m['cpi']] -= (1.0 * mult)

    if sentiment == "Risk-Off" and m['fx'] in df.columns: df[m['fx']] *= 1.05
    elif sentiment == "Risk-On" and m['fx'] in df.columns: df[m['fx']] *= 0.95

    avg_g = df[m['gdp']].mean()
    df['Taylor'] = m['n'] + 0.5*(df[m['cpi']] - m['t']) + 0.5*(df[m['gdp']] - avg_g)
    if view_real: df[m['p']] -= df[m['cpi']]
    if lag > 0: df[m['cpi']] = df[m['cpi']].shift(lag); df[m['gdp']] = df[m['gdp']].shift(lag)

    # --- 5. DASHBOARD UI ---
    st.markdown(f"<div class='main-title'>{market.upper()} STRATEGIC TERMINAL</div>", unsafe_allow_html=True)
    
    def get_v(s): return s.dropna().iloc[-1] if not s.dropna().empty else 0
    lp, lc, lg, lt = get_v(df[m['p']]), get_v(df[m['cpi']]), get_v(df[m['gdp']]), get_v(df['Taylor'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("POLICY RATE", f"{lp:.2f}%")
    c2.metric("CPI INFLATION", f"{lc:.2f}%")
    c3.metric("GDP GROWTH", f"{lg:.1f}%")
    c4.metric(f"FX ({m['sym']})", f"{get_v(df[m['fx']]):.2f}")

    # I. GRAPHS
    st.markdown("<div class='section-header'><i class='fa-solid fa-chart-line'></i> I. Monetary Transmission & FX</div>", unsafe_allow_html=True)
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Policy Rate", line=dict(color='#002366', width=3)), secondary_y=False)
    if show_taylor: fig1.add_trace(go.Scatter(x=df['Date'], y=df['Taylor'], name="Taylor Rule", line=dict(color='#B8860B', dash='dash')), secondary_y=False)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="Exchange Rate", line=dict(color='#10B981')), secondary_y=True)
    fig1.update_layout(height=350, template="plotly_white", margin=dict(t=20, b=20))
    st.plotly_chart(fig1, use_container_width=True)

    # II. ANALYST NOTE (DYNAMIC)
    rate_trend = "upward" if lp > df[m['p']].iloc[0] else "downward"
    st.markdown(f"""<div class='analyst-card'>
        <b>Analyst Note:</b> The <b>{market}</b> monetary stance is currently <b>{'Restrictive' if lp > lt else 'Accommodative'}</b>. 
        We observe an <b>{rate_trend}</b> trend in policy rates. Under the <b>{scenario}</b> scenario, 
        the gap between the Taylor Rule target and actual rates is <b>{abs(lp-lt):.2f}%</b>.
    </div>""", unsafe_allow_html=True)

    st.markdown("<div class='section-header'><i class='fa-solid fa-chart-bar'></i> II. Growth vs Inflation</div>", unsafe_allow_html=True)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(x=df['Date'], y=df[m['gdp']], name="GDP Growth", marker_color='#E5E7EB'), secondary_y=False)
    fig2.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI Inflation", line=dict(color='#DC2626', width=3)), secondary_y=True)
    fig2.update_layout(height=350, template="plotly_white", margin=dict(t=20, b=20))
    st.plotly_chart(fig2, use_container_width=True)

    # III. LAYMAN'S NOTE
    st.markdown("<div class='section-header'><i class='fa-solid fa-user-tie'></i> III. Layman's Recommendation</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='layman-card'>
        <h4>How this affects your wallet:</h4>
        • <b>Loans/Mortgages:</b> {'Borrowing costs are high. Avoid new large debt if possible.' if lp > 4.5 else 'Interest on loans is relatively low. Good time for financing.'}<br>
        • <b>Savings:</b> {'This is a great time to put money into fixed deposits or savings accounts.' if lp > 4.5 else 'Savings yields are low; consider diversified investments.'}<br>
        • <b>Daily Costs:</b> {'Prices are rising fast ({lc:.1f}%). Your monthly budget will feel squeezed.' if lc > 3.0 else 'Inflation is stable. Your purchasing power is safe.'}
    </div>""", unsafe_allow_html=True)

    # IV. STATS & METHODOLOGY
    st.divider()
    colA, colB = st.columns([1, 1.2])
    with colA:
        st.markdown("<div class='section-header'>IV. Correlation Matrix</div>", unsafe_allow_html=True)
        corr = df[[m['p'], m['cpi'], m['gdp'], m['fx']]].corr()
        st.dataframe(corr.style.background_gradient(cmap='RdYlGn').format("{:.2f}"), use_container_width=True)
    with colB:
        st.markdown("<div class='section-header'>V. Methodological Note</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='method-card'>
            <b>Economic Framework:</b> We apply the <b>Taylor Rule</b> to assess policy appropriateness. 
            By calculating the deviation between actual rates and the rule, we define market "stress." 
            FX data is resampled to monthly mean frequency to align with GDP growth vectors.
        </div>""", unsafe_allow_html=True)

else:
    st.error("Missing .xlsx files. Please verify repository contents.")
