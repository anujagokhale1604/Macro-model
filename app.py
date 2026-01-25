import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Macro Research Terminal", layout="wide")

@st.cache_data
def load_and_clean_data():
    file_name = 'EM_Macro_Data_India_SG_UK.xlsx'
    if not os.path.exists(file_name):
        st.error("File not found in GitHub.")
        st.stop()

    xl = pd.ExcelFile(file_name)
    all_sheets = {}

    for sheet in xl.sheet_names:
        # Load the raw sheet
        df = pd.read_excel(xl, sheet_name=sheet)
        
        # 1. FIND THE DATA START (Skip hidden/header rows)
        # We look for the first row that contains 'Date'
        found_start = False
        for i in range(min(len(df), 20)):  # Check first 20 rows
            row_values = [str(val).strip().lower() for val in df.iloc[i].values]
            if 'date' in row_values:
                # Set this row as the header
                df.columns = [str(c).strip() for c in df.iloc[i]]
                df = df.iloc[i+1:].reset_index(drop=True)
                found_start = True
                break
        
        if found_start:
            # 2. CLEANING
            # Convert Date and force errors to NaT (removes footer text/totals)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            
            # Ensure country columns are numeric
            for col in ['India', 'UK', 'Singapore']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            all_sheets[sheet] = df
            
    return all_sheets

# --- LOAD DATA ---
data_dict = load_and_clean_data()

# --- DASHBOARD UI ---
st.title("🏦 Macroeconomic Research Terminal")

if not data_dict:
    st.error("Could not find any sheet with a 'Date' column. Check Row 1-20 of your Excel.")
    st.stop()

# SIDEBAR: Select Category & Market
selected_category = st.sidebar.selectbox("Select Data Category", list(data_dict.keys()))
market = st.sidebar.selectbox("Select Market", ["India", "UK", "Singapore"])

df = data_dict[selected_category]

try:
    # Filter out empty rows for the specific market
    plot_df = df.dropna(subset=[market]).sort_values('Date')

    if plot_df.empty:
        st.warning(f"No data found for {market} in the '{selected_category}' sheet.")
    else:
        # DISPLAY METRIC
        current_val = plot_df[market].iloc[-1]
        st.metric(label=f"Latest {market} {selected_category}", value=f"{current_val:.2f}%")

        # DISPLAY CHART
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_df['Date'], 
            y=plot_df[market], 
            name=f"{market} {selected_category}",
            line=dict(color="#1a237e" if "Rate" in selected_category else "#d32f2f", width=3)
        ))

        fig.update_layout(
            template="plotly_white",
            hovermode="x unified",
            xaxis_title="Timeline",
            yaxis_title="Percentage (%)",
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

        # SHOW DATA TABLE (Optional check for you)
        with st.expander("View Raw Data Table"):
            st.dataframe(plot_df)

except Exception as e:
    st.error(f"Error displaying chart: {e}")
    st.write("Columns found in this sheet:", list(df.columns))
