from ipyfilechooser import FileChooser
import pandas as pd

def select_file(initial_path='/eos/project-c/collimation-team/machine_configurations'):
    file_chooser = FileChooser(initial_path)
    display(file_chooser)
    
    def on_selection_change(change):
        if file_chooser.selected:
            print(f"Selected file: {file_chooser.selected}")

    file_chooser.register_callback(on_selection_change)
    return file_chooser

def shift_and_redefine(df, new_zero, s):
    """
    shifts a graph to set a new element/value as zero
    """
    # Substract the new 0 from S
    df[s] = df[s] - new_zero
    
    last_value = 26658.88318

    # Add length of the graph to 'S' values less than 0
    df.loc[df[s] < 0, s] += last_value

    df = df.sort_values(by=s)
    df = df.reset_index(drop=True)

    return df

def shift_by(df, by, s):
    """
    shifts a graph by a given value
    """
    # Add the value to shift to the dataframe
    df[s] = df[s] + by

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