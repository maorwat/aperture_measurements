from ipyfilechooser import FileChooser
import numpy as np

def select_file(initial_path='/eos/project-c/collimation-team/machine_configurations'):
    file_chooser = FileChooser(initial_path)
    display(file_chooser)
    
    def on_selection_change(change):
        if file_chooser.selected:
            print(f"Selected file: {file_chooser.selected}")

    file_chooser.register_callback(on_selection_change)
    return file_chooser


def match_indices(short_arr, long_arr):
    """
    Function to find the closest indices using a linear scan on sorted arrays
    Facilitates numpy operations
    """
    long_arr_indices = []
    for i in range(len(short_arr)):
        #find the index of s2 that's the closest to s1[i]
        j = np.argmin(abs(long_arr - short_arr[i]))
        long_arr_indices.append(j)

    return long_arr_indices

def shift_and_redefine(df, delta_s):

    # Calculate the shift required to make the minimum s value zero
    df['S'] = df['S'] - delta_s
    last_value = df['S'].iloc[-1] - df['S'].iloc[0]

    # Find index of first positive value in any column
    first_positive_index = df[df['S'] > 0].index.min()

    # Roll all columns by the same amount
    for col in df.columns:
        df[col] = np.roll(df[col], -first_positive_index+1)

    # Add add_amount to 'S' values less than 0
    df.loc[df['S'] < 0, 'S'] += last_value

    # Check if the last value of 'S' is zero and add last_value if it is
    if df['S'].iloc[-1] == 0:
        df['S'].iloc[-1] += last_value