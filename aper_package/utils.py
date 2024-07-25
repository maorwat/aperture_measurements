import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os

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

def select_file(path, title, initial_path='/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/'):

    # If path provided use it
    if path:
        file_path = path
    # If no display environment available (SWAN)
    elif not os.getenv('DISPLAY'):
        print(f"No display found. Please manually provide the path for {title} or provide tha path as an argument.")
        return input(f"Enter path for {title}: ")
    # Else ask to select a file
    else:
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        file_path = filedialog.askopenfilename(initialdir=initial_path, title=f'Select {title}')
    
    return file_path

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