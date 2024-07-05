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
