import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    # 1. LOAD AND CLEAN POLICY RATES
    # We read the Excel file and manually reconstruct the Date column
    policy_df_raw = pd.read_excel('EM_Macro_Data_India_SG_UK.xlsx', sheet_name='Policy_Rate')
    
    current_year = None
    cleaned_rows = []
    months_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    
    for _, row in policy_df_raw.iterrows():
        val = str(row['Date']).strip()
        # If the row is a 4-digit year (e.g., 2025), update the current year
        if val.isdigit() and len(val) == 4:
            current_year = int(val)
        # If the row is a month name, create the full date using the current year
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
    # Helper to convert daily rates in separate Excel files to monthly averages
    def get_monthly_fx(filename, col_name, label):
        df = pd.read_excel(filename, sheet_name='Daily')
        df['observation_date'] = pd.to_datetime(df['observation_date'])
        # Handle non-numeric characters like '.'
        df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
        # Aggregate to Monthly Start ('MS') to match policy data
        return df.resample('MS', on='observation_date').mean().reset_index().rename(
            columns={'observation_date': 'Date', col_name: label})

    inr_monthly = get_monthly_fx('DEXINUS.xlsx', 'DEXINUS', 'USDINR')
    gbp_monthly = get_monthly_fx('DEXUSUK.xlsx', 'DEXUSUK', 'USDGBP')

    # 3. MERGE ALL INTO ONE DATAFRAME
    master = policy_clean.merge(inr_monthly, on='Date', how='left')
    master = master.merge(gbp_monthly, on='Date', how='left')
    
    # Final cleanup: Sort by date and remove empty rows
    master = master.sort_values('Date').reset_index(drop=True)
    
    return master

# Use the function in your app
df = load_data()

st.title("Macro Economic Analysis")
st.write("Cleaned Data Preview", df.tail())

# Example Plotting code
# st.line_chart(df.set_index('Date')[['India_Policy', 'USDINR']])
