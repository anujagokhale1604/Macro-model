import pandas as pd
import numpy as np

def clean_macro_data():
    # 1. FIX POLICY RATE (Handling Year-Header rows)
    policy_raw = pd.read_csv('EM_Macro_Data_India_SG_UK.xlsx - Policy_Rate.csv')
    policy_raw = policy_raw.dropna(how='all').reset_index(drop=True)
    
    current_year = None
    cleaned_rows = []
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for _, row in policy_raw.iterrows():
        val = str(row['Date']).strip()
        if val.isdigit() and len(val) == 4:
            current_year = val
        elif val in months:
            if current_year:
                date_obj = pd.to_datetime(f"{val} {current_year}", format='%b %Y')
                cleaned_rows.append({
                    'Date': date_obj,
                    'India_Policy': row['India'],
                    'UK_Policy': row['UK'],
                    'Singapore_Policy': row['Singapore']
                })
    
    policy_df = pd.DataFrame(cleaned_rows)

    # 2. FIX EXCHANGE RATES (Convert Daily to Monthly Average)
    def get_monthly_fx(file, col_name, new_name):
        df = pd.read_csv(file, parse_dates=['observation_date'])
        df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
        return df.resample('MS', on='observation_date').mean().reset_index().rename(
            columns={'observation_date': 'Date', col_name: new_name})

    inr_monthly = get_monthly_fx('DEXINUS.xlsx - Daily.csv', 'DEXINUS', 'USDINR')
    gbp_monthly = get_monthly_fx('DEXUSUK.xlsx - Daily.csv', 'DEXUSUK', 'USDGBP')

    # 3. MERGE EVERYTHING
    master = policy_df.merge(inr_monthly, on='Date', how='left')
    master = master.merge(gbp_monthly, on='Date', how='left')
    
    # Sort by date for analysis
    master = master.sort_values('Date')
    
    return master

# Execute and Save
cleaned_data = clean_macro_data()
cleaned_data.to_csv('Cleaned_Macro_Data.csv', index=False)
print("Processing complete. Created 'Cleaned_Macro_Data.csv' with uniform dates.")
