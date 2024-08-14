import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, List, Tuple, Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ipywidgets import widgets, VBox, HBox, Button, Layout, FloatText, DatePicker, Text, Dropdown
from IPython.display import display

from aper_package.figure_data import *
from aper_package.timber_data import BPMData
from aper_package.timber_data import CollimatorsData

def plot(data: object,
         spark: Optional[Any] = None, 
         width: Optional[int] = 1600, 
         height: Optional[int] = 600, 
         additional_traces: Optional[list] = None) -> None:
    """
    Create and display an interactive plot with widgets for controlling and visualizing data.
    
    Parameters:
        data: The primary object ApertureData for plotting.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).
        BPM_data: Optional object BPMData.
        collimator_data: Optional object CollimatorsData.
        width: Width of the plot. Default is 1600.
        height: Height of the plot. Default is 600.
        additional_traces: List of additional traces to add to the plot.
    """

    # Set global variables
    global knob_dropdown, add_button, remove_button, apply_button, graph_container, knob_box
    global cycle_button, cycle_input, date_picker, time_input, load_BPMs_button, load_cols_button, envelope_button, envelope_input
    global values, selected_knobs, knob_widgets, plane_button, plane_dropdown
    global global_data, global_plane, global_BPM_data, global_collimator_data
    global global_width, global_height, global_additional_traces

    # Set the arguments as global
    global_data = data
    global_width = width
    global_height = height
    global_additional_traces = additional_traces

    # Dictionaries and list to store selected knobs, corresponding widgets, and current widget values
    selected_knobs = []
    knob_widgets = {}
    values = {}

    # Define and configure widgets
    add_button, remove_button, apply_button, cycle_button, reset_button, envelope_button, plane_button = define_buttons()
    knob_dropdown, knob_box, cycle_input, envelope_input, graph_container, plane_dropdown = define_widgets()

    global_plane = plane_dropdown.value

    # Set up event handlers
    add_button.on_click(on_add_button_clicked)
    remove_button.on_click(on_remove_button_clicked)
    apply_button.on_click(on_apply_button_clicked)
    cycle_button.on_click(on_cycle_button_clicked)
    reset_button.on_click(on_reset_button_clicked)
    envelope_button.on_click(on_envelope_button_clicked)
    plane_button.on_click(on_plane_button_clicked)

    # Set the order of some of the controls
    knob_selection_controls = [knob_dropdown, add_button, remove_button, apply_button, reset_button]
    cycle_controls = [cycle_input, cycle_button]
    envelope_controls = [envelope_input, envelope_button]
    plane_controls = [plane_dropdown, plane_button]

    # Create an empty list for timber controls
    timber_controls = []

    # Only add timber buttons if spark given as an argument
    if spark:

        global_collimator_data, global_BPM_data = initialise_timber_data(spark)

        load_BPMs_button = Button(description="Load BPMs", style=widgets.ButtonStyle(button_color='pink'))
        load_BPMs_button.on_click(on_load_BPMs_button_clicked)
        timber_controls.append(load_BPMs_button)

        load_cols_button = Button(description="Load collimators", style=widgets.ButtonStyle(button_color='pink'))
        load_cols_button.on_click(on_load_cols_button_clicked)
        timber_controls.append(load_cols_button)

        # Time selection widgets
        date_picker, time_input = define_time_widgets()
        time_controls = [date_picker, time_input]

        # Define layout depending if timber buttons present or not
        timber_row_controls = time_controls+timber_controls
    
    else: global_BPM_data, global_collimator_data, timber_row_controls = None, None, None

    first_row_controls = knob_selection_controls
    second_row_controls = cycle_controls+envelope_controls+plane_controls

    # Put all the widgets together into a nice layout
    everything = define_widget_layout(first_row_controls, second_row_controls, timber_row_controls)

    # Display the widgets and the graph
    display(everything)

    # Plot all traces
    update_graph()

def initialise_timber_data(spark):

    collimators_object = CollimatorsData(spark)
    BPM_object = BPMData(spark)

    return collimators_object, BPM_object

