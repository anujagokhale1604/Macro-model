import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    # 1. LOAD AND CLEAN POLICY RATES
    # We use engine='openpyxl' to read the .xlsx file directly
    try:
        policy_df_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Policy_Rate', engine='openpyxl')
    except Exception as e:
        st.error(f"Could not find EM_Macro_Data_India_SG_UK.xlsx: {e}")
        return pd.DataFrame(), {}

    current_year = None
    cleaned_rows = []
    months_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    
    # Workaround for the year-header row format
    for _, row in policy_df_raw.iterrows():
        val = str(row['Date']).strip()
        # Check if row is a 4-digit year
        if val.isdigit() and len(val) == 4:
            current_year = int(val)
        # Check if row is a month name
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

    # 2. LOAD AND RESAMPLE EXCHANGE RATES (From separate XLSX files)
    def get_monthly_fx(filename, col_name, label):
        try:
            # Daily data to Monthly Average
            df = pd.read_excel(filename, sheet_name='Daily', engine='openpyxl')
            df['observation_date'] = pd.to_datetime(df['observation_date'])
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
            monthly = df.resample('MS', on='observation_date').mean().reset_index()
            return monthly.rename(columns={'observation_date': 'Date', col_name: label})
        except Exception as e:
            st.warning(f"Warning: {filename} processing issue: {e}")
            return pd.DataFrame(columns=['Date', label])

    inr_monthly = get_monthly_fx('DEXINUS.xlsx', 'DEXINUS', 'USDINR')
    gbp_monthly = get_monthly_fx('DEXUSUK.xlsx', 'DEXUSUK', 'USDGBP')

    # 3. MERGE EVERYTHING
    master = policy_clean.merge(inr_monthly, on='Date', how='left')
    master = master.merge(gbp_monthly, on='Date', how='left')
    master = master.sort_values('Date').reset_index(drop=True)
    
    # Creating the fx_dict expected by the rest of your app
    fx_dict = {
        'USDINR': inr_monthly,
        'USDGBP': gbp_monthly
    }
    
    return master, fx_dict

# App Execution
st.title("Macro Economic Analysis")

df, fx_dict = load_data()

if not df.empty:
    st.write("### Data Preview (Last 12 Months)")
    st.dataframe(df.tail(12))
    
    # Fixed Plotting Example
    st.subheader("Policy Rates vs FX")
    selection = st.selectbox("Select Country", ["India", "UK"])
    
    if selection == "India":
        st.line_chart(df.set_index('Date')[['India_Policy', 'USDINR']])
    else:
        st.line_chart(df.set_index('Date')[['UK_Policy', 'USDGBP']])
