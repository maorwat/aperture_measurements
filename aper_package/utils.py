import pandas as pd
import numpy as np

def find_s_value(name, data):
    """Find a position of an element."""
    # Normalize the input name to lowercase
    name = name.lower()
    # Check if the aperture is loaded
    if hasattr(data, 'aper_b1'):
        df_list = [data.tw_b1, data.tw_b2, data.aper_b1, data.aper_b2]
    else: df_list = [data.tw_b1, data.tw_b2]
    
    # Iterate through each dataframe in the list
    for df in df_list:
        # Create a temporary copy of the DataFrame and change column names to lowercase
        df_temp = df.copy()
        df_temp.columns = df_temp.columns.str.lower()
        
        # Check if the 'name' column contains the given name
        if name in df_temp['name'].values:
            # Return the corresponding 's' value
            return df_temp.loc[df_temp['name'] == name, 's'].values[0]
    
    # If name is not found in any dataframe
    return None

def shift_by(df, by, s):
    """Shift a graph by a given value."""
    # Add the value to shift to the dataframe
    df.loc[:, s] = df.loc[:, s] + by

    # Calculate the shift required to set new_zero as 0
    last_value = 26658.88318

    if by > 0:
        # Substract length of the graph from 'S' values more than 26658.88318
        df.loc[df[s] > last_value, s] -= last_value
    else: 
        # Add length of the graph to 'S' values less than 0
        # This is the same as setting a new 0
        df.loc[df[s] < 0, s] += last_value

    df = df.sort_values(by=s)
    df = df.reset_index(drop=True)

    return df

def merge_twiss_and_aper(twiss, aper):

    # Convert both columns to lowercase
    aper['NAME'] = aper['NAME'].str.lower()

    # Merge the DataFrames on the normalized 'name' column
    merged_df = pd.merge(twiss, aper, left_on='name', right_on='NAME')
    # Drop the redundant 'NAME' column after merging
    merged_df.drop(columns=['NAME'], inplace=True)

    # Define columns to ignore for NaN checks
    ignore_columns = ['APER_TOL_1', 'APER_TOL_2', 'APER_TOL_3']

    # Get a list of columns to check for NaNs (all columns except the ignored ones)
    columns_to_check = merged_df.columns.difference(ignore_columns)

    # Drop rows where there are NaNs in columns_to_check
    # but keep rows if NaNs only appear in `ignore_columns`
    merged_df.dropna(subset=columns_to_check, how='any', inplace=True)
    # Reset the index and drop the old index column
    merged_df.reset_index(drop=True, inplace=True)
    
    return merged_df