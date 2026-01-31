import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PREMIUM STYLING ---
st.set_page_config(page_title="Macro Intelligence Terminal", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F5F5DC; color: #2c3e50; }
    section[data-testid="stSidebar"] { background-color: #2c3e50 !important; border-right: 2px solid #d4af37; }
    section[data-testid="stSidebar"] .stWidgetLabel, section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stSlider { color: #ecf0f1 !important; }
    
    .main-title { 
        font-size: 38px; font-weight: 900; color: #002366; 
        border-bottom: 4px solid #d4af37; padding-bottom: 10px; margin-bottom: 25px; 
    }
    
    .note-box { padding: 18px; border-radius: 8px; border: 1px solid #d4af37; background-color: #ffffff; margin-bottom: 20px; line-height: 1.6; }
    .header-gold { color: #b8860b; font-weight: bold; font-size: 18px; margin-bottom: 8px; text-transform: uppercase; }
    .logo-container { display: flex; justify-content: center; margin-bottom: 20px; }
    .analyst-verdict { padding: 15px; border-left: 5px solid #002366; background-color: #e8efff; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
@st.cache_data
def load_data():
    # Note: Using .xlsx per system instructions
    files = {"workbook": 'EM_Macro_Data_India_SG_UK.xlsx', "inr": 'DEXINUS.xlsx', "gbp": 'DEXUSUK.xlsx', "sgd": 'AEXSIUS.xlsx'}
    
    try:
        df_macro = pd.read_excel(files["workbook"], sheet_name='Macro data')
        df_macro['Date'] = pd.to_datetime(df_macro['Date'], errors='coerce')
        
        df_gdp = pd.read_excel(files["workbook"], sheet_name='GDP_Growth', skiprows=1).iloc[1:, [0, 2, 3, 4]]
        df_gdp.columns = ['Year', 'GDP_India', 'GDP_Singapore', 'GDP_UK']
        df_gdp['Year'] = pd.to_numeric(df_gdp['Year'], errors='coerce')

        def get_fx(path, out_col):
            xls = pd.ExcelFile(path)
            sheet = [s for s in xls.sheet_names if s != 'README'][0]
            f = pd.read_excel(path, sheet_name=sheet)
            d_col = [c for c in f.columns if 'date' in c.lower()][0]
            v_col = [c for c in f.columns if c != d_col][0]
            f[d_col] = pd.to_datetime(f[d_col], errors='coerce')
            f[v_col] = pd.to_numeric(f[v_col], errors='coerce')
            return f.dropna().resample('MS', on=d_col).mean().reset_index().rename(columns={d_col:'Date', v_col:out_col})

        fx_inr, fx_gbp, fx_sgd = get_fx(files["inr"], 'FX_India'), get_fx(files["gbp"], 'FX_UK'), get_fx(files["sgd"], 'FX_Singapore')
        df_macro['Year'] = df_macro['Date'].dt.year
        df = df_macro.merge(df_gdp, on='Year', how='left').merge(fx_inr, on='Date', how='left').merge(fx_gbp, on='Date', how='left').merge(fx_sgd, on='Date', how='left')
        return df.sort_values('Date').ffill()
    except Exception as e:
        st.error(f"Data Loading Error: Ensure all .xlsx files are in the directory. {e}")
        return pd.DataFrame()

# --- 3. SIDEBAR: THE ANALYTIC HUB ---
with st.sidebar:
    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    st.image("https://cdn-icons-png.flaticon.com/512/2830/2830284.png", width=80) 
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.button("🔄 Reset Terminal"): st.rerun()
    
    market = st.selectbox("Market Focus", ["India", "UK", "Singapore"])
    horizon = st.radio("Lookback Window", ["Historical", "10 Years", "5 Years"], index=1)
    
    st.divider()
    st.markdown("⚠️ **SCENARIO ANALYSIS**")
    scenario = st.selectbox("Global Event", ["Standard", "Stagflation 🌪️", "Depression 📉", "High Growth 🚀"])
    severity = st.slider("Scenario Severity (%)", 0, 100, 50)
    
    st.divider()
    st.markdown("🛠️ **ADVANCED LEVERS**")
    view_real = st.toggle("View 'Real' Interest Rates", help="Nominal Rate minus Inflation")
    rate_intervention = st.slider("Manual Rate Intervention (bps)", -200, 200, 0, step=25)
    lag_effect = st.selectbox("Transmission Lag (Months)", [0, 3, 6, 12])
    
    st.divider()
    st.markdown("📈 **MARKET SENTIVITY**")
    sentiment = st.select_slider("Global Sentiment", options=["Risk-Off", "Neutral", "Risk-On"], value="Neutral")
    show_taylor = st.toggle("Overlay Taylor Rule (Policy Target)")

# --- 4. DYNAMIC LOGIC ENGINE ---
raw_df = load_data()
if not raw_df.empty:
    m_map = {
        "India": {"p": "Policy_India", "cpi": "CPI_India", "gdp": "GDP_India", "fx": "FX_India", "sym": "INR", "target": 4.0, "neutral": 4.5},
        "UK": {"p": "Policy_UK", "cpi": "CPI_UK", "gdp": "GDP_UK", "fx": "FX_UK", "sym": "GBP", "target": 2.0, "neutral": 2.5},
        "Singapore": {"p": "Policy_Singapore", "cpi": "CPI_Singapore", "gdp": "GDP_Singapore", "fx": "FX_Singapore", "sym": "SGD", "target": 2.0, "neutral": 2.5}
    }
    m = m_map[market]
    df = raw_df.copy()

    # Filter Horizon
    if horizon == "10 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=10))]
    elif horizon == "5 Years": df = df[df['Date'] > (df['Date'].max() - pd.DateOffset(years=5))]

    # Apply Simulations
    mult = severity / 100
    df[m['p']] += (rate_intervention / 100)
    
    if "Stagflation" in scenario:
        df[m['cpi']] += (5.0 * mult); df[m['gdp']] -= (3.0 * mult)
    elif "Depression" in scenario:
        df[m['gdp']] -= (8.0 * mult); df[m['cpi']] -= (2.0 * mult)
    elif "High Growth" in scenario:
        df[m['gdp']] += (4.0 * mult); df[m['cpi']] -= (1.0 * mult)

    # Sentiment FX Impact
    if sentiment == "Risk-Off": df[m['fx']] *= 1.05
    elif sentiment == "Risk-On": df[m['fx']] *= 0.95

    # Taylor Rule Calc: Rate = Neutral + 0.5*(Inf - Target) + 0.5*(GDP - Avg)
    avg_gdp = df[m['gdp']].mean()
    df['Taylor_Rule'] = m['neutral'] + 0.5*(df[m['cpi']] - m['target']) + 0.5*(df[m['gdp']] - avg_gdp)

    if view_real: df[m['p']] = df[m['p']] - df[m['cpi']]
    if lag_effect > 0:
        df[m['cpi']] = df[m['cpi']].shift(lag_effect)
        df[m['gdp']] = df[m['gdp']].shift(lag_effect)

    # --- 5. INTERFACE ---
    st.markdown(f"<div class='main-title'>{market.upper()} // STRATEGIC MACRO TERMINAL</div>", unsafe_allow_html=True)

    def get_val(series): return series.dropna().iloc[-1] if not series.dropna().empty else 0
    latest_p = get_val(df[m['p']])
    latest_c = get_val(df[m['cpi']])
    latest_g = get_val(df[m['gdp']])
    latest_t = get_val(df['Taylor_Rule'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Policy Rate", f"{latest_p:.2f}%", delta=f"{rate_intervention} bps")
    c2.metric("Inflation (CPI)", f"{latest_c:.2f}%")
    c3.metric("GDP Growth", f"{latest_g:.1f}%")
    c4.metric(f"FX Spot ({m['sym']})", f"{get_val(df[m['fx']]):.2f}")

    # Graphs
    st.markdown("<div class='header-gold'>I. Monetary Corridor & Policy Deviation</div>", unsafe_allow_html=True)
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['p']], name="Actual Rate", line=dict(color='#1f77b4', width=3)), secondary_y=False)
    if show_taylor:
        fig1.add_trace(go.Scatter(x=df['Date'], y=df['Taylor_Rule'], name="Taylor Rule (Suggested)", line=dict(color='orange', width=2, dash='dash')), secondary_y=False)
    fig1.add_trace(go.Scatter(x=df['Date'], y=df[m['fx']], name="FX Spot", line=dict(color='#d4af37', width=2, dash='dot')), secondary_y=True)
    fig1.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=400, hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("<div class='header-gold'>II. Economic Health: Growth vs. Inflation</div>", unsafe_allow_html=True)
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    fig2.add_trace(go.Bar(x=df['Date'], y=df[m['gdp']], name="GDP Growth (%)", marker_color='#2ecc71', opacity=0.7), secondary_y=False)
    fig2.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="CPI Inflation (%)", line=dict(color='#e74c3c', width=3)), secondary_y=True)
    fig2.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', height=400, hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    # --- 6. DYNAMIC RECRUITER NOTES ---
    st.divider()
    colA, colB = st.columns(2)

    with colA:
        st.markdown("<div class='header-gold'>Executive Summary & Analyst Verdict</div>", unsafe_allow_html=True)
        # Dynamic Verdict Logic
        if latest_p < latest_t - 1.0:
            verdict = "The Central Bank is currently <b>significantly behind the curve</b> (too dovish). This risks further currency depreciation."
        elif latest_p > latest_t + 1.0:
            verdict = "The Policy Rate is <b>restrictive</b> compared to the Taylor Rule suggestion, which may dampen GDP growth but protect the currency."
        else:
            verdict = "Policy rates are <b>neutral and aligned</b> with current inflation and growth gaps."

        st.markdown(f"""<div class='note-box'>
        <b>Current Scenario:</b> {scenario} at {severity}% intensity.<br>
        <div class='analyst-verdict'>{verdict}</div><br>
        <b>Recommendation:</b> {"Focus on inflation-protected assets." if latest_c > latest_p else "Fixed income assets are yielding positive real returns."}
        </div>""", unsafe_allow_html=True)
        
        if st.button("📊 Run Statistical Correlation Matrix"):
            st.markdown("<div class='header-gold'>Correlation Analysis</div>", unsafe_allow_html=True)
            corr = df[[m['p'], m['cpi'], m['gdp'], m['fx']]].corr()
            st.write(corr.style.background_gradient(cmap='RdYlGn'))

    with colB:
        st.markdown("<div class='header-gold'>Methodological Framework</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='note-box'>
        <b>The Taylor Rule Overlay:</b> This model uses a neutral rate of {m['neutral']}% to estimate the "correct" policy stance. It assumes a 0.5 weight on both inflation and output gaps.<br><br>
        <b>Frequency Synthesis:</b> To prevent data-loss, we use monthly resampled FX means paired with annual GDP step-functions. This allows daily market movements to be analyzed alongside structural economic shifts.<br><br>
        <b>Sentiment Modeling:</b> The Risk-Off toggle applies a 5% idiosyncratic shock to the FX pair, simulating a flight-to-safety capital flow.
        </div>""", unsafe_allow_html=True)
