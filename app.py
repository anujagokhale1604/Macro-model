import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Macro Policy Lab", layout="wide")

@st.cache_data
def load_data():
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    if os.path.exists(file_name):
        # We read the file
        df = pd.read_excel(file_name)
        
        # CLEANING: This removes hidden spaces from column names
        df.columns = df.columns.str.strip()
        
        # DEBUGGING: If 'Date' is still missing, show the user the names
        if 'Date' not in df.columns:
            st.error(f"⚠️ Column 'Date' not found.")
            st.write("Your Excel columns are named:", list(df.columns))
            st.stop()
            
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    else:
        st.error(f"Could not find {file_name}")
        st.stop()

df = load_data()

# --- THE REST OF THE APP ---
st.title("🏦 Macroeconomic Research Terminal")
market = st.sidebar.selectbox("Select Market", ["India", "UK", "Singapore"])

m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}

# Final check: Make sure the market columns exist too
try:
    m = m_map[market]
    st.metric(f"Latest {market} CPI", f"{df[m['cpi']].iloc[-1]:.2f}%")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="Inflation", line=dict(color="red")))
    fig.add_trace(go.Scatter(x=df['Date'], y=df[m['rate']], name="Policy Rate", line=dict(color="blue")))
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
except KeyError as e:
    st.error(f"⚠️ Column {e} not found in Excel. Check your header names!")
    st.write("Available columns:", list(df.columns))
