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
    
    # We will search for a sheet that has 'Date' and country names
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            df = df.sort_values('Date')
            return df, sheet
            
    st.error("Could not find a valid 'Date' column.")
    st.stop()

df, used_sheet = load_data()

# --- APP UI ---
st.title("🏦 Macroeconomic Research Terminal")
st.caption(f"Analyzing Data from Sheet: **{used_sheet}**")

market = st.sidebar.selectbox("Select Market", ["India", "UK", "Singapore"])

# --- UPDATED COLUMN MAP ---
# Based on your feedback, the inflation columns are just the country names.
# Note: We are using the same column for both lines for a moment just to 
# get the chart to appear. If you have another sheet for 'Policy Rates', 
# let me know!
m_map = {
    "India": {"cpi": "India"},
    "UK": {"cpi": "UK"},
    "Singapore": {"cpi": "Singapore"}
}

try:
    m = m_map[market]
    col_name = m['cpi']
    
    # Ensure data is numeric
    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
    plot_df = df.dropna(subset=[col_name])
    
    # Create the Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=plot_df['Date'], 
        y=plot_df[col_name], 
        name=f"{market} Inflation", 
        line=dict(color="#d32f2f", width=3)
    ))
    
    fig.update_layout(
        title=f"Historical Inflation Trend: {market}",
        template="plotly_white", 
        hovermode="x unified",
        xaxis_title="Timeline",
        yaxis_title="Percentage (%)"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Latest Data Metric
    last_val = plot_df[col_name].iloc[-1]
    st.metric(label=f"Latest {market} Reading", value=f"{last_val:.2f}%")
    
except Exception as e:
    st.error(f"Mapping Error: {e}")
    st.write("Current Sheet Columns:", list(df.columns))
