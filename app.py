import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Macro Policy Lab", layout="wide")

@st.cache_data
def load_data():
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    if not os.path.exists(file_name):
        st.error(f"File {file_name} not found in GitHub.")
        st.stop()

    xl = pd.ExcelFile(file_name)
    
    # Try EVERY sheet in the Excel file
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        
        # Clean up column names (remove hidden spaces/newlines)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Look for 'Date' in the headers OR in the first few rows
        if 'Date' in df.columns:
            df = df.dropna(subset=['Date'])
            df['Date'] = pd.to_datetime(df['Date'])
            return df, sheet
            
        # If 'Date' wasn't in the header, maybe it's in the first row of data?
        # We search the first 5 rows to find the headers
        for i in range(min(len(df), 5)):
            if "Date" in df.iloc[i].values:
                df.columns = df.iloc[i].str.strip()
                df = df[i+1:].reset_index(drop=True)
                df = df.dropna(subset=['Date'])
                df['Date'] = pd.to_datetime(df['Date'])
                return df, sheet

    # If we get here, we found nothing
    st.error("⚠️ DATA FORMAT ERROR")
    st.write("I searched all tabs but couldn't find a column named 'Date'.")
    st.write("Current Tabs in Excel:", xl.sheet_names)
    st.info("Check: Is 'Date' written exactly like that in Row 1 of your Excel sheet?")
    st.stop()

df, used_sheet = load_data()

# --- APP UI ---
st.title("🏦 Macroeconomic Research Terminal")
st.caption(f"Connected to sheet: **{used_sheet}**")

market = st.sidebar.selectbox("Select Market", ["India", "UK", "Singapore"])

m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}

try:
    m = m_map[market]
    # Force numbers to be numbers (Excel sometimes keeps them as text)
    df[m['cpi']] = pd.to_numeric(df[m['cpi']], errors='coerce')
    df[m['rate']] = pd.to_numeric(df[m['rate']], errors='coerce')
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df[m['cpi']], name=f"{market} CPI (Inflation)", line=dict(color="#d32f2f")))
    fig.add_trace(go.Scatter(x=df['Date'], y=df[m['rate']], name=f"{market} Policy Rate", line=dict(color="#1a237e")))
    
    fig.update_layout(template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)
    
except Exception as e:
    st.warning(f"Columns not found in sheet '{used_sheet}'.")
    st.write("Available columns in this sheet:", list(df.columns))
