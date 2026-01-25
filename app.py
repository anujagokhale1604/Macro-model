import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Macro Policy Lab", layout="wide")

@st.cache_data
def load_data():
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    if not os.path.exists(file_name):
        st.error(f"File {file_name} not found.")
        st.stop()

    xl = pd.ExcelFile(file_name)
    
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Check if 'Date' exists in this sheet
        if 'Date' in df.columns:
            # MAGIC FIX: errors='coerce' turns crazy dates into 'NaT' instead of crashing
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            
            # Remove any rows where Date became NaT (the stray text/total rows)
            df = df.dropna(subset=['Date'])
            
            # Sort by date so the chart flows correctly
            df = df.sort_values('Date')
            return df, sheet
            
    st.error("Could not find a valid 'Date' column.")
    st.stop()

df, used_sheet = load_data()

# --- APP UI ---
st.title("🏦 Macroeconomic Research Terminal")
market = st.sidebar.selectbox("Select Market", ["India", "UK", "Singapore"])

m_map = {
    "India": {"cpi": "CPI_India", "rate": "Policy_India"},
    "UK": {"cpi": "CPI_UK", "rate": "Policy_UK"},
    "Singapore": {"cpi": "CPI_Singapore", "rate": "Policy_Singapore"}
}

try:
    m = m_map[market]
    # Ensure data is numeric
    df[m['cpi']] = pd.to_numeric(df[m['cpi']], errors='coerce')
    df[m['rate']] = pd.to_numeric(df[m['rate']], errors='coerce')
    
    # Drop empty values for the chart
    plot_df = df.dropna(subset=[m['cpi'], m['rate']])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df[m['cpi']], name="Inflation", line=dict(color="#d32f2f")))
    fig.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df[m['rate']], name="Policy Rate", line=dict(color="#1a237e")))
    
    fig.update_layout(template="plotly_white", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    
    # Metric for the latest available data
    last_row = plot_df.iloc[-1]
    st.metric(f"Latest {market} CPI", f"{last_row[m['cpi']]:.2f}%")
    
except Exception as e:
    st.warning(f"Formatting issues on sheet '{used_sheet}': {e}")
    st.write("Found Columns:", list(df.columns))
