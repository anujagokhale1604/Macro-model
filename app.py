import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Macro Policy Lab", layout="wide")

# --- DATA LOADING ---
@st.cache_data
def load_data():
    # Use the exact filename of your uploaded Excel file
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    
    if os.path.exists(file_name):
        # We use pd.read_excel because it is an .xlsx file
        df = pd.read_excel(file_name)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    else:
        st.error(f"⚠️ Could not find {file_name}")
        st.write("Files currently in your GitHub folder:", os.listdir("."))
        st.stop()

df = load_data()

# --- DASHBOARD ---
st.title("🏦 Macroeconomic Research Terminal")
market = st.sidebar.selectbox("Select Market", ["India", "UK", "Singapore"])

m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}
m = m_map[market]

st.metric(f"Latest {market} CPI", f"{df[m['cpi']].iloc[-1]:.2f}%")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="Inflation", line=dict(color="red")))
fig.add_trace(go.Scatter(x=df['Date'], y=df[m['rate']], name="Policy Rate", line=dict(color="blue")))
fig.update_layout(template="plotly_white")
st.plotly_chart(fig, use_container_width=True)
