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


def match_indices_np(short_arr, long_arr):
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

def match_indices_slow(short_df, long_df):
    """
    Function to find the closest indices using a linear scan on sorted arrays
    Facilitates numpy operations
    """
    long_df_indices = []
    new_long_df = long_df[~long_df.name.str.contains('drift')]

    for i in range(short_df.shape[0]):
        #find the index of s2 that's the closest to s1[i]
        j = round(new_long_df['s'], 5) == short_df['S'].iloc[i]
        long_df_indices.append(j)

    return long_df_indices

def match_indices(short_df, long_df):
    """
    Function to find the closest indices using a linear scan on sorted arrays
    Facilitates numpy operations
    """
    long_df_indices = []
    new_long_df = long_df[~long_df.name.str.contains('drift')]

    for i in range(short_df.shape[0]):
        #find the index of s2 that's the closest to s1[i]
        j = round(new_long_df['s'], 5) == short_df['S'].iloc[i]
        long_df_indices.append(j)

    return long_df_indices

def shift_and_redefine(df, new_zero):

    # Substract the new 0 from S
    df['S'] = df['S'] - new_zero
    # Calculate the shift required to set new_zero as 0
    last_value = 26658.88318

    # Add add_amount to 'S' values less than 0
    df.loc[df['S'] < 0, 'S'] += last_value

    df = df.sort_values(by='S')
    df = df.reset_index(drop=True)

    return df