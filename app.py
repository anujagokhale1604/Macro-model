import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Macro Policy Lab", layout="wide")

@st.cache_data
def load_data():
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    if os.path.exists(file_name):
        # 1. Read the Excel file
        # We try to find the data even if it's not on the first sheet
        xl = pd.ExcelFile(file_name)
        sheet_name = xl.sheet_names[0] # Takes the first tab
        df = pd.read_excel(file_name, sheet_name=sheet_name)
        
        # 2. If the first row is empty/numbers, we tell pandas to skip until it finds 'Date'
        # This fix handles cases where data starts further down in the Excel
        for i in range(10): # Check the first 10 rows
            if 'Date' in df.columns:
                break
            # Promote the next row to be the header
            new_header = df.iloc[0] 
            df = df[1:] 
            df.columns = new_header
            df.columns = df.columns.str.strip() # Remove spaces

        # 3. Final Check
        if 'Date' not in df.columns:
            st.error("⚠️ Analyst Note: I can't find a column named 'Date' in your Excel.")
            st.write("I see these headers instead:", list(df.columns))
            st.info("Tip: Make sure your Excel headers are in the very first row (Row 1).")
            st.stop()

        # Convert Date and drop any rows that are empty
        df = df.dropna(subset=['Date'])
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    else:
        st.error(f"File {file_name} not found.")
        st.stop()

df = load_data()

# --- THE UI ---
st.title("🏦 Macroeconomic Research Terminal")
market = st.sidebar.selectbox("Select Market", ["India", "UK", "Singapore"])

# Match these exactly to your Excel column names
m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}

try:
    m = m_map[market]
    # Convert data to numeric just in case Excel formatted them as text
    df[m['cpi']] = pd.to_numeric(df[m['cpi']], errors='coerce')
    df[m['rate']] = pd.to_numeric(df[m['rate']], errors='coerce')
    
    st.metric(f"Latest {market} CPI", f"{df[m['cpi']].iloc[-1]:.2f}%")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name="Inflation (CPI)", line=dict(color="#d32f2f")))
    fig.add_trace(go.Scatter(x=df['Date'], y=df[m['rate']], name="Policy Rate", line=dict(color="#1a237e")))
    fig.update_layout(template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    
except Exception as e:
    st.error(f"Column Error: {e}")
    st.write("Check if your Excel columns match these names: CPI_India, Policy_India, etc.")
