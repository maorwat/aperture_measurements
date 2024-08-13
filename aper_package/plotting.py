import numpy as np
import pandas as pd
from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ipywidgets import widgets, VBox, HBox, Button, Layout, FloatText, DatePicker, Text, FileUpload
from IPython.display import display

from aper_package.figure_data import *

def plot(data, plane, BPM_data = None, collimator_data = None, width=1600, height=600, additional_traces=None):

    global knob_dropdown, add_button, remove_button, apply_button, graph_container, knob_box
    global cycle_button, cycle_input, date_picker, time_input, load_BPMs_button, load_cols_button, envelope_button, envelope_input
    global values, selected_knobs, knob_widgets
    global global_data, global_plane, global_BPM_data, global_collimator_data
    global global_width, global_height, global_additional_traces

    # Set the arguments as global
    global_data = data
    global_plane = plane

    global_BPM_data = BPM_data
    global_collimator_data = collimator_data

    global_width = width
    global_height = height
    global_additional_traces = additional_traces

    # Dictionaries and list to store selected knobs and corresponding widgets and current widget values
    selected_knobs = []
    knob_widgets = {}
    values = {}

    # Define widgets
    add_button, remove_button, apply_button, cycle_button, reset_button, envelope_button = define_buttons()
    knob_dropdown, knob_box, cycle_input, envelope_input, graph_container = define_widgets()

    # Set up event handlers
    add_button.on_click(on_add_button_clicked)
    remove_button.on_click(on_remove_button_clicked)
    apply_button.on_click(on_apply_button_clicked)
    cycle_button.on_click(on_cycle_button_clicked)
    reset_button.on_click(on_reset_button_clicked)
    envelope_button.on_click(on_envelope_button_clicked)

    # Set the order of some of the controls
    knob_selection_controls = [knob_dropdown, add_button, remove_button, apply_button, reset_button]
    cycle_controls = [cycle_input, cycle_button]
    envelope_controls = [envelope_input, envelope_button]

    # Create an empty list for timber controls
    timber_controls = []
    # Only add timber buttons if given as an argument
    if BPM_data or collimator_data:

        if BPM_data:
            load_BPMs_button = Button(description="Load BPMs", style=widgets.ButtonStyle(button_color='pink'))
            load_BPMs_button.on_click(on_load_BPMs_button_clicked)
            timber_controls.append(load_BPMs_button)
        if collimator_data:
            load_cols_button = Button(description="Load collimators", style=widgets.ButtonStyle(button_color='pink'))
            load_cols_button.on_click(on_load_cols_button_clicked)
            timber_controls.append(load_cols_button)

        # Time selection widgets
        date_picker, time_input, time_controls = define_time_widgets()

        # Define layout depending if timber buttons present or not
        first_row_controls = cycle_controls+knob_selection_controls
        second_row_controls = envelope_controls+time_controls+timber_controls
    else:
        first_row_controls = knob_selection_controls
        second_row_controls = cycle_controls+envelope_controls

    # Put all the widgets together into a nice layout
    everything = define_widget_layout(first_row_controls, second_row_controls)

    # Display the widgets and the graph
    display(everything)

    # Plot all traces
    update_graph()

def define_widget_layout(first_row_controls, second_row_controls):

        # Arrange knob dropdown and buttons in a horizontal layout
    controls = HBox(
        first_row_controls,
        layout=Layout(
            justify_content='space-around',  # Distribute space evenly
            align_items='center',            # Center align all items
            width='100%',
            padding='10px',                  # Add padding around controls
            border='solid 2px #ccc'))

    # Arrange knob dropdown and buttons in a horizontal layout
    more_controls = HBox(
        second_row_controls,
        layout=Layout(
            justify_content='space-around',  # Distribute space evenly
            align_items='center',            # Center align all items
            width='100%',
            padding='10px',                  # Add padding around controls
            border='solid 2px #ccc'))

    # Combine everything into the main VBox layout
    everything = VBox(
        [controls, knob_box, more_controls, graph_container],
        layout=Layout(
            justify_content='center',
            align_items='center',
            width='80%',                     # Limit width to 80% of the page
            margin='0 auto',                 # Center the VBox horizontally
            padding='20px',                  # Add p0dding around the whole container
            border='solid 2px #ddd'))

    return everything

def define_time_widgets():

    # Create date and time input widgets
    date_picker = DatePicker(
            description='Select Date:',
            style={'description_width': 'initial'},
            layout=Layout(width='300px'))
    
    time_input = Text(
            description='Enter Time (HH:MM:SS):',
            placeholder='10:53:15',
            style={'description_width': 'initial'},
            layout=Layout(width='300px'))
    
    time_controls = [date_picker, time_input]

    return date_picker, time_input, time_controls

def define_buttons():

    # Button to add selection
    add_button = Button(description="Add", style=widgets.ButtonStyle(button_color='rgb(166, 216, 84)'))
    # Button to remove selection
    remove_button = Button(description="Remove", style=widgets.ButtonStyle(button_color='rgb(237, 100, 90)'))
    # Button to apply selection and update graph
    apply_button = Button(description="Apply", style=widgets.ButtonStyle(button_color='lightblue'))
    # Button to shift the graph
    cycle_button = Button(description="Cycle", style=widgets.ButtonStyle(button_color='pink'))
    # Button to reset knobs    
    reset_button = Button(description="Reset knobs", style=widgets.ButtonStyle(button_color='rgb(255, 242, 174)'))
    # Button to change envelope size
    envelope_button = Button(description="Apply", style=widgets.ButtonStyle(button_color='pink'))

    return add_button, remove_button, apply_button, cycle_button, reset_button, envelope_button

