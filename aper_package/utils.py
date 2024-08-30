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

def match_with_twiss(twiss, aper_to_match):

    # Convert the 'NAME' column to lowercase to match the 'name' column in df_correct
    aper_to_match['name'] = aper_to_match['NAME'].str.lower()

    # Merge the dataframes son the 'name' column
    df_merged = aper_to_match.merge(twiss[['name', 's']], on='name', how='left')

    df_merged = df_merged.drop(columns=['name', 'S'])

    # Update the 'S' column in df_incorrect with the 's' values from df_correct
    df_merged.rename(columns={'s':'S'}, inplace=True)

    df_merged = df_merged.sort_values(by='S').dropna()
    df_merged = df_merged.reset_index(drop=True)

    return df_merged

def print_and_clear(message):

    print(message+'                                                                            ', end="\r")

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
