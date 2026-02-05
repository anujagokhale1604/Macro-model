import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. CHIC RESEARCH UI ENGINE ---
st.set_page_config(page_title="Macro Intel Pro", layout="wide")

st.markdown('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">', unsafe_allow_html=True)

st.markdown("""
    <style>
    * { font-family: 'Times New Roman', Times, serif !important; }
    .stApp { background-color: #F2EFE9; color: #2C2C2C; }

    /* REDUCING VERTICAL WASTE */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .stPlotlyChart { margin-top: -25px; } 

    section[data-testid="stSidebar"] {
        background-color: #E5E1D8 !important; 
        border-right: 1px solid #A39B8F;
    }

    /* CARDS */
    .analyst-card { 
        padding: 15px; border: 1px solid #A39B8F; 
        background-color: #FFFFFF; margin-top: -10px; margin-bottom: 20px; 
        border-left: 5px solid #002366; font-size: 0.95rem;
    }
    .for-you-card {
        padding: 20px; background-color: #FDFCFB; 
        color: #1A1A1A; margin-bottom: 25px; border: 1px solid #A39B8F;
        border-left: 10px solid #002366;
    }
    .method-card { 
        padding: 20px; background-color: #FAF9F6; 
        color: #1A1A1A; font-size: 0.92rem; border: 1px solid #A39B8F; line-height: 1.5;
    }
    
    .main-title { 
        font-size: 32px; font-weight: bold; color: #002366; 
        border-bottom: 3px solid #C5A059; padding-bottom: 5px; margin-bottom: 20px; 
    }
    .section-header { 
        color: #7A6D5D; font-weight: bold; font-size: 1.2rem; 
        margin-top: 20px; margin-bottom: 5px; text-transform: uppercase;
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
    st.markdown("<h2 style='color:#000000;'><i class='fas fa-bars-staggered'></i> NAVIGATE</h2>", unsafe_allow_html=True)
    if st.button("RESET PARAMETERS", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
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
# --- Add to Sidebar Section ---
st.sidebar.header("🛠️ Strategy & Stress-Testing")

# Scenario Sliders
energy_shock = st.sidebar.slider("Energy Price Surge (%)", 0, 100, 0)

# Policy Parameters
target_inf = st.sidebar.number_input("Target Inflation (%)", value=2.0)
stance = st.sidebar.select_slider(
    "Central Bank Stance",
    options=["Dovish", "Neutral", "Hawkish"],
    value="Neutral"
)

# --- 4. ANALYTICS ENGINE ---
df_raw = load_data()
if df_raw is not None:
    m_map = {
        "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR", "t": 4.0, "n": 4.5},
        "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP", "t": 2.0, "n": 2.5},
        "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD", "t": 2.0, "n": 2.5}
    }
    m = m_map[market]; df = df_raw.copy()

    mult = severity / 100
    df[m['p']] += (rate_intervention / 100)
    
    if scenario == "Stagflation 🌪️":
        df[m['cpi']] += (5.0 * mult); df[m['gdp']] -= (3.0 * mult)
    elif scenario == "Depression 📉":
        df[m['gdp']] -= (8.0 * mult); df[m['cpi']] -= (2.0 * mult)
    elif scenario == "High Growth 🚀":
        df[m['gdp']] += (4.0 * mult); df[m['cpi']] -= (1.0 * mult)

    avg_g = df[m['gdp']].mean()
    df['Taylor'] = m['n'] + 0.5*(df[m['cpi']] - m['t']) + 0.5*(df[m['gdp']] - avg_g)
    if view_real: df[m['p']] -= df[m['cpi']]
    if lag > 0: df[m['cpi']] = df[m['cpi']].shift(lag); df[m['gdp']] = df[m['gdp']].shift(lag)

    st.markdown(f"<div class='main-title'><i class='fas fa-scale-balanced'></i> {market.upper()} STRATEGY TERMINAL</div>", unsafe_allow_html=True)
    
    # METRICS
    lp, lc, lg = df[m['p']].iloc[-1], df[m['cpi']].iloc[-1], df[m['gdp']].iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("POLICY RATE", f"{lp:.2f}%")
    c2.metric("CPI INFLATION", f"{lc:.2f}%")
    c3.metric("GDP GROWTH", f"{lg:.1f}%")
    c4.metric(f"FX ({m['sym']})", f"{df[m['fx']].iloc[-1]:.2f}")

    # CHART I
    st.markdown("<div class='section-header'><i class='fas fa-chart-line'></i> I. Monetary Policy & FX Transmission</div>", unsafe_allow_html=True)
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Policy Rate", line=dict(color='#002366', width=3)), secondary_y=False)
    if show_taylor: fig1.add_trace(go.Scatter(x=df['Date'], y=df['Taylor'], name="Taylor Rule", line=dict(color='#8B4513', dash='dash')), secondary_y=False)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="FX Spot", line=dict(color='#2E8B57')), secondary_y=True)
    fig1.update_layout(height=400, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    # --- Add inside your Figure definition ---

# Add the Taylor Line
fig.add_trace(go.Scatter(x=df.index, y=df['Taylor_Rate'], name="Taylor Rule (Optimal)", line=dict(dash='dash', color='red')))

# Highlight "Behind the Curve" periods with red shading
for i in range(1, len(df)):
    if df['Policy_Gap'].iloc[i] < -2.0: # If the gap is more than 2%
        fig.add_vrect(x0=df.index[i-1], x1=df.index[i], 
                      fillcolor="red", opacity=0.1, layer="below", line_width=0)
    st.plotly_chart(fig1, use_container_width=True)
    
    st.markdown(f"""<div class='analyst-card'><b>Monetary Insight:</b> The spread between the actual Policy Rate and the Taylor Rule suggests a <b>{'Hawkish' if lp > df['Taylor'].iloc[-1] else 'Dovish'}</b> stance. 
    The current FX trend indicates <b>{'capital outflows' if df[m['fx']].iloc[-1] > df[m['fx']].iloc[-2] else 'currency appreciation'}</b> which may influence future import prices.</div>""", unsafe_allow_html=True)

    # CHART II
    st.markdown("<div class='section-header'><i class='fas fa-chart-column'></i> II. Real Economy: Growth & Inflation Linkage</div>", unsafe_allow_html=True)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(x=df['Date'], y=df[m['gdp']], name="Real GDP Growth", marker_color='#BDB7AB'), secondary_y=False)
    fig2.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI (YoY)", line=dict(color='#A52A2A', width=3)), secondary_y=True)
    fig2.update_layout(height=400, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"""<div class='analyst-card'><b>Growth Insight:</b> Under the <b>{scenario}</b> scenario, the economy is experiencing <b>{'contractionary' if lg < 0 else 'expansionary'}</b> pressure. 
    The CPI trajectory reflects <b>{'accelerating' if lc > 3.0 else 'disinflationary'}</b> dynamics, potentially forcing a recalibration of real interest rates.</div>""", unsafe_allow_html=True)

    # FOR YOU
    st.markdown("<div class='section-header'><i class='fas fa-user-tie'></i> III. For You</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='for-you-card'><b>Strategic Personal Guidance:</b><br>
    • <b>Mortgages/Loans:</b> Borrowing costs are currently <b>{'Restrictive' if lp > 4.5 else 'Accommodative'}</b>. High severity in {scenario} suggests potential tightening ahead.<br>
    • <b>Personal Savings:</b> Current rates offer <b>{'strong' if lp > 4.5 else 'limited'}</b> returns for cash deposits. Consider hedging against {lc:.1f}% inflation.<br>
    • <b>Daily Budget:</b> At {lc:.1f}% CPI, your purchasing power is <b>{'eroding' if lc > 3 else 'stable'}</b>. Plan for increased essential costs.</div>""", unsafe_allow_html=True)

    # STATS & METHODOLOGY
    st.divider()
    colA, colB = st.columns([1, 1.2])
    with colA:
        st.markdown("<div class='section-header'><i class='fas fa-table'></i> IV. Correlation Matrix</div>", unsafe_allow_html=True)
        corr = df[[m['p'], m['cpi'], m['gdp'], m['fx']]].corr()
        st.dataframe(corr.style.background_gradient(cmap='PuBu').format("{:.2f}"), use_container_width=True)
        st.markdown(f"""<div class='analyst-card' style='border-left:5px solid #7A6D5D;'><b>Correlation Insight:</b> The strongest relationship is between <b>{corr.unstack().sort_values(ascending=False).index[4][0]}</b> and <b>{corr.unstack().sort_values(ascending=False).index[4][1]}</b>. 
        High correlation implies that changes in one variable will likely trigger immediate volatility in the other.</div>""", unsafe_allow_html=True)

    with colB:
        st.markdown("<div class='section-header'><i class='fas fa-book'></i> V. Methodological Note</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='method-card'>
            <b>1. Taylor Rule Modelling:</b> We utilize a standard monetary reaction function: $i = r^* + \pi + 0.5(\pi - \pi^*) + 0.5(y - y^*)$. 
            This identifies where the 'neutral' rate should sit based on the Output Gap and Inflation Gap.<br><br>
            <b>2. Scenario Overrides:</b> 
            - <i>Stagflation:</i> Applies a +500bps shock to CPI and a -300bps shock to GDP, scaled by user-defined severity.
            - <i>Depression:</i> Forces a -800bps contraction in GDP and a -200bps deflationary shock to CPI.
            - <i>High Growth:</i> Projects a +400bps GDP expansion with moderate -100bps price stabilization.<br><br>
            <b>3. Data Integrity:</b> FX data is resampled to monthly mean (MS) to eliminate high-frequency noise and align with lagging GDP reporting cycles.
        </div>""", unsafe_allow_html=True)

else:
    st.error("Missing Data: Ensure .xlsx files are present in the directory.")