def define_widgets():

    # Create a dropdown to select a knob
    knob_dropdown = widgets.Dropdown(
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
    cycle_input = widgets.Text(
        value='',                  # Initial value (empty string)
        description='First element:',      # Label for the widget
        placeholder='e. g. ip3',  # Placeholder text when the input is empty
        style={'description_width': 'initial'},  # Adjust the width of the description label
        layout=widgets.Layout(width='300px'))  # Set the width of the widget

    # Create a float widget to specify envelope size
    envelope_input = widgets.FloatText(
            value=global_data.n,                  # Initial value (empty string)
            description='Size of envelope [σ]:',      # Label for the widget 
            style={'description_width': 'initial'},  # Adjust the width of the description label
            layout=widgets.Layout(width='300px'))  # Set the width of the widget
        
    # Create an empty VBox container for the graph
    graph_container = VBox(layout=Layout(
        justify_content='center',
        align_items='center',
        width='100%',
        padding='10px',
        border='solid 2px #eee'))
    
    return knob_dropdown, knob_box, cycle_input, envelope_input, graph_container

def on_envelope_button_clicked(b):

    selected_size = envelope_input.value

    global_data.envelope(selected_size)

    # Update the figure
    update_graph()

def on_load_BPMs_button_clicked(b):

    selected_date = date_picker.value
    selected_time_str = time_input.value

    if selected_date and selected_time_str:
        try:
            # Parse the time string to extract hours, minutes, seconds
            selected_time = datetime.strptime(selected_time_str, '%H:%M:%S').time()
            
            # Create a datetime object
            combined_datetime = datetime(
                selected_date.year, selected_date.month, selected_date.day,
                selected_time.hour, selected_time.minute, selected_time.second
            )
        except ValueError:
            print("Invalid time format. Please use HH:MM:SS.")
    else:
        print("Please select both a date and a time.")

    # Load BPM data
    global_BPM_data.load_data(combined_datetime)

    # Update the figure
    update_graph()

def on_load_cols_button_clicked(b):

    selected_date = date_picker.value
    selected_time_str = time_input.value

    if selected_date and selected_time_str:
        try:
            # Parse the time string to extract hours, minutes, seconds
            selected_time = datetime.strptime(selected_time_str, '%H:%M:%S').time()
            
            # Create a datetime object
            combined_datetime = datetime(
                selected_date.year, selected_date.month, selected_date.day,
                selected_time.hour, selected_time.minute, selected_time.second
            )
        except ValueError:
            print("Invalid time format. Please use HH:MM:SS.")
    else:
        print("Please select both a date and a time.")

    # Load BPM data
    global_collimator_data.load_data(combined_datetime)

    # Update the figure
    update_graph()

def on_reset_button_clicked(b):

    for knob in selected_knobs[:]:
        selected_knobs.remove(knob)
        del values[knob]  # Remove the value of the knob
        del knob_widgets[knob]  # Remove the widget
        
    # Re-twiss
    global_data.reset_knobs()

    # Update selected knobs and display value
    update_knob_box()

    # Update the figure
    update_graph()

def on_cycle_button_clicked(b):

    first_element = cycle_input.value

    # Re-twiss
    global_data.cycle(first_element)
    
    # Update the figure
    update_graph()

def on_add_button_clicked(b):

    """
    Function to handle adding a knob
    """
    # Knob selected in the dropdown menu
    knob = knob_dropdown.value
    # If the knob is not already in the selected list, add it
    if knob and knob not in selected_knobs:
        selected_knobs.append(knob)
        values[knob] = 1.0  # Initialize knob for new value

        # Create a new FloatText widget for the selected knob
        knob_widget = FloatText(
            value=global_data.knobs[global_data.knobs['knob']==knob]['initial value'],
            description=f'{knob}',
            disabled=False,
            layout=Layout(width='270px')
        )
        # Add the widget to the knob widgets list
        knob_widgets[knob] = knob_widget

        # Update selected knobs and display value
        update_knob_box()

def on_remove_button_clicked(b):
    """
    Function to handle removing a knob
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
    Function to apply changes and update the graph
    """
    # Update knobs dictionary based on current values in the knob widgets
    for knob, widget in knob_widgets.items():
        global_data.change_knob(knob, widget.value)
    
    # Re-twiss
    global_data.twiss()
    
    # Update the figure
    update_graph()
        
def create_figure():

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
    Function to update the knob_box layout
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
    Function to update the graph
    """
    # Create figure
    fig, row, col, visibility_b1, visibility_b2 = create_figure()
    # Update figure layout
    update_layout(fig, row, col, visibility_b1, visibility_b2)
    
    # Change to a widget
    fig_widget = go.FigureWidget(fig)
    # Put the figure in the graph container
    graph_container.children = [fig_widget]

def update_layout(fig, row, col, visibility_b1, visibility_b2):

    # Set layout
    fig.update_layout(height=global_height, width=global_width, showlegend=False, xaxis=dict(tickformat=','), yaxis=dict(tickformat=','), plot_bgcolor='white')

    # Change x limits and labels
    fig.update_xaxes(title_text="s [m]", row=row, col=col)

    # Change y limits and labels
    if global_plane == 'h': title = 'x [m]'
    elif global_plane == 'v': title = 'y [m]'
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