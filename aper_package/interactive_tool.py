import numpy as np
import os
import pandas as pd
from datetime import datetime
from typing import Optional, List, Tuple, Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ipywidgets import widgets, VBox, HBox, Button, Layout, FloatText, DatePicker, Text, Dropdown
from IPython.display import display, clear_output
from ipyfilechooser import FileChooser

from aper_package.figure_data import *
from aper_package.timber_data import BPMData
from aper_package.timber_data import CollimatorsData
from aper_package.aperture_data import ApertureData

class InteractiveTool():
    
    def __init__(self,
                 line_b1_path: Optional[str] = None,
                 line_b2_path: Optional[str] = None,
                 initial_path: Optional[str] = '/eos/project-c/collimation-team/machine_configurations/',
                 spark: Optional[Any] = None, 
                 plane: Optional[str] = 'horizontal',
                 additional_traces: Optional[list] = None):
        
        """
        Create and display an interactive plot with widgets for controlling and visualizing data.

        Parameters:
            line_b1:
            initial_path: initial path for FileChoosers
            spark: SWAN spark session
            additional_traces: List of additional traces to add to the plot.
        """
        # If line was given load
        if line_b1_path:
            if not line_b2_path and os.path.exists(str(line_b1_path).replace('b1', 'b2')): self.aperture_data = ApertureData(line_b1_path)
            elif not line_b2_path and not os.path.exists(str(line_b1_path).replace('b1', 'b2')): print('Path for beam 2 not found. You can either provide it as an argument line_b2_path\nor load interactively from the graph')

        self.additional_traces = additional_traces
        self.initial_path = initial_path
        # By default show horizontal plane first
        self.plane = plane
        self.spark = spark
        # Create and configure widgets
        self.initialise_knob_controls()
        self.create_buttons()
        self.create_widgets()
        self.create_file_choosers()
        # Set-up corresponding evcent handlers
        self.setup_event_handlers()

        # Put all the widgets together into a nice layout
        self.group_controls_into_rows()
        self.define_widget_layout()

    def initialise_knob_controls(self):

        # Dictionaries and list to store selected knobs, corresponding widgets, and current widget values
        self.selected_knobs = []
        self.knob_widgets = {}
        self.values = {}

        if hasattr(self, 'aperture_data'):
            # Create a dropdown to select a knob
            self.knob_dropdown = Dropdown(
                options=self.aperture_data.knobs['knob'].to_list(),
                description='Select knob:',
                disabled=False)
        else: 
            # Create a dropdown to select a knob
            self.knob_dropdown = Dropdown(
                options=[],
                description='Select knob:',
                disabled=False)
            
        # Create a box to store selected knobs
        self.knob_box = VBox(layout=Layout(
            justify_content='center',
            align_items='center',
            width='100%',
            padding='10px',
            border='solid 2px #eee'))
        
    def create_buttons(self):
        """
        Create and configure various control buttons for the interface.
        """

        # Button to add selection
        self.add_button = Button(description="Add", style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)'), tooltip='Add selected knob to be able to change its value.')
        # Button to remove selection
        self.remove_button = Button(description="Remove", style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'), tooltip='Remove selected knob from the list below.')
        # Button to apply selection and update graph
        self.apply_button = Button(description="Apply", style=widgets.ButtonStyle(button_color='pink'), tooltip='Re-twiss the data with knob values given below.')
        # Button to shift the graph
        self.cycle_button = Button(description="Cycle", style=widgets.ButtonStyle(button_color='pink'), tooltip='Shift the figure to start at a different element for better visualisation.')
        # Button to reset knobs    
        self.reset_button = Button(description="Reset knobs", style=widgets.ButtonStyle(button_color='rgb(255, 242, 174)'), tooltip='Reset all the knobs to their nominal values.')
        # Button to change envelope size# Create a dropdown to select a knob
        self.envelope_button = Button(description="Apply", style=widgets.ButtonStyle(button_color='pink'), tooltip='Change the size of beam envelope (in units of normalized beam size).')
        self.plane_button = Button(description="Switch", style=widgets.ButtonStyle(button_color='pink'), tooltip='Switch between horizontal and vertical planes.')

    def create_widgets(self):
        """
        Define and configure widgets for knob selection, cycle start, envelope size, and graph container.
        """

        # Create a text widget to specify cycle start
        self.cycle_input = Text(
            value='',                               # Initial value (empty string)
            description='First element:',           # Label for the widget
            placeholder='e. g. ip3',                # Placeholder text when the input is empty
            style={'description_width': 'initial'}, # Adjust the width of the description label
            layout=Layout(width='300px'))           # Set the width of the widget

        # Create a float widget to specify envelope size
        if hasattr(self, 'aperture_data'): n = self.aperture_data.n
        else: n = 0

        self.envelope_input = FloatText(
                value=0,                    # Initial value (empty string)
                description='Envelope size [σ]:',    # Label for the widget 
                style={'description_width': 'initial'}, # Adjust the width of the description label
                layout=Layout(width='300px'))           # Set the width of the widget

        # Create an empty VBox container for the graph
        self.graph_container = VBox(layout=Layout(
            justify_content='center',
            align_items='center',
            width='100%',
            padding='10px',
            border='solid 2px #eee'))

        # Create a dropdown to select a plane
        self.plane_dropdown = Dropdown(
            options=['horizontal', 'vertical'],
            description='Select plane:',
            disabled=False)
        
    def create_file_choosers(self):

        # Create filechoosers
        self.file_chooser_line = FileChooser(self.initial_path)
        self.file_chooser_aperture = FileChooser(self.initial_path)
        self.file_chooser_optics = FileChooser(self.initial_path)
        # Corresponding load buttons
        self.load_line_button = Button(description="Load line", style=widgets.ButtonStyle(button_color='pink'), tooltip='Load a line from b1.json file. The path for b2.json\nwill be generated automatically by replacing b1 with b2.')
        self.load_aperture_button = Button(description="Load aperture", style=widgets.ButtonStyle(button_color='pink'), tooltip='Load aperture data from all_optics_B1.tfs file.\nThe path for B4.tfs will be generated automatically by replacing B1 with B4.')
        self.load_optics_button = Button(description="Load optics", style=widgets.ButtonStyle(button_color='pink'), tooltip='Load MADX_thick all_optics_B1.tfs file to show optics elements above the figure.')   

    def setup_event_handlers(self):
        
        self.add_button.on_click(self.on_add_button_clicked)
        self.remove_button.on_click(self.on_remove_button_clicked)
        self.apply_button.on_click(self.on_apply_button_clicked)
        self.cycle_button.on_click(self.on_cycle_button_clicked)
        self.reset_button.on_click(self.on_reset_button_clicked)
        self.envelope_button.on_click(self.on_envelope_button_clicked)
        self.plane_button.on_click(self.on_plane_button_clicked)
        self.load_line_button.on_click(self.on_load_line_button_clicked)
        self.load_aperture_button.on_click(self.on_load_aperture_button_clicked)
        self.load_optics_button.on_click(self.on_load_optics_button_clicked)

    def group_controls_into_rows(self):

        # Group controls together
        self.file_chooser_controls = [self.file_chooser_line, self.load_line_button, self.file_chooser_aperture, self.load_aperture_button, self.file_chooser_optics, self.load_optics_button]
        self.first_row_controls = [self.knob_dropdown, self.add_button, self.remove_button, self.apply_button, self.reset_button]
        self.second_row_controls = [self.cycle_input, self.cycle_button, self.envelope_input, self.envelope_button, self.plane_dropdown, self.plane_button]
        self.widgets = self.file_chooser_controls+self.first_row_controls+self.second_row_controls+self.second_row_controls     
        self.timber_row_controls = self.initialise_timber_data() # If spark was not given this will return a None     
 
    def initialise_timber_data(self):
        
        # Only add timber buttons if spark given as an argument
        if self.spark:

            self.collimator_data = CollimatorsData(self.spark)
            self.BPM_data = BPMData(self.spark)
            
            self.load_BPMs_button = Button(description="Load BPMs", style=widgets.ButtonStyle(button_color='pink'), tooltip='Load BPM data from timber for the specified time.')
            self.load_BPMs_button.on_click(self.on_load_BPMs_button_clicked)

            self.load_cols_button = Button(description="Load collimators", style=widgets.ButtonStyle(button_color='pink'), tooltip='Load collimator data from timber for the specified time.')
            self.load_cols_button.on_click(self.on_load_cols_button_clicked)

            # Time selection widgets
            self.create_time_widgets()

            # Define layout depending if timber buttons present or not
            timber_row_controls = [self.date_picker, self.time_input, self.load_cols_button, self.load_BPMs_button]
            self.widgets += timber_row_controls

        else: self.BPM_data, self.collimator_data, timber_row_controls = None, None, None
            
        return timber_row_controls
    
    def define_widget_layout(self):
        """
        Define and arrange the layout of the widgets.

        Parameters:
            first_row_controls: List of widgets to be arranged in the first row.
            second_row_controls: List of widgets to be arranged in the second row.
        """

        # Create layout for the first row of controls
        file_chooser_layout = HBox(
            self.file_chooser_controls,
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='flex-start',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox

        # Create layout for the first row of controls
        first_row_layout = HBox(
            self.first_row_controls,
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox

        # Create layout for the second row of controls
        second_row_layout = HBox(
            self.second_row_controls,
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox

        # Combine both rows, knob box, and graph container into a VBox layout
        if self.timber_row_controls: 
            # Create layout for the timber row of controls
            timber_row_layout = HBox(
                self.timber_row_controls,
                layout=Layout(
                    justify_content='space-around', # Distribute space evenly
                    align_items='center',           # Center align all items
                    width='100%',                   # Full width of the container
                    padding='10px',                 # Add padding around controls
                    border='solid 2px #ccc'))       # Border around the HBox

            full_column = [file_chooser_layout, first_row_layout, self.knob_box, second_row_layout, timber_row_layout, self.graph_container]

        else: full_column = [file_chooser_layout, first_row_layout, self.knob_box, second_row_layout, self.graph_container]

        self.full_layout = VBox(
            full_column,
            layout=Layout(
                justify_content='center',       # Center align the VBox content horizontally
                align_items='center',           # Center align all items vertically
                width='80%',                    # Limit width to 80% of the page
                margin='0 auto',                # Center the VBox horizontally
                padding='20px',                 # Add p0dding around the whole container
                border='solid 2px #ddd'))       # Border around the VBox
        
    def on_load_line_button_clicked(self, b):

        path = self.file_chooser_line.selected
        
        if path and os.path.exists(str(path).replace('b1', 'b2')):
            # I add these akward spaced so the printing updates fully
            print('Loading new line...                                      ', end="\r")

            # Keep envelope and the first element the same
            if hasattr(self, 'aperture_data'):
                n = self.aperture_data.n
                if hasattr(self.aperture_data, 'first_element'): first_element = self.aperture_data.first_element
                else: first_element = None
            else: n, first_element = None, None

            self.aperture_data = ApertureData(path_b1 = path)

            if self.file_chooser_aperture.selected:
                print('Re-loading aperture data...                                      ', end="\r")
                self.aperture_data.load_aperture(self.file_chooser_aperture.selected)

            if self.file_chooser_optics.selected:
                print('Re-loading optics elements...                                      ', end="\r")
                self.aperture_data.load_elements(self.file_chooser_optics.selected)

            if n: self.aperture_data.envelope(n)
            if first_element: self.aperture_data.cycle(first_element)

            self.enable_widgets()
            self.update_knob_dropdown()
            self.update_graph()

        else: print('Make sure the path is selected by clicking Select button first.                                      ', end="\r")

    def on_load_aperture_button_clicked(self, b):

        path = self.file_chooser_aperture.selected

        if path:
            print('Loading new aperture data...                                      ', end="\r")
            self.aperture_data.load_aperture(path)

            self.update_graph()

        else: print('Make sure the path is selected by clicking Select button first.                                      ', end="\r")

    def on_load_optics_button_clicked(self, b):

        path = self.file_chooser_optics.selected

        if path:
            print('Loading new optics elements...                                      ', end="\r")
            self.aperture_data.load_elements(path)

            self.update_graph()
        else: print('Make sure the path is selected by clicking Select button first.                                      ', end="\r")

    def create_time_widgets(self):
        """
        Create and configure date and time input widgets.

        Returns:
            Tuple[DatePicker, Text, List[DatePicker, Text]]: A tuple containing:
                - DatePicker widget for selecting the date.
                - Text widget for entering the time.
                - A list containing both widgets.
        """

        # Create date and time input widgets
        self.date_picker = DatePicker(
                description='Select Date:',
                style={'description_width': 'initial'}, # Ensures the description width fits the content
                layout=Layout(width='300px'))           # Sets the width of the widget

        self.time_input = Text(
                description='Enter Time (HH:MM:SS):',
                placeholder='10:53:15',                 # Provides a placeholder text for the expected format
                style={'description_width': 'initial'}, # Ensures the description width fits the content
                layout=Layout(width='300px'))           # Sets the width of the widget
     
    def on_plane_button_clicked(self, b):

        selected_plane = self.plane_dropdown.value

        print('Switching between planes...                                      ', end="\r")
        self.plane = selected_plane

        self.update_graph()

    def on_envelope_button_clicked(self, b):
        """
        Handle the event when the envelope button is clicked. Update the global envelope size and refresh the graph.
        """
        # Get the selected envelope size from the widget
        selected_size = self.envelope_input.value
        print('Setting new envelope size...                                      ', end="\r")
        # Update global data with the new envelope size
        self.aperture_data.envelope(selected_size)
        # Update the graph with the new envelope size
        self.update_graph()

    def on_load_BPMs_button_clicked(self, b):
        """
        Handle the event when the Load BPMs button is clicked. 
        Parse the date and time inputs, load BPM data, and update the graph.
        """
        # Retrieve the selected date and time from the widgets
        selected_date = self.date_picker.value
        selected_time_str = self.time_input.value

        if selected_date and selected_time_str:
            try:
                # Parse the time string to extract hours, minutes, seconds
                selected_time = datetime.strptime(selected_time_str, '%H:%M:%S').time()

                # Create a datetime object
                combined_datetime = datetime(
                    selected_date.year, selected_date.month, selected_date.day,
                    selected_time.hour, selected_time.minute, selected_time.second)

                # Load BPM data for the specified datetime
                self.BPM_data.load_data(combined_datetime)

                # Update the graph with the new BPM data
                self.update_graph()
            except ValueError:
                print("Invalid time format. Please use HH:MM:SS.                                      ", end="\r")
        else:
            print("Please select both a date and a time.                                      ", end="\r")

    def on_load_cols_button_clicked(self, b):
        """
        Handle the event when the Load Collimators button is clicked. 
        Parse the date and time inputs, load collimator data, and update the graph.
        """
        # Retrieve the selected date and time from the widgets
        selected_date = self.date_picker.value
        selected_time_str = self.time_input.value

        if selected_date and selected_time_str:
            try:
                # Parse the time string to extract hours, minutes, seconds
                selected_time = datetime.strptime(selected_time_str, '%H:%M:%S').time()

                # Create a datetime object
                combined_datetime = datetime(
                    selected_date.year, selected_date.month, selected_date.day,
                    selected_time.hour, selected_time.minute, selected_time.second)

                # Load collimator data
                self.collimator_data.load_data(combined_datetime)

                # Update the graph with the new collimator data
                self.update_graph()

            except ValueError:
                print("Invalid time format. Please use HH:MM:SS.                                      ", end="\r")
        else:
            print("Please select both a date and a time.                                      ", end="\r")

    def on_reset_button_clicked(self, b):
        """
        Handle the event when the Reset button is clicked. 
        Remove all selected knobs, reset their values, and update the display and graph.
        """
        # Remove selected knobs and their associated data
        for knob in self.selected_knobs[:]:
            self.selected_knobs.remove(knob)
            del self.values[knob]  # Remove the value of the knob
            del self.knob_widgets[knob]  # Remove the widget

        # Reset knobs to their initial values and re-twiss
        self.aperture_data.reset_knobs()

        # Update selected knobs and display value
        self.update_knob_box()

        # Update the figure
        self.update_graph()

    def on_cycle_button_clicked(self, b):
        """
        Handle the event when the Cycle button is clicked. 
        Cycle all the data to set a new zero point and update the graph.
        """
        # Retrieve the selected element from the widget
        first_element = self.cycle_input.value
        print(f'Setting {first_element} as the first element...                                      ', end="\r")
        # Cycle
        self.aperture_data.cycle(first_element)
        # If invalid input don't update the graph
        if len(self.aperture_data.tw_b1.loc[self.aperture_data.tw_b1['name'] != first_element]['s'].values)!=0:
            # Update the figure
            self.update_graph()

    def on_add_button_clicked(self, b):
        """
        Handle the event when the Add button is clicked. 
        Add a new knob to the selected list and create a widget for it.
        """
        # Knob selected in the dropdown menu
        knob = self.knob_dropdown.value
        # If the knob is not already in the selected list, add it
        if knob and knob not in self.selected_knobs:
            self.selected_knobs.append(knob)
            self.values[knob] = 1.0  # Initialize knob for new value

            # Create a new FloatText widget for the selected knob
            knob_widget = FloatText(
                value=self.aperture_data.knobs[self.aperture_data.knobs['knob']==knob]['current value'],
                description=f'{knob}',
                disabled=False
            )
            # Add the widget to the knob widgets list
            self.knob_widgets[knob] = knob_widget

            # Update selected knobs and display value
            self.update_knob_box()

    def on_remove_button_clicked(self, b):
        """
        Handle the event when the Remove button is clicked. 
        Remove the selected knob from the list and delete its widget.
        """
        # Knob selected in the dropdown menu
        knob = self.knob_dropdown.value
        # If the knob is in the selected list, remove it
        if knob in self.selected_knobs:
            self.selected_knobs.remove(knob)
            del self.values[knob]  # Remove the value of the knob
            if knob in self.knob_widgets:
                del self.knob_widgets[knob]  # Remove the widget

            # Update selected knobs and display value
            self.update_knob_box()

    def on_apply_button_clicked(self, b):
        """
        Handle the event when the Apply button is clicked. 
        Apply changes to the knobs and update the graph.
        """
        # Update knobs dictionary based on current values in the knob widgets
        for knob, widget in self.knob_widgets.items():
            self.aperture_data.change_knob(knob, widget.value)

        # Re-twiss
        self.aperture_data.twiss()

        # Update the figure
        self.update_graph()

    def update_knob_box(self):
        """
        Updates the layout of the knob_box with current knob widgets.
        """
        # Group the widgets into sets of three per row
        rows = []
        for i in range(0, len(self.selected_knobs), 3):
            row = HBox([self.knob_widgets[knob] for knob in self.selected_knobs[i:i+3]],
                       layout=Layout(align_items='flex-start'))
            rows.append(row)

        # Update the knob_box with the new rows
        self.knob_box.children = rows

    def update_knob_dropdown(self):

        # Create a dropdown to select a knob
        self.knob_dropdown.options = self.aperture_data.knobs['knob'].to_list()

    def disable_widgets(self):

        filtered_buttons = [widget for widget in self.widgets if isinstance(widget, Button)]

        for i in filtered_buttons[1:]:
            i.disabled = True
    
    def enable_widgets(self):

        filtered_buttons = [widget for widget in self.widgets if isinstance(widget, Button)]

        for i in filtered_buttons:
            i.disabled = False

    def update_graph(self):
        """
        Updates the graph displayed in the graph_container.
        """
        # If line loaded add all the available traces
        if hasattr(self, 'aperture_data'): 
            self.create_figure()
            
        # Else return an empty figure
        else: 
            self.fig = make_subplots(rows=1, cols=1)
            self.row, self.col = 1, 1
            self.disable_widgets()

        self.update_layout()   
        # Change to a widget
        self.fig_widget = go.FigureWidget(self.fig)
        # Put the figure in the graph container
        self.graph_container.children = [self.fig_widget]

    def show(self,
             width: Optional[int] = 1600, 
             height: Optional[int] = 600):
        
        self.width = width
        self.height = height
        
        # Display the widgets and the graph
        display(self.full_layout)

        # Plot all traces
        self.update_graph()

    def create_figure(self):
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
        self.visibility_b1 = np.array([], dtype=bool)
        self.visibility_b2 = np.array([], dtype=bool)

        # If thick machine elements are loaded
        if hasattr(self.aperture_data, 'elements'):

            # Create 2 subplots: for elements and the plot
            self.fig = make_subplots(rows=2, cols=1, row_heights=[0.2, 0.8], shared_xaxes=True)
            # Update layout of the upper plot (machine components plot)
            self.fig.update_yaxes(range=[-1, 1], showticklabels=False, showline=False, row=1, col=1)
            self.fig.update_xaxes(showticklabels=False, showline=False, row=1, col=1)
            elements_visibility, elements = plot_machine_components(self.aperture_data)

            for i in elements:
                self.fig.add_trace(i, row=1, col=1)

            # Row and col for other traces
            self.row, self.col = 2, 1

            # Always show machine components
            self.visibility_b1 = np.append(self.visibility_b1, elements_visibility)
            self.visibility_b2 = np.append(self.visibility_b2, elements_visibility)

        # If thick machine elements are not loaded
        else:
            # Create only one plot
            self.fig = make_subplots(rows=1, cols=1)
            # Row and col for other traces
            self.row, self.col = 1, 1

        # If any additional traces were given as an argument
        if self.additional_traces:
            # TODO: handle if not a list
            for i in self.additional_traces:
                self.fig.add_trace(i, row=self.row, col=self.col)
                self.visibility_b1 = np.append(self.visibility_b1, True)
                self.visibility_b2 = np.append(self.visibility_b2, True)

        # If there is aperture data
        if hasattr(self.aperture_data, 'aper_b1'):
            aper_visibility, apertures = plot_aperture(self.aperture_data, self.plane)
            for i in apertures:
                self.fig.add_trace(i, row=self.row, col=self.col)

            # Show only aperture for one beam
            self.visibility_b1 = np.append(self.visibility_b1, aper_visibility)
            self.visibility_b2 = np.append(self.visibility_b2, np.logical_not(aper_visibility))

        # If there are collimators loaded from yaml file
        if hasattr(self.aperture_data, 'colx_b1'):
            collimator_visibility, collimator = plot_collimators_from_yaml(self.aperture_data, self.plane)
            for i in collimator:
                self.fig.add_trace(i, row=self.row, col=self.col)

            # Show only collimators for one beam
            visibility_b1 = np.append(visibility_b1, collimator_visibility)
            visibility_b2 = np.append(visibility_b2, np.logical_not(collimator_visibility))

        # If collimators were loaded from timber
        if self.collimator_data and hasattr(self.collimator_data, 'colx_b1'):
            collimator_visibility, collimator = plot_collimators_from_timber(self.collimator_data, self.aperture_data, self.plane)
            for i in collimator:
                self.fig.add_trace(i, row=self.row, col=self.col)

            # Show only collimators for one beam
            self.visibility_b1 = np.append(self.visibility_b1, collimator_visibility)
            self.visibility_b2 = np.append(self.visibility_b2, np.logical_not(collimator_visibility))

        # If BPM data was loaded from timber
        if self.BPM_data and hasattr(self.BPM_data, 'data'):
            BPM_visibility, BPM_traces = plot_BPM_data(self.BPM_data, self.plane, self.aperture_data)
            for i in BPM_traces:
                self.fig.add_trace(i, row=self.row, col=self.col)

            # Always show BPM data for both beams
            self.visibility_b1 = np.append(self.visibility_b1, BPM_visibility)
            self.visibility_b2 = np.append(self.visibility_b2, np.logical_not(BPM_visibility))

        # Add beam positions from twiss data
        beam_visibility, beams = plot_beam_positions(self.aperture_data, self.plane)  

        for i in beams:
            self.fig.add_trace(i, row=self.row, col=self.col)

        # Always show BPM data for both beams
        self.visibility_b1 = np.append(self.visibility_b1, beam_visibility)
        self.visibility_b2 = np.append(self.visibility_b2, np.logical_not(beam_visibility))

        # Add nominal beam positions
        nominal_beam_visibility, nominal_beams = plot_nominal_beam_positions(self.aperture_data, self.plane)

        for i in nominal_beams:
            self.fig.add_trace(i, row=self.row, col=self.col)

        # Always show BPM data for both beams
        self.visibility_b1 = np.append(self.visibility_b1, nominal_beam_visibility)
        self.visibility_b2 = np.append(self.visibility_b2, np.logical_not(nominal_beam_visibility))

        # Add envelopes
        envelope_visibility, envelope = plot_envelopes(self.aperture_data, self.plane)    
        for i in envelope:
            self.fig.add_trace(i, row=self.row, col=self.col)

        # Always show BPM data for both beams
        self.visibility_b1 = np.append(self.visibility_b1, envelope_visibility)
        self.visibility_b2 = np.append(self.visibility_b2, np.logical_not(envelope_visibility))

        self.visibility_b1, self.visibility_b2, self.visibility_both = self.visibility_b1.tolist(), self.visibility_b2.tolist(), np.full(len(self.visibility_b1), True)
        
    def update_layout(self):
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
        self.fig.update_layout(height=self.height, width=self.width, showlegend=False, xaxis=dict(tickformat=','), yaxis=dict(tickformat=','), plot_bgcolor='white')

        # Change x limits and labels
        self.fig.update_xaxes(title_text="s [m]", row=self.row, col=self.col)

        # Change y limits and labels
        if self.plane == 'horizontal': title = 'x [m]'
        elif self.plane == 'vertical': title = 'y [m]'

        self.fig.update_yaxes(title_text=title, range = [-0.05, 0.05], row=self.row, col=self.col)

        if hasattr(self, 'aperture_data'): 
            self.fig.update_layout(
                                    updatemenus=[
                                        dict(
                                            type="buttons",
                                            direction="right",
                                            active=0,
                                            xanchor='left',
                                            y=1.2,
                                            buttons=list([
                                                dict(label="Show beam 1",
                                                    method="update",
                                                    args=[{"visible": self.visibility_b1}]),
                                                dict(label="Show beam 2",
                                                    method="update",
                                                    args=[{"visible": self.visibility_b2}]),
                                                dict(label="Show both beams",
                                                    method="update",
                                                    args=[{"visible": self.visibility_both}])]))])