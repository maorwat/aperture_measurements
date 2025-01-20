import pandas as pd
import xtrack as xt
import tkinter as tk
import numpy as np
from tkinter import filedialog
import os

from ipyfilechooser import FileChooser
from IPython.display import display
import ipywidgets as widgets

from datetime import datetime, timezone, timedelta

def find_s_value(name, data):
    """
    Finds a position of an element
    """
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
    """
    shifts a graph by a given value
    """
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
    # TODO: maybe use the function below rather than repeat the same thing

    df1 = twiss
    df2 = aper

    # Convert both columns to lowercase
    df1['name'] = df1['name'].str.lower()
    df2['NAME'] = df2['NAME'].str.lower()

    # Merge the DataFrames on the normalized 'name' column
    merged_df = pd.merge(df1, df2, left_on='name', right_on='NAME')
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

def match_with_twiss(twiss, aper_to_match):

    # Convert the 'NAME' column to lowercase to match the 'name' column in df_correct
    aper_to_match['name'] = aper_to_match['NAME'].str.lower()

    # Merge the dataframes on the 'name' column
    df_merged = aper_to_match.merge(twiss[['name', 's']], on='name', how='left')

    df_merged = df_merged.drop(columns=['name'])

    # Update the 'S' column in df_incorrect with the 's' values from df_correct
    df_merged.rename(columns={'s':'S'}, inplace=True)

    df_merged = df_merged.sort_values(by='S').dropna()
    df_merged = df_merged.reset_index(drop=True)

    return df_merged

def print_and_clear(message):
    #need to get rid of that
    print(message)

def transform_string(s):
        # Replace 'acb' with 'mcb'
        s = s.replace('acb', 'mcb')
        
        # Identify the parts of the string
        prefix = s[:3]      # 'mcb'
        rest = s[3:]        # 'v21.l3b1'
        
        # Extract the first letter/number combination
        part1, part2 = rest.split('.', 1) # part1 = 'v21', part2 = 'l3b1'
        
        # Reconstruct the string
        transformed = f"{prefix}{part1[0]}.{part1[1:]}{part2[:2]}.{part2[2:]}"
        
        return transformed

def reverse_transform_string(s):
    # Replace 'mcb' back with 'acb'
    s = s.replace('mcb', 'acb')
    
    # Identify the parts of the string
    prefix = s[:3]      # 'acb'
    rest = s[3:]        # 'v.21l3.b1'
    
    # Extract the parts
    part1, rest = rest.split('.', 1)  # part1 = 'v', rest = '21l3.b1'
    part2, part3 = rest.split('.', 1) # part2 = '21l3', part3 = 'b1'
    
    # Reconstruct the original string
    original = f"{prefix}{part1}{part2[:2]}.{part2[2:]}{part3}"
    
    return original

def matchSummary(opt):
    for tt in opt._err.targets:
        if tt.line:
            nn = " ".join((tt.line,) + tt.tar)
            rr = tt.action.run()[tt.line][tt.tar]
        else:
            nn = tt.tar
            rr = tt.action.run()[tt.tar]
        if type(tt.value) == xt.match.LessThan:
            vv = tt.value.upper
            dd = rr - vv
            print(f"{nn:25}: {rr:15.7e} {vv:15.7e} d={dd:15.7e} {rr<(vv+tt.tol)}")
        elif type(tt.value) == xt.match.GreaterThan:
            vv = tt.value.lower
            dd = rr - vv
            print(f"{nn:25}: {rr:15.7e} {vv:15.7e} d={dd:15.7e} {rr>(vv-tt.tol)}")
        elif hasattr(tt, "rhs"):
            vv = tt.rhs
            dd = rr - vv
            if tt.ineq_sign == ">":
                print(f"{nn:25}: {rr:15.7e} {vv:15.7e} d={dd:15.7e} {rr>(vv-tt.tol)}")
            else:
                print(f"{nn:25}: {rr:15.7e} {vv:15.7e} d={dd:15.7e} {rr<(vv+tt.tol)}")
        else:
            vv = tt.value
            dd = rr - vv
            dd = np.abs(dd)
            try:
                nn = " ".join(nn)
            except:
                nn = tt.tar
            try:
                print(f"{nn:25}: {rr:15.7e} {vv:15.7e} d={dd:15.7e} {dd<tt.tol}")
            except:
                return [nn,rr,vv,dd,tt.tol]
