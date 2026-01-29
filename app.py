import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    # 1. LOAD AND CLEAN POLICY RATES
    # Added engine='openpyxl' to ensure compatibility with Streamlit Cloud
    try:
        policy_df_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Policy_Rate', engine='openpyxl')
    except Exception as e:
        st.error(f"Error loading Policy_Rate sheet: {e}")
        return pd.DataFrame()

    current_year = None
    cleaned_rows = []
    months_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    
    for _, row in policy_df_raw.iterrows():
        # Clean the value: convert to string, remove decimals if any, and strip whitespace
        val = str(row['Date']).split('.')[0].strip()
        
        # Logic: If 4 digits, it's our anchor year
        if val.isdigit() and len(val) == 4:
            current_year = int(val)
        # If it's a month, combine with current_year
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

    # 2. LOAD AND RESAMPLE EXCHANGE RATES
    def get_monthly_fx(filename, col_name, label):
        try:
            df = pd.read_excel(filename, sheet_name='Daily', engine='openpyxl')
            # Ensure the date column is datetime objects
            df['observation_date'] = pd.to_datetime(df['observation_date'], errors='coerce')
            # Drop rows where date conversion failed
            df = df.dropna(subset=['observation_date'])
            # Convert values to numeric, turning '.' or 'ND' into NaN
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
            # Aggregate to Monthly Start ('MS') and average the rates
            monthly = df.resample('MS', on='observation_date').mean().reset_index()
            return monthly.rename(columns={'observation_date': 'Date', col_name: label})
        except Exception as e:
            st.warning(f"Could not process {filename}: {e}")
            return pd.DataFrame(columns=['Date', label])

    inr_monthly = get_monthly_fx('DEXINUS.xlsx', 'DEXINUS', 'USDINR')
    gbp_monthly = get_monthly_fx('DEXUSUK.xlsx', 'DEXUSUK', 'USDGBP')

    # 3. MERGE ALL INTO ONE DATAFRAME
    if not policy_clean.empty:
        master = policy_clean.merge(inr_monthly, on='Date', how='left')
        master = master.merge(gbp_monthly, on='Date', how='left')
        master = master.sort_values('Date').reset_index(drop=True)
        return master
    else:
        return pd.DataFrame()

# Main App Execution
st.set_page_config(page_title="Macro Analysis", layout="wide")
st.title("🌏 Macro Economic Analysis")

df = load_data()

if not df.empty:
    st.subheader("Data Overview")
    st.write(df.tail(12)) # Show the last year of data

    # Visualization
    st.subheader("Policy Rates vs Exchange Rates")
    
    # Let user pick a country
    country = st.selectbox("Select Country to Visualize", ["India", "UK"])
    
    if country == "India":
        plot_cols = ['India_Policy', 'USDINR']
    else:
        plot_cols = ['UK_Policy', 'USDGBP']
        
    chart_data = df.set_index('Date')[plot_cols].dropna()
    st.line_chart(chart_data)
else:
    st.error("Data could not be loaded. Please check your Excel file names and sheet structures.")
