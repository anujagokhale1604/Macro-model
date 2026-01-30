import pandas as pd
import streamlit as st
import plotly.express as px

@st.cache_data
def load_data():
    # --- 1. POLICY RATE CLEANING (The Excel Workaround) ---
    try:
        policy_df_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Policy_Rate', engine='openpyxl')
    except Exception as e:
        st.error(f"Error loading main macro file: {e}")
        return pd.DataFrame(), {}

    current_year = None
    cleaned_rows = []
    months_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                  'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    
    for _, row in policy_df_raw.iterrows():
        val = str(row['Date']).strip().split('.')[0]
        if val.isdigit() and len(val) == 4:
            current_year = int(val)
        elif val in months_map:
            if current_year:
                dt = pd.Timestamp(year=current_year, month=months_map[val], day=1)
                cleaned_rows.append({
                    'Date': dt,
                    'India_Policy': row['India'],
                    'UK_Policy': row['UK'],
                    'Singapore_Policy': row['Singapore']
                })
    policy_clean = pd.DataFrame(cleaned_rows)

    # --- 2. FX RATE CLEANING (Daily to Monthly Average) ---
    def process_fx(filename, col_name, label):
        try:
            fx_df = pd.read_excel(filename, sheet_name='Daily', engine='openpyxl')
            fx_df['observation_date'] = pd.to_datetime(fx_df['observation_date'])
            # Convert values to numeric (handles '.' or 'ND' as NaN)
            fx_df[col_name] = pd.to_numeric(fx_df[col_name], errors='coerce')
            # Resample to Monthly Start (MS) and get the average
            monthly = fx_df.resample('MS', on='observation_date').mean().reset_index()
            return monthly.rename(columns={'observation_date': 'Date', col_name: label})
        except Exception as e:
            st.warning(f"Could not process FX file {filename}: {e}")
            return pd.DataFrame(columns=['Date', label])

    inr_data = process_fx('DEXINUS.xlsx', 'DEXINUS', 'USDINR')
    gbp_data = process_fx('DEXUSUK.xlsx', 'DEXUSUK', 'USDGBP')

    # --- 3. MERGE ALL DATA ---
    master_df = policy_clean.merge(inr_data, on='Date', how='left')
    master_df = master_df.merge(gbp_data, on='Date', how='left')
    master_df = master_df.sort_values('Date')

    # Return dict for compatibility with your existing app structure if needed
    fx_dict = {'USDINR': inr_data, 'USDGBP': gbp_data}
    
    return master_df, fx_dict

# --- STREAMLIT UI ---
st.set_page_config(layout="wide")
st.title("Macro-Economic & FX Analysis Dashboard")

df, fx_dict = load_data()

if not df.empty:
    # Sidebar Filters
    st.sidebar.header("Settings")
    country = st.sidebar.selectbox("Select Country", ["India", "UK"])
    
    # Logic to select correct columns based on country
    if country == "India":
        policy_col, fx_col = 'India_Policy', 'USDINR'
        currency_label = "USD/INR"
    else:
        policy_col, fx_col = 'UK_Policy', 'USDGBP'
        currency_label = "USD/GBP (GBP per USD)"

    # Create two columns for the dashboard
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"{country} Policy Rate vs {currency_label}")
        # Plotting using Plotly for better interactivity
        fig = px.line(df, x='Date', y=[policy_col, fx_col], 
                     labels={"value": "Rate", "variable": "Indicator"},
                     title=f"Monthly Trends: {country}")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Data Summary")
        st.write(df[['Date', policy_col, fx_col]].tail(12))

else:
    st.error("Data could not be loaded. Check your .xlsx filenames.")