def define_widget_layout(first_row_controls: List[widgets.Widget], 
                         second_row_controls: List[widgets.Widget],
                         timber_row_controls: Optional[List[widgets.Widget]] = None) -> VBox:
    """
    Define and arrange the layout of the widgets.

    Parameters:
        first_row_controls: List of widgets to be arranged in the first row.
        second_row_controls: List of widgets to be arranged in the second row.

    Returns:
        VBox: A VBox containing all widget layouts.
    """

    # Create layout for the first row of controls
    first_row_layout = HBox(
        first_row_controls,
        layout=Layout(
            justify_content='space-around', # Distribute space evenly
            align_items='center',           # Center align all items
            width='100%',                   # Full width of the container
            padding='10px',                 # Add padding around controls
            border='solid 2px #ccc'))       # Border around the HBox

    # Create layout for the second row of controls
    second_row_layout = HBox(
        second_row_controls,
        layout=Layout(
            justify_content='space-around', # Distribute space evenly
            align_items='center',           # Center align all items
            width='100%',                   # Full width of the container
            padding='10px',                 # Add padding around controls
            border='solid 2px #ccc'))       # Border around the HBox

    # Combine both rows, knob box, and graph container into a VBox layout
    if timber_row_controls: 
        # Create layout for the timber row of controls
        timber_row_layout = HBox(
            timber_row_controls,
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox
        
        full_column = [first_row_layout, knob_box, second_row_layout, timber_row_layout, graph_container]

    else: full_column = [first_row_layout, knob_box, second_row_layout, graph_container]

    full_layout = VBox(
        full_column,
        layout=Layout(
            justify_content='center',       # Center align the VBox content horizontally
            align_items='center',           # Center align all items vertically
            width='80%',                    # Limit width to 80% of the page
            margin='0 auto',                # Center the VBox horizontally
            padding='20px',                 # Add p0dding around the whole container
            border='solid 2px #ddd'))       # Border around the VBox

    return full_layout

def define_time_widgets() -> Tuple[DatePicker, Text]:
    """
    Create and configure date and time input widgets.

    Returns:
        Tuple[DatePicker, Text, List[DatePicker, Text]]: A tuple containing:
            - DatePicker widget for selecting the date.
            - Text widget for entering the time.
            - A list containing both widgets.
    """

    # Create date and time input widgets
    date_picker = DatePicker(
            description='Select Date:',
            style={'description_width': 'initial'}, # Ensures the description width fits the content
            layout=Layout(width='300px'))           # Sets the width of the widget
    
    time_input = Text(
            description='Enter Time (HH:MM:SS):',
            placeholder='10:53:15',                 # Provides a placeholder text for the expected format
            style={'description_width': 'initial'}, # Ensures the description width fits the content
            layout=Layout(width='300px'))           # Sets the width of the widget

    return date_picker, time_input

def define_buttons()-> Tuple[Button, Button, Button, Button, Button, Button]:
    """
    Create and configure various control buttons for the interface.

    Returns:
        Tuple[Button, Button, Button, Button, Button, Button]: A tuple containing:
            - Add button
            - Remove button
            - Apply button
            - Cycle button
            - Reset knobs button
            - Envelope button
    """

    # Button to add selection
    add_button = Button(description="Add", style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)'))
    # Button to remove selection
    remove_button = Button(description="Remove", style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'))
    # Button to apply selection and update graph
    apply_button = Button(description="Apply", style=widgets.ButtonStyle(button_color='pink'))
    # Button to shift the graph
    cycle_button = Button(description="Cycle", style=widgets.ButtonStyle(button_color='pink'))
    # Button to reset knobs    
    reset_button = Button(description="Reset knobs", style=widgets.ButtonStyle(button_color='rgb(255, 242, 174)'))
    # Button to change envelope size
    envelope_button = Button(description="Apply", style=widgets.ButtonStyle(button_color='pink'))
    # Button to change between planes
    plane_button = Button(description="Switch", style=widgets.ButtonStyle(button_color='pink'))

    return add_button, remove_button, apply_button, cycle_button, reset_button, envelope_button, plane_button

def define_widgets() -> Tuple[Dropdown, VBox, Text, FloatText, VBox]:
    """
    Define and configure widgets for knob selection, cycle start, envelope size, and graph container.

    Returns:
        Tuple[Dropdown, VBox, Text, FloatText, VBox]: A tuple containing:
            - Dropdown for knob selection
            - VBox container for selected knobs
            - Text widget for cycle start input
            - FloatText widget for envelope size input
            - VBox container for the graph
    """
    # Create a dropdown to select a knob
    knob_dropdown = Dropdown(
        options=global_data.knobs['knob'].to_list(),
        description='Select knob:',
        disabled=False)
    
    # Create a box to store selected knobs
    knob_box = VBox(layout=Layout(
        justify_content='center',
        align_items='center',
        width='100%',
        padding='10px',
        border='solid 2px #eee'))

    # Create a text widget to specify cycle start
    cycle_input = Text(
        value='',                               # Initial value (empty string)
        description='First element:',           # Label for the widget
        placeholder='e. g. ip3',                # Placeholder text when the input is empty
        style={'description_width': 'initial'}, # Adjust the width of the description label
        layout=Layout(width='300px'))           # Set the width of the widget

    # Create a float widget to specify envelope size
    envelope_input = FloatText(
            value=global_data.n,                    # Initial value (empty string)
            description='Envelope size [σ]:',    # Label for the widget 
            style={'description_width': 'initial'}, # Adjust the width of the description label
            layout=Layout(width='300px'))           # Set the width of the widget
        
    # Create an empty VBox container for the graph
    graph_container = VBox(layout=Layout(
        justify_content='center',
        align_items='center',
        width='100%',
        padding='10px',
        border='solid 2px #eee'))
    
    # Create a dropdown to select a plane
    plane_dropdown = Dropdown(
        options=['horizontal', 'vertical'],
        description='Select plane:',
        disabled=False)
    
    return knob_dropdown, knob_box, cycle_input, envelope_input, graph_container, plane_dropdown

def on_plane_button_clicked(b):

    selected_plane = plane_dropdown.value

    print('Switching between planes...')
    global global_plane
    global_plane = selected_plane

    update_graph()

def on_envelope_button_clicked(b):
    """
    Handle the event when the envelope button is clicked. Update the global envelope size and refresh the graph.
    """
    # Get the selected envelope size from the widget
    selected_size = envelope_input.value
    print('Setting new envelope size...')
    # Update global data with the new envelope size
    global_data.envelope(selected_size)
    # Update the graph with the new envelope size
    update_graph()

def on_load_BPMs_button_clicked(b):
    """
    Handle the event when the Load BPMs button is clicked. Parse the date and time inputs, and load BPM data.
    """
    # Retrieve the selected date and time from the widgets
    selected_date = date_picker.value
    selected_time_str = time_input.value

    if selected_date and selected_time_str:
        try:
            # Parse the time string to extract hours, minutes, seconds
            selected_time = datetime.strptime(selected_time_str, '%H:%M:%S').time()
            
            # Create a datetime object
            combined_datetime = datetime(
                selected_date.year, selected_date.month, selected_date.day,
                selected_time.hour, selected_time.minute, selected_time.second)
            
            # Load BPM data for the specified datetime
            global_BPM_data.load_data(combined_datetime)

            # Update the graph with the new BPM data
            update_graph()
        except ValueError:
            print("Invalid time format. Please use HH:MM:SS.")
    else:
        print("Please select both a date and a time.")

def on_load_cols_button_clicked(b):
    """
    Handle the event when the Load Collimators button is clicked. 
    Parse the date and time inputs, load collimator data, and update the graph.
    """
    # Retrieve the selected date and time from the widgets
    selected_date = date_picker.value
    selected_time_str = time_input.value

    if selected_date and selected_time_str:
        try:
            # Parse the time string to extract hours, minutes, seconds
            selected_time = datetime.strptime(selected_time_str, '%H:%M:%S').time()
            
            # Create a datetime object
            combined_datetime = datetime(
                selected_date.year, selected_date.month, selected_date.day,
                selected_time.hour, selected_time.minute, selected_time.second)

            # Load collimator data
            global_collimator_data.load_data(combined_datetime)

            # Update the graph with the new collimator data
            update_graph()

        except ValueError:
            print("Invalid time format. Please use HH:MM:SS.")
    else:
        print("Please select both a date and a time.")

def on_reset_button_clicked(b):
    """
    Handle the event when the Reset button is clicked. 
    Remove all selected knobs, reset their values, and update the display and graph.
    """
    # Remove selected knobs and their associated data
    for knob in selected_knobs[:]:
        selected_knobs.remove(knob)
        del values[knob]  # Remove the value of the knob
        del knob_widgets[knob]  # Remove the widget
        
    # Reset knobs to their initial values and re-twiss
    global_data.reset_knobs()

    # Update selected knobs and display value
    update_knob_box()

    # Update the figure
    update_graph()

def on_cycle_button_clicked(b):
    """
    Handle the event when the Cycle button is clicked. 
    Cycle all the data to set a new zero point and update the graph.
    """
    # Retrieve the selected element from the widget
    first_element = cycle_input.value
    print(f'Setting {first_element} as the first element...')
    # Cycle
    global_data.cycle(first_element)
    
    # Update the figure
    update_graph()

def on_add_button_clicked(b):
    """
    Handle the event when the Add button is clicked. 
    Add a new knob to the selected list and create a widget for it.
    """
    # Knob selected in the dropdown menu
    knob = knob_dropdown.value
    # If the knob is not already in the selected list, add it
    if knob and knob not in selected_knobs:
        selected_knobs.append(knob)
        values[knob] = 1.0  # Initialize knob for new value

        # Create a new FloatText widget for the selected knob
        knob_widget = FloatText(
            value=global_data.knobs[global_data.knobs['knob']==knob]['current value'],
            description=f'{knob}',
            disabled=False
        )
        # Add the widget to the knob widgets list
        knob_widgets[knob] = knob_widget

        # Update selected knobs and display value
        update_knob_box()

def on_remove_button_clicked(b):
    """
    Handle the event when the Remove button is clicked. 
    Remove the selected knob from the list and delete its widget.
    """
    # Knob selected in the dropdown menu
    knob = knob_dropdown.value
    # If the knob is in the selected list, remove it
    if knob in selected_knobs:
        selected_knobs.remove(knob)
        del values[knob]  # Remove the value of the knob
        if knob in knob_widgets:
            del knob_widgets[knob]  # Remove the widget
        
        # Update selected knobs and display value
        update_knob_box()
        
def on_apply_button_clicked(b):
    """
    Handle the event when the Apply button is clicked. 
    Apply changes to the knobs and update the graph.
    """
    # Update knobs dictionary based on current values in the knob widgets
    for knob, widget in knob_widgets.items():
        global_data.change_knob(knob, widget.value)
    
    # Re-twiss
    global_data.twiss()
    
    # Update the figure
    update_graph()
        
def create_figure() -> Tuple[go.Figure, int, int, np.ndarray, np.ndarray]:
    """
    Create and return a Plotly figure with multiple traces based on the global data.

    Returns:
        fig: The constructed Plotly figure.
        row: The row index for plotting additional traces.
        col: The column index for plotting additional traces.
        visibility_b1: Array indicating visibility of elements for beam 1.
        visibility_b2: Array indicating visibility of elements for beam 2.
    """

    # These correspond to swapping between visibilities of aperture/collimators for beam 1 and 2
    visibility_b1 = np.array([], dtype=bool)
    visibility_b2 = np.array([], dtype=bool)

    # If thick machine elements are loaded
    if hasattr(global_data, 'elements'):

        # Create 2 subplots: for elements and the plot
        fig = make_subplots(rows=2, cols=1, row_heights=[0.2, 0.8], shared_xaxes=True)
        # Update layout of the upper plot (machine components plot)
        fig.update_yaxes(range=[-1, 1], showticklabels=False, showline=False, row=1, col=1)
        fig.update_xaxes(showticklabels=False, showline=False, row=1, col=1)
        elements_visibility, elements = plot_machine_components(global_data)

        for i in elements:
            fig.add_trace(i, row=1, col=1)

        # Row and col for other traces
        row, col = 2, 1

        # Always show machine components
        visibility_b1 = np.append(visibility_b1, elements_visibility)
        visibility_b2 = np.append(visibility_b2, elements_visibility)

    # If thick machine elements are not loaded
    else:
        # Create only one plot
        fig = make_subplots(rows=1, cols=1)
        # Row and col for other traces
        row, col = 1, 1

    # If any additional traces were given as an argument
    if global_additional_traces:
        # TODO: handle if not a list
        for i in global_additional_traces:
            fig.add_trace(i, row=row, col=col)
            visibility_b1 = np.append(visibility_b1, True)
            visibility_b2 = np.append(visibility_b2, True)

    # If there is aperture data
    if hasattr(global_data, 'aper_b1'):
        aper_visibility, apertures = plot_aperture(global_data, global_plane)
        for i in apertures:
            fig.add_trace(i, row=row, col=col)

        # Show only aperture for one beam
        visibility_b1 = np.append(visibility_b1, aper_visibility)
        visibility_b2 = np.append(visibility_b2, np.logical_not(aper_visibility))

    # If there are collimators loaded from yaml file
    if hasattr(global_data, 'colx_b1'):
        collimator_visibility, collimator = plot_collimators_from_yaml(global_data, global_plane)
        for i in collimator:
            fig.add_trace(i, row=row, col=col)

        # Show only collimators for one beam
        visibility_b1 = np.append(visibility_b1, collimator_visibility)
        visibility_b2 = np.append(visibility_b2, np.logical_not(collimator_visibility))

    # If collimators were loaded from timber
    if global_collimator_data and hasattr(global_collimator_data, 'colx_b1'):
        collimator_visibility, collimator = plot_collimators_from_timber(global_collimator_data, global_data, global_plane)
        for i in collimator:
            fig.add_trace(i, row=row, col=col)

        # Show only collimators for one beam
        visibility_b1 = np.append(visibility_b1, collimator_visibility)
        visibility_b2 = np.append(visibility_b2, np.logical_not(collimator_visibility))

    # Add beam positions from twiss data
    beam_visibility, beams = plot_beam_positions(global_data, global_plane)
    for i in beams:
        fig.add_trace(i, row=row, col=col)

    # Always show both beams
    visibility_b1 = np.append(visibility_b1, beam_visibility)
    visibility_b2 = np.append(visibility_b2, beam_visibility)

    # Add nominal beam positions
    nominal_beam_visibility, nominal_beams = plot_nominal_beam_positions(global_data, global_plane)
    for i in nominal_beams:
        fig.add_trace(i, row=row, col=col)

    # Always show both beams
    visibility_b1 = np.append(visibility_b1, nominal_beam_visibility)
    visibility_b2 = np.append(visibility_b2, nominal_beam_visibility)

    # Add envelopes
    envelope_visibility, envelope = plot_envelopes(global_data, global_plane)
    for i in envelope:
        fig.add_trace(i, row=row, col=col)
    
    # Always show both envelopes
    visibility_b1 = np.append(visibility_b1, envelope_visibility)
    visibility_b2 = np.append(visibility_b2, envelope_visibility)

    # If BPM data was loaded from timber
    if global_BPM_data and hasattr(global_BPM_data, 'data'):
        BPM_visibility, BPM_traces = plot_BPM_data(global_BPM_data, global_plane, global_data)
        for i in BPM_traces:
            fig.add_trace(i, row=row, col=col)

        # Always show BPM data for both beams
        visibility_b1 = np.append(visibility_b1, BPM_visibility)
        visibility_b2 = np.append(visibility_b2, BPM_visibility)

    return fig, row, col, visibility_b1, visibility_b2

def update_knob_box():
    """
    Updates the layout of the knob_box with current knob widgets.
    """
    # Group the widgets into sets of three per row
    rows = []
    for i in range(0, len(selected_knobs), 3):
        row = HBox([knob_widgets[knob] for knob in selected_knobs[i:i+3]],
                   layout=Layout(align_items='flex-start'))
        rows.append(row)

    # Update the knob_box with the new rows
    knob_box.children = rows
    
def update_graph():
    """
    Updates the graph displayed in the graph_container.
    """
    # Create figure
    fig, row, col, visibility_b1, visibility_b2 = create_figure()
    # Update figure layout
    update_layout(fig, row, col, visibility_b1, visibility_b2)
    
    # Change to a widget
    fig_widget = go.FigureWidget(fig)
    # Put the figure in the graph container
    graph_container.children = [fig_widget]

def update_layout(fig: go.Figure, 
                  row: int, 
                  col: int, 
                  visibility_b1: np.ndarray, 
                  visibility_b2: np.ndarray):
    """
    Updates the layout of the given figure with appropriate settings and visibility toggles.

    Parameters:
        fig: The Plotly figure to be updated.
        row: The row index where the main plot is located.
        col: The column index where the main plot is located.
        visibility_b1: Visibility settings for beam 1.
        visibility_b2: Visibility settings for beam 2.
    """
    # Set layout
    fig.update_layout(height=global_height, width=global_width, showlegend=False, xaxis=dict(tickformat=','), yaxis=dict(tickformat=','), plot_bgcolor='white')

    # Change x limits and labels
    fig.update_xaxes(title_text="s [m]", row=row, col=col)

    # Change y limits and labels
    if global_plane == 'horizontal': title = 'x [m]'
    elif global_plane == 'vertical': title = 'y [m]'

    fig.update_yaxes(title_text=title, range = [-0.05, 0.05], row=row, col=col)

    # If aperture/collimators were loaded add buttons to switch between beam 1 and beam 2
    if hasattr(global_data, 'aper_b1') or hasattr(global_data, 'colx_b1') or global_collimator_data:

        fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                xanchor='left',
                y=1.2,
                buttons=list([
                    dict(label="Beam 1 aperture/collimation",
                        method="update",
                        args=[{"visible": visibility_b1}]),
                    dict(label="Beam 2 aperture/collimation",
                        method="update",
                        args=[{"visible": visibility_b2}])]))])