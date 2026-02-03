import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. CHIC RESEARCH UI ENGINE ---
st.set_page_config(page_title="Macro Intel Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css');

    /* GLOBAL FONT FORCE */
    * {
        font-family: 'Times New Roman', Times, serif !important;
    }

    /* GLOBAL THEME - CHIC BEIGE */
    .stApp { background-color: #F2EFE9; color: #2C2C2C; }

    /* SIDEBAR - HIGH CONTRAST */
    section[data-testid="stSidebar"] {
        background-color: #E5E1D8 !important; 
        border-right: 1px solid #A39B8F;
    }

    /* FORCING TOGGLE TITLES TO VISIBLE BLACK */
    section[data-testid="stSidebar"] .stWidgetLabel p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p {
        color: #1A1A1A !important; 
        font-weight: bold !important;
        font-size: 1.05rem !important;
        text-transform: uppercase;
    }

    /* HARMONIZED CARDS */
    .analyst-card { 
        padding: 20px; border: 1px solid #A39B8F; 
        background-color: #FFFFFF; margin-bottom: 20px; 
        border-left: 5px solid #002366;
    }
    .layman-card {
        padding: 20px; background-color: #FDFCFB; 
        color: #1A1A1A; margin-bottom: 25px; border: 1px solid #A39B8F;
        border-left: 10px solid #002366;
    }
    .method-card { 
        padding: 20px; background-color: #FAF9F6; 
        color: #1A1A1A; font-size: 0.95rem; border: 1px solid #A39B8F;
    }
    
    /* TITLES & HEADERS */
    .main-title { 
        font-size: 36px; font-weight: bold; color: #002366; 
        border-bottom: 3px solid #C5A059; padding-bottom: 10px; margin-bottom: 30px; 
    }
    .section-header { 
        color: #7A6D5D; font-weight: bold; font-size: 1.3rem; 
        margin-top: 30px; margin-bottom: 15px; text-transform: uppercase;
    }
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

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:#000000;'><i class='fa-solid fa-bars-staggered'></i> NAVIGATE</h2>", unsafe_allow_html=True)
    market = st.selectbox("1. SELECT MARKET", ["India", "UK", "Singapore"])
    horizon = st.radio("2. TIME HORIZON", ["Historical", "10 Years", "5 Years"], index=1)
    st.divider()
    scenario = st.selectbox("3. SCENARIO ENGINE", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    severity = st.slider("4. SEVERITY (%)", 0, 100, 50)
    st.divider()
    view_real = st.toggle("ACTIVATE REAL RATES")
    show_taylor = st.toggle("OVERLAY TAYLOR RULE")
    rate_intervention = st.slider("5. MANUAL ADJ (BPS)", -200, 200, 0, step=25)
    lag = st.selectbox("6. TRANSMISSION LAG", [0, 3, 6, 12])
    st.divider()
    sentiment = st.select_slider("7. MARKET SENTIMENT", options=["Risk-Off", "Neutral", "Risk-On"], value="Neutral")

# --- 4. ANALYTICS ENGINE ---
df_raw = load_data()
if df_raw is not None:
    m_map = {
        "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR", "t": 4.0, "n": 4.5},
        "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP", "t": 2.0, "n": 2.5},
        "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD", "t": 2.0, "n": 2.5}
    }
    m = m_map[market]; df = df_raw.copy()

    # Apply Scenario logic
    mult = severity / 100
    df[m['p']] += (rate_intervention / 100)
    
    scenario_desc = ""
    if scenario == "Stagflation 🌪️":
        df[m['cpi']] += (5.0 * mult)
        df[m['gdp']] -= (3.0 * mult)
        scenario_desc = "driven by high inflation coupled with stagnant growth."
    elif scenario == "Depression 📉":
        df[m['gdp']] -= (8.0 * mult)
        df[m['cpi']] -= (2.0 * mult)
        scenario_desc = "reflecting a severe contraction in aggregate demand."
    elif scenario == "High Growth 🚀":
        df[m['gdp']] += (4.0 * mult)
        df[m['cpi']] -= (1.0 * mult)
        scenario_desc = "indicating strong productivity and expansion."
    else:
        scenario_desc = "following historical baseline patterns."

    avg_g = df[m['gdp']].mean()
    df['Taylor'] = m['n'] + 0.5*(df[m['cpi']] - m['t']) + 0.5*(df[m['gdp']] - avg_g)
    
    if view_real: df[m['p']] -= df[m['cpi']]
    if lag > 0: df[m['cpi']] = df[m['cpi']].shift(lag); df[m['gdp']] = df[m['gdp']].shift(lag)

    # --- 5. UI DISPLAY ---
    st.markdown(f"<div class='main-title'><i class='fa-solid fa-scale-balanced'></i> {market.upper()} MACRO TERMINAL</div>", unsafe_allow_html=True)
    
    def get_v(s): return s.dropna().iloc[-1] if not s.dropna().empty else 0
    lp, lc, lg, lt = get_v(df[m['p']]), get_v(df[m['cpi']]), get_v(df[m['gdp']]), get_v(df['Taylor'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("POLICY RATE", f"{lp:.2f}%")
    c2.metric("CPI INFLATION", f"{lc:.2f}%")
    c3.metric("GDP GROWTH", f"{lg:.1f}%")
    c4.metric(f"FX ({m['sym']})", f"{get_v(df[m['fx']]):.2f}")

    # I. MONETARY TRANSMISSION
    st.markdown("<div class='section-header'><i class='fa-solid fa-chart-line'></i> I. Monetary Transmission Analysis</div>", unsafe_allow_html=True)
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Policy Rate", line=dict(color='#002366', width=3)), secondary_y=False)
    if show_taylor: fig1.add_trace(go.Scatter(x=df['Date'], y=df['Taylor'], name="Taylor Rule", line=dict(color='#8B4513', dash='dash')), secondary_y=False)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="Exchange Rate", line=dict(color='#2E8B57')), secondary_y=True)
    fig1.update_layout(height=350, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Times New Roman"))
    st.plotly_chart(fig1, use_container_width=True)

    # DYNAMIC ANALYST NOTE
    st.markdown(f"""<div class='analyst-card'>
        <b>Analyst Interpretation:</b> The terminal is currently simulating a <b>{scenario}</b> environment, {scenario_desc} 
        Under these conditions, rates are <b>{'above' if lp > lt else 'below'}</b> the Taylor Rule estimate. 
        {'This suggests a hawkish attempt to curb inflation despite growth risks.' if scenario == 'Stagflation 🌪️' else 'This highlights the central bank’s struggle to stimulate a contracting economy.' if scenario == 'Depression 📉' else 'Policy appears balanced against historical benchmarks.'}
    </div>""", unsafe_allow_html=True)

    # II. GROWTH vs INFLATION
    st.markdown("<div class='section-header'><i class='fa-solid fa-chart-column'></i> II. Real Economy Activity</div>", unsafe_allow_html=True)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(x=df['Date'], y=df[m['gdp']], name="GDP Growth", marker_color='#BDB7AB'), secondary_y=False)
    fig2.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI Inflation", line=dict(color='#A52A2A', width=3)), secondary_y=True)
    fig2.update_layout(height=350, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Times New Roman"))
    st.plotly_chart(fig2, use_container_width=True)

    # III. LAYMAN'S NOTE
    st.markdown("<div class='section-header'><i class='fa-solid fa-user-check'></i> III. Layman's Recommendation</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='layman-card'>
        <b>Current Guidance:</b><br>
        • <b>Borrowing:</b> {'Rates are restrictive; high costs for new loans.' if lp > 4.5 else 'Accommodative rates favor borrowing for investment.'}<br>
        • <b>Savings:</b> {'Attractive returns for fixed-income and savings.' if lp > 4.5 else 'Low yields suggest seeking equity/growth assets.'}<br>
        • <b>Cost of Living:</b> {'Inflation ({lc:.1f}%) is high; prioritize essential spending.' if lc > 3.0 else 'Stable prices support consumer purchasing power.'}
    </div>""", unsafe_allow_html=True)

    # IV/V. STATS
    st.divider()
    colA, colB = st.columns([1, 1.2])
    with colA:
        st.markdown("<div class='section-header'><i class='fa-solid fa-table'></i> IV. Correlation Matrix</div>", unsafe_allow_html=True)
        corr = df[[m['p'], m['cpi'], m['gdp'], m['fx']]].corr()
        st.dataframe(corr.style.background_gradient(cmap='Greys').format("{:.2f}"), use_container_width=True)
    with colB:
        st.markdown("<div class='section-header'><i class='fa-solid fa-book'></i> V. Methodological Note</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='method-card'>
            <b>Concept: Taylor Rule Modelling</b><br>
            The neutral policy rate is derived from: $i = r^* + \pi + 0.5(\pi - \pi^*) + 0.5(y - y^*)$.<br>
            The <b>{scenario}</b> scenario modifies these inputs by adjusting inflation expectations and GDP growth forecasts, allowing you to visualize how policy should pivot during market shocks.
        </div>""", unsafe_allow_html=True)

else:
    st.error("Check .xlsx files.")
