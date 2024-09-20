import numpy as np
import os
import pandas as pd
import copy
from datetime import datetime, date
from typing import Optional, List, Tuple, Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ipywidgets import widgets, Tab, VBox, HBox, Button, Layout, FloatText, DatePicker, Text, Dropdown, Label, Accordion
from IPython.display import display
from ipyfilechooser import FileChooser

from aper_package.figure_data import *
from aper_package.utils import print_and_clear
from aper_package.timber_data import *
from aper_package.aperture_data import ApertureData

class InteractiveTool():
    
    def __init__(self,
                 initial_path: Optional[str] = '/eos/project-c/collimation-team/machine_configurations/',
                 spark: Optional[Any] = None, 
                 angle_range = (-800, 800),
                 number_of_knobs_per_line = 5):
        
        """
        Create and display an interactive plot with widgets for controlling and visualizing data.

        Parameters:
            initial_path: initial path for FileChoosers
            spark: SWAN spark session
        """
        # Initially, set all the paths to None
        self.path_line = None
        self.path_aperture = None
        self.path_optics = None

        self.initial_path = initial_path
        # By default show horizontal plane first
        self.plane = 'horizontal'
        self.spark = spark
        self.number_of_knobs_per_line = number_of_knobs_per_line
        self.angle_range = angle_range
        self.cross_section_b1 = self.create_empty_cross_section()
        self.cross_section_b2 = self.create_empty_cross_section()
        self.cross_section_both = self.create_empty_cross_section()
        # Create and configure widgets
        self.create_file_choosers()
        self.create_options_controls()
        self.create_knob_controls()
        self.create_local_bump_controls()
        self.create_2d_plot_controls()
        self.create_acb_knobs()
        self.create_graph_container()

        # Put all the widgets together into a nice layout
        self.group_all_widgets()
        self.define_widget_layout()

    def create_file_choosers(self):
        """
        Initializes file chooser widgets and corresponding load buttons for the user interface.

        This method creates three file chooser widgets for selecting different types of files
        (line, aperture, and optics) and their corresponding labels.
        """

        # Create filechoosers
        self.file_chooser_line = FileChooser(self.initial_path, layout=Layout(width='350px'))
        self.file_chooser_aperture = FileChooser(self.initial_path, layout=Layout(width='350px'))
        self.file_chooser_optics = FileChooser(self.initial_path, layout=Layout(width='350px'))

        # Create descriptions for each file chooser
        line_chooser_with_label = HBox([Label("Select Line File:"), self.file_chooser_line])
        aperture_chooser_with_label = HBox([Label("Select Aperture File:"), self.file_chooser_aperture])
        optics_chooser_with_label = HBox([Label("Select Optics File:"), self.file_chooser_optics])

        # Group together
        self.file_chooser_controls = [line_chooser_with_label, aperture_chooser_with_label, optics_chooser_with_label]

    def create_knob_controls(self):
        """
        Initializes the knob controls for the user interface. 

        This method sets up the necessary containers and widgets to manage knob selections, 
        including a dropdown for selecting knobs and a box to display the selected knobs. 
        It handles the initialization based on whether the `aperture_data` attribute exists 
        and contains valid knob data.
        """
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
        
        # Button to add selection
        self.add_button = Button(
            description="Add", 
            style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)'), 
            tooltip='Add the selected knob to the list of adjustable knobs.'
        )
        # Button to remove selection
        self.remove_button = Button(
            description="Remove", 
            style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'), 
            tooltip='Remove the selected knob from the list of adjustable knobs.'
        )

        # Button to reset knobs    
        self.reset_button = Button(
            description="Reset knobs", 
            style=widgets.ButtonStyle(button_color='rgb(255, 242, 174)'), 
            tooltip='Reset all knobs to their default or nominal values.'
        )

        self.knob_controls = [self.knob_dropdown, self.add_button, self.remove_button, self.reset_button]

        # Assign function to buttons
        self.add_button.on_click(self.on_add_button_clicked)
        self.remove_button.on_click(self.on_remove_button_clicked)
        self.reset_button.on_click(self.on_reset_button_clicked)

    def update_knob_box(self):
        """
        Updates the layout of the knob_box with current knob widgets.
        """
        # Group the widgets into sets of three per row21840
        rows = []
        for i in range(0, len(self.selected_knobs), self.number_of_knobs_per_line):
            row = HBox([self.knob_widgets[knob] for knob in self.selected_knobs[i:i+self.number_of_knobs_per_line]],
                       layout=Layout(align_items='flex-start'))
            rows.append(row)

        # Update the knob_box with the new rows
        self.knob_box.children = rows

    def update_knob_dropdown(self):
        """
        Update the knob dropdown with a list of knobs read from loaded JSON file
        """
        # Create a dropdown to select a knob
        self.knob_dropdown.options = self.aperture_data.knobs['knob'].to_list()
        if self.spark: self.ls_dropdown.options = [knob for knob in self.aperture_data.knobs['knob'].to_list() if 'on_x' in knob]

    def create_local_bump_controls(self):
        
        # Dictionary to hold all created bumps (key: bump_name, value: VBox containing bump details)
        self.bump_dict = {}
        
        # Dropdown to select the bump
        self.bump_selection_dropdown = widgets.Dropdown(options=[], description="Select Bump", layout=widgets.Layout(width='200px'))

        # Dropdown to select bump for final addition
        self.final_bump_dropdown = widgets.Dropdown(options=[], description="Final Bump", layout=widgets.Layout(width='200px'))
        
        # Button to define a new bump
        self.define_bump_button = widgets.Button(description="Define a new bump", style=widgets.ButtonStyle(button_color='pink'))
        self.define_bump_button.on_click(self.define_bump)

        # Dropdown to select the bump
        self.bump_selection_dropdown = widgets.Dropdown(options=[], description="Select Bump", layout=widgets.Layout(width='200px'))

        # Dropdown to select the knob
        self.bump_knob_dropdown = widgets.Dropdown(options=[], description="Knob", layout=widgets.Layout(width='200px'))
        
        # Dropdown to select the knob
        self.sort_knobs_plane_dropdown = widgets.Dropdown(options=['horizontal', 'vertical'], description="Plane", layout=widgets.Layout(width='200px'))

        # Dropdown to select the knob
        self.sort_knobs_beam_dropdown = widgets.Dropdown(options=['beam 1', 'beam 2'], description="Beam", layout=widgets.Layout(width='200px'))

        self.sort_knobs_plane_dropdown.observe(self.update_bump_knob_dropdown, names='value')
        self.sort_knobs_beam_dropdown.observe(self.update_bump_knob_dropdown, names='value')
        
        # Dropdown to select bump for final addition
        self.final_bump_dropdown = widgets.Dropdown(options=[], description="Final Bump", layout=widgets.Layout(width='200px'))

        # Button to add the selected knob
        self.add_bump_knob_button = widgets.Button(description="Add Knob", layout=widgets.Layout(width='150px'), style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)'))
        self.add_bump_knob_button.on_click(self.add_knob)

        # Button to apply operation
        self.bump_apply_button = widgets.Button(description="Apply", style=widgets.ButtonStyle(button_color='pink'), layout=widgets.Layout(width='150px'))
        self.bump_apply_button.on_click(self.apply_operation)

        # Button to add the selected bump to the final container
        self.add_final_bump_button = widgets.Button(description="Add Bump", layout=widgets.Layout(width='150px'), style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)'))
        self.add_final_bump_button.on_click(self.add_final_bump)
        
        # Create the main container that will hold all the dynamically added VBox widgets
        self.main_bump_box = widgets.VBox([])
        
        # Container to hold bumps added to the final HBox with floats
        self.final_bump_container = widgets.GridBox([], layout=widgets.Layout(grid_template_columns="repeat(4, 500px)", width='100%'))
        
    def define_bump(self, b):
        bump_name = f"Bump {len(self.bump_dict) + 1}"  # Unique bump name
        beam_dropdown = widgets.Dropdown(options=['beam 1', 'beam 2'], description=f'{bump_name}: Beam', layout=widgets.Layout(width='400px'), style={'description_width': '150px'})

        # Container for knobs in a grid (4 knobs per row)
        knob_container = widgets.GridBox([], layout=widgets.Layout(grid_template_columns="repeat(5, 400px)", width='100%'))

        # Create the VBox for each bump (beam + knobs)
        bump_vbox = widgets.VBox([beam_dropdown, knob_container], layout=widgets.Layout(width='100%', padding='10px', border='solid 2px #ccc'))

        # Add the new bump to the main box
        self.main_bump_box.children += (bump_vbox,)

        # Store the bump in the dictionary
        self.bump_dict[bump_name] = {
            'vbox': bump_vbox,
            'knobs': knob_container,
            'added_knobs': [],  # List to track added knobs
            'float_inputs': []  # List to store float inputs for each knob
        }

        # Update the bump selection dropdown to include the new bump
        self.bump_selection_dropdown.options = list(self.bump_dict.keys())
        self.final_bump_dropdown.options = list(self.bump_dict.keys())  # Update the dropdown for the final section
        
    # Function to add a knob to the selected bump
    def add_knob(self, b):
        selected_bump = self.bump_selection_dropdown.value
        if selected_bump in self.bump_dict:
            knob_name = self.bump_knob_dropdown.value

            # Check if the knob is already added
            if knob_name not in self.bump_dict[selected_bump]['added_knobs']:
                float_input = widgets.FloatText(description=knob_name, layout=widgets.Layout(width='200px'))
                remove_button = widgets.Button(description="Remove", style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'), layout=widgets.Layout(width='100px'))

                # Function to remove the knob
                def remove_knob(btn):
                    # Remove the knob from the UI
                    self.bump_dict[selected_bump]['knobs'].children = [
                        child for child in self.bump_dict[selected_bump]['knobs'].children
                        if child is not knob_hbox
                    ]
                    # Remove the knob from the added_knobs list and float_inputs
                    self.bump_dict[selected_bump]['added_knobs'].remove(knob_name)
                    self.bump_dict[selected_bump]['float_inputs'].remove(float_input)

                knob_hbox = widgets.HBox([float_input, remove_button], layout=widgets.Layout(width='100%', padding='5px', align_items='center'))
                remove_button.on_click(remove_knob)

                # Add the knob to the corresponding bump's knob container
                self.bump_dict[selected_bump]['knobs'].children += (knob_hbox,)

                # Add the knob to the added_knobs list and float_inputs list
                self.bump_dict[selected_bump]['added_knobs'].append(knob_name)
                self.bump_dict[selected_bump]['float_inputs'].append(float_input)
            
    # Function to add a bump to the final bump container
    def add_final_bump(self, b):
        selected_bump = self.final_bump_dropdown.value
        if selected_bump and selected_bump not in [child.children[0].value for child in self.final_bump_container.children]:
            float_input = widgets.FloatText(description="Value", layout=widgets.Layout(width='200px'))
            remove_button = widgets.Button(description="Remove", style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'), layout=widgets.Layout(width='100px'))

            # Create HBox with bump dropdown and float input
            bump_hbox = widgets.HBox([widgets.Label(selected_bump, layout=widgets.Layout(width='50px', align_items='center')), float_input, remove_button], layout=widgets.Layout(width='400px', padding='5px', align_items='center'))

            # Function to remove bump from final container
            def remove_bump(btn):
                self.final_bump_container.children = [child for child in self.final_bump_container.children if child is not bump_hbox]

            remove_button.on_click(remove_bump)
            self.final_bump_container.children += (bump_hbox,)
            
    # Function to apply and calculate sum of knobs for each bump
    def apply_operation(self, b):
          
        for bump_hbox in self.final_bump_container.children:
            bump_name = bump_hbox.children[0].value
            bump_float_value = bump_hbox.children[1].value

            if bump_name in self.bump_dict:
                float_inputs = self.bump_dict[bump_name]['float_inputs']
                selected_beam = self.bump_dict[bump_name]['vbox'].children[0].value  # Get the selected beam
                
                for i in float_inputs:
                    self.aperture_data.change_acb_knob(i.description, i.value*bump_float_value*1e-6, selected_beam)
        
        self.aperture_data.twiss()
        self.update_graph()
            
    def create_acb_knobs(self):
        """
        Initialises controls for adding a local bump by specifying currents for knobs
        """
        self.bump_plane_dropdown_b1 = Dropdown(
                    options=['horizontal', 'vertical'],
                    description='Select plane:',
                    layout=Layout(width='300px'),
                    disabled=False)
        
        self.bump_plane_dropdown_b2 = Dropdown(
                    options=['horizontal', 'vertical'],
                    description='Select plane:',
                    layout=Layout(width='300px'),
                    disabled=False)
        
        self.remove_bumps_button = Button(
                description="Remove all bumps", 
                style=widgets.ButtonStyle(button_color='rgb(255, 242, 174)')
            )
        
        # Attach a method to the button
        self.remove_bumps_button.on_click(self.on_remove_bumps_button_clicked)

        # Attach the update function to the first dropdown's 'value' attribute
        self.bump_plane_dropdown_b1.observe(self.update_acb_dropdown_b1, names='value')
        self.bump_plane_dropdown_b2.observe(self.update_acb_dropdown_b2, names='value')
        # Group in a list for later
        self.main_bump_controls = [self.remove_bumps_button]
        
        # Dictionaries and list to store selected knobs, corresponding widgets, and current widget values
        self.selected_acb_knobs_b1 = []
        self.acb_widgets_b1 = {}
        self.acb_values_b1 = {}
        
        self.selected_acb_knobs_b2 = []
        self.acb_widgets_b2 = {}
        self.acb_values_b2 = {}

        # Create a dropdown to select a knob
        self.acb_knob_dropdown_b1 = Dropdown(
                options=[],
                description='Select knob:',
                disabled=False)
        
        self.acb_knob_dropdown_b2 = Dropdown(
                options=[],
                description='Select knob:',
                disabled=False)
        
        # Create a box to store selected knobs
        self.acb_knob_box_b1 = VBox(layout=Layout(
            justify_content='center',
            align_items='center',
            width='100%',
            padding='10px',
            border='solid 2px #eee'))
        
        self.acb_knob_box_b2 = VBox(layout=Layout(
            justify_content='center',
            align_items='center',
            width='100%',
            padding='10px',
            border='solid 2px #eee'))
        
        # Button to add selection
        self.acb_add_button_b1 = Button(
            description="Add", 
            style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)'), 
            tooltip='Add the selected knob to the list of adjustable knobs.'
        )
        # Button to remove selection
        self.acb_remove_button_b1 = Button(
            description="Remove", 
            style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'), 
            tooltip='Remove the selected knob from the list of adjustable knobs.'
        )
        # Button to add a bump    
        self.acb_apply_button_b1 = Button(
            description="Add bump", 
            style=widgets.ButtonStyle(button_color='pink'), 
            tooltip='Reset all knobs to their default or nominal values.'
        )

        # Group in a list for later
        self.acb_knob_controls_b1 = [self.bump_plane_dropdown_b1, self.acb_knob_dropdown_b1, self.acb_add_button_b1, self.acb_remove_button_b1, self.acb_apply_button_b1]
        
        # Button to add selection
        self.acb_add_button_b2 = Button(
            description="Add", 
            style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)'), 
            tooltip='Add the selected knob to the list of adjustable knobs.'
        )
        # Button to remove selection
        self.acb_remove_button_b2 = Button(
            description="Remove", 
            style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'), 
            tooltip='Remove the selected knob from the list of adjustable knobs.'
        )
        # Button to add a bump    
        self.acb_apply_button_b2 = Button(
            description="Add bump", 
            style=widgets.ButtonStyle(button_color='pink'), 
            tooltip='Reset all knobs to their default or nominal values.'
        )

        # Group in a list for later
        self.acb_knob_controls_b2 = [self.bump_plane_dropdown_b2, self.acb_knob_dropdown_b2, self.acb_add_button_b2, self.acb_remove_button_b2, self.acb_apply_button_b2]

        # Assign function to buttons
        self.acb_add_button_b1.on_click(lambda b: self.on_acb_add_button_clicked(b, 'beam 1'))
        self.acb_remove_button_b1.on_click(lambda b:self.on_acb_remove_button_clicked(b, 'beam 1'))
        self.acb_apply_button_b1.on_click(lambda b:self.on_acb_apply_button_clicked(b, 'beam 1'))
        
        self.acb_add_button_b2.on_click(lambda b: self.on_acb_add_button_clicked(b, 'beam 2'))
        self.acb_remove_button_b2.on_click(lambda b:self.on_acb_remove_button_clicked(b, 'beam 2'))
        self.acb_apply_button_b2.on_click(lambda b:self.on_acb_apply_button_clicked(b, 'beam 2'))
    
    def on_acb_apply_button_clicked(self, b, beam):
        """
        Handles event of adding a local bump by using current inputs
        """
        if beam == 'beam 1': 
            plane_dropdown = self.bump_plane_dropdown_b1
            acb_widgets = self.acb_widgets_b1
        elif beam == 'beam 2': 
            plane_dropdown = self.bump_plane_dropdown_b2
            acb_widgets = self.acb_widgets_b2
            
        try:
            for knob, widget in acb_widgets.items():
                self.aperture_data.change_acb_knob(knob, widget.value, beam)

            # Re-twiss
            self.aperture_data.twiss()
            self.update_graph()
        except: 
            print_and_clear('Could not compute twiss. Try again with different knob values.')

    def on_acb_add_button_clicked(self, b, beam):
        """
        Handle the event when the Add button is clicked. 
        Add a new knob to the selected list and create a widget for it.
        """
        if beam == 'beam 1': 
            acb_knob_dropdown = self.acb_knob_dropdown_b1
            acb_widgets = self.acb_widgets_b1
            selected_acb_knobs = self.selected_acb_knobs_b1
            acb_values = self.acb_values_b1
        elif beam == 'beam 2': 
            acb_knob_dropdown = self.acb_knob_dropdown_b2
            acb_widgets = self.acb_widgets_b2
            selected_acb_knobs = self.selected_acb_knobs_b2
            acb_values = self.acb_values_b2
            
        # Knob selected in the dropdown menu
        knob = acb_knob_dropdown.value
        # If the knob is not already in the selected list, add it
        if knob and knob not in selected_acb_knobs:
            selected_acb_knobs.append(knob)
            acb_values[knob] = 0
            # Create a new FloatText widget for the selected knob
            acb_widget = FloatText(
                value=acb_values[knob],
                description=f'{knob}',
                disabled=False
            )
            # Add the widget to the knob widgets list
            acb_widgets[knob] = acb_widget

            # Update selected knobs and display value
            self.update_acb_box(beam)

    def on_acb_remove_button_clicked(self, b, beam):
        """
        Handle the event when the Remove button is clicked. 
        Remove the selected knob from the list and delete its widget.
        """
        if beam == 'beam 1': 
            acb_knob_dropdown = self.acb_knob_dropdown_b1
            acb_widgets = self.acb_widgets_b1
            selected_acb_knobs = self.selected_acb_knobs_b1
            acb_values = self.acb_values_b1
        elif beam == 'beam 2': 
            acb_knob_dropdown = self.acb_knob_dropdown_b2
            acb_widgets = self.acb_widgets_b2
            selected_acb_knobs = self.selected_acb_knobs_b2
            acb_values = self.acb_values_b2
            
        # Knob selected in the dropdown menu
        knob = acb_knob_dropdown.value
        # If the knob is in the selected list, remove it
        if knob in selected_acb_knobs:
            selected_acb_knobs.remove(knob)
            del acb_values[knob]  # Remove the value of the knob
            if knob in acb_widgets:
                del acb_widgets[knob]  # Remove the widget

            # Update selected knobs and display value
            self.update_acb_box(beam)

    def update_acb_box(self, beam):
        """
        Updates the layout of the knob_box with current knob widgets.
        """
        if beam == 'beam 1': 
            acb_knob_dropdown = self.acb_knob_dropdown_b1
            acb_widgets = self.acb_widgets_b1
            selected_acb_knobs = self.selected_acb_knobs_b1
            acb_values = self.acb_values_b1
            acb_knob_box = self.acb_knob_box_b1
        elif beam == 'beam 2': 
            acb_knob_dropdown = self.acb_knob_dropdown_b2
            acb_widgets = self.acb_widgets_b2
            selected_acb_knobs = self.selected_acb_knobs_b2
            acb_values = self.acb_values_b2
            acb_knob_box = self.acb_knob_box_b2
            
        # Group the widgets into sets of three per row21840
        rows = []
        for i in range(0, len(selected_acb_knobs), self.number_of_knobs_per_line):
            row = HBox([acb_widgets[knob] for knob in selected_acb_knobs[i:i+self.number_of_knobs_per_line]],
                       layout=Layout(align_items='flex-start'))
            rows.append(row)

        # Update the knob_box with the new rows
        acb_knob_box.children = rows
        
    def create_options_controls(self):
        """
        Controls for the third row: first element, envelope size, plane
        """
        # Create a text widget to specify cycle start
        self.cycle_input = Text(
            value='',                               # Initial value (empty string)
            description='First element:',           # Label for the widget
            placeholder='e. g. ip3',                # Placeholder text when the input is empty
            style={'description_width': 'initial'}, # Adjust the width of the description label
            layout=Layout(width='300px'))           # Set the width of the widget

        self.envelope_input = FloatText(
                value=4,                    # Initial value (4 sigma)
                description='Envelope size [σ]:',    # Label for the widget 
                style={'description_width': 'initial'}, # Adjust the width of the description label
                layout=Layout(width='300px'))           # Set the width of the widget
        
        # Create a dropdown to select a plane
        self.plane_dropdown = Dropdown(
            options=['horizontal', 'vertical'],
            description='Select plane:',
            disabled=False)
        
        # Button to switch between horizontal and vertical planes
        self.apply_changes_button = Button(
            description="Apply changes", 
            style=widgets.ButtonStyle(button_color='pink'), 
            tooltip='blah blah'
        )
        # Assign method to the button
        self.apply_changes_button.on_click(self.on_apply_changes_button_clicked)

        # Group in a list for later
        self.options_controls = [self.cycle_input, self.envelope_input, self.plane_dropdown, self.apply_changes_button]

    def create_2d_plot_controls(self):

        self.element_input = Text(
            value='',                               # Initial value (empty string)
            description='Element:',           # Label for the widget
            placeholder='e. g. mq.21l3.b1_mken',                # Placeholder text when the input is empty
            style={'description_width': 'initial'}, # Adjust the width of the description label
            layout=Layout(width='300px'))  
        
        self.beam_dropdown_2d_plot = Dropdown(
                    options=['beam 1', 'beam 2', 'both'],
                    description='Select beam:',
                    layout=Layout(width='300px'),
                    disabled=False)
        
        self.generate_2d_plot_button = Button(
            description="Generate", 
            style=widgets.ButtonStyle(button_color='pink'), 
            tooltip='blah blah'
        )
        
        self.add_trace_to_2d_plot_button = Button(
            description="Add trace", 
            style=widgets.ButtonStyle(button_color='pink'), 
            tooltip='blah blah'
        )    

        self.generate_2d_plot_button.on_click(self.generate_2d_plot_button_clicked)
        self.add_trace_to_2d_plot_button.on_click(self.add_trace_to_2d_plot_button_clicked)        
        
        self.cross_section_controls = [self.element_input, self.beam_dropdown_2d_plot]
        
        # Attach the action to the dropdown's 'observe' method
        self.beam_dropdown_2d_plot.observe(self.on_beam_change)

    def on_beam_change(self, change):
        
        if change['type'] == 'change' and change['name'] == 'value':
            # Add your desired action here
            beam = change['new']
            if beam == 'beam 1': self.cross_section_container.children = [self.cross_section_b1]
            elif beam == 'beam 2': self.cross_section_container.children = [self.cross_section_b2]
            elif beam == 'both': self.cross_section_container.children = [self.cross_section_both]

    def add_trace_to_2d_plot_button_clicked(self, b):
        
        n = self.aperture_data.n
        element = self.element_input.value
        beam = self.beam_dropdown_2d_plot.value
        
        beam_center_trace_b1, envelope_trace_b1, aperture_trace = add_beam_trace(element, 'beam 1', self.aperture_data, n)
        self.cross_section_b1.add_trace(beam_center_trace_b1)
        self.cross_section_b1.add_trace(envelope_trace_b1)
        beam_center_trace_b2, envelope_trace_b2, aperture_trace = add_beam_trace(element, 'beam 2', self.aperture_data, n)
        self.cross_section_b2.add_trace(beam_center_trace_b2)
        self.cross_section_b2.add_trace(envelope_trace_b2)

        self.cross_section_both.add_trace(beam_center_trace_b1)
        self.cross_section_both.add_trace(envelope_trace_b1)
        self.cross_section_both.add_trace(beam_center_trace_b2)
        self.cross_section_both.add_trace(envelope_trace_b2)
        
        if beam == 'beam 1': self.cross_section_container.children = [self.cross_section_b1]
        elif beam == 'beam 2': self.cross_section_container.children = [self.cross_section_b2]
        elif beam == 'both': self.cross_section_container.children = [self.cross_section_both]
    
    def generate_2d_plot_button_clicked(self, b):

        n = self.aperture_data.n
        element = self.element_input.value
        beam = self.beam_dropdown_2d_plot.value
        try:
            print_and_clear('Generating the cross-section...')
            self.cross_section_b1 = generate_2d_plot(element, 'beam 1', self.aperture_data, n, width=450, height=450)
            self.cross_section_b2 = generate_2d_plot(element, 'beam 2', self.aperture_data, n, width=450, height=450)
            self.cross_section_both = generate_2d_plot(element, 'both', self.aperture_data, n, width=450, height=450)
            if beam == 'beam 1': self.cross_section_container.children = [self.cross_section_b1]
            elif beam == 'beam 2': self.cross_section_container.children = [self.cross_section_b2]
            elif beam == 'both': self.cross_section_container.children = [self.cross_section_both]
        except Exception as e:
            raise e
        
    def on_remove_bumps_button_clicked(self, b):
        """
        Handles event of clicking Remove all bumps button
        """
        self.aperture_data.reset_all_acb_knobs()
        self.update_graph()
        
    def update_bump_knob_dropdown(self, change):
        
        if hasattr(self, 'aperture_data'):
            beam = self.sort_knobs_beam_dropdown.value
            plane = self.sort_knobs_plane_dropdown.value
            if plane == 'horizontal': 
                if beam == 'beam 1': 
                    self.bump_knob_dropdown.options = self.aperture_data.acbh_knobs_b1['knob']
                elif beam == 'beam 2': 
                    self.bump_knob_dropdown.options = self.aperture_data.acbh_knobs_b2['knob']
            if plane == 'vertical':
                if beam == 'beam 1': 
                    self.bump_knob_dropdown.options = self.aperture_data.acbv_knobs_b1['knob']
                elif beam == 'beam 2': 
                    self.bump_knob_dropdown.options = self.aperture_data.acbv_knobs_b2['knob']
    
    def update_acb_dropdown(self, beam, plane_dropdown, knob_dropdown):
        """
        Method to update all local bump dropdowns options by plane and beam selected
        """
        if hasattr(self, 'aperture_data'):
            # Update dropdowns with acb knobs dropdowns
            if plane_dropdown.value == 'horizontal': 
                if beam == 'beam 1': 
                    knob_dropdown.options = self.aperture_data.acbh_knobs_b1['knob']
                elif beam == 'beam 2': 
                    knob_dropdown.options = self.aperture_data.acbh_knobs_b2['knob']
            if plane_dropdown.value == 'vertical':
                if beam == 'beam 1': 
                    knob_dropdown.options = self.aperture_data.acbv_knobs_b1['knob']
                elif beam == 'beam 2': 
                    knob_dropdown.options = self.aperture_data.acbv_knobs_b2['knob']

    def update_acb_dropdown_b1(self, change):
        """
        Handles event of changing the beam in the beam dropdown
        """
        self.update_acb_dropdown('beam 1', self.bump_plane_dropdown_b1, self.acb_knob_dropdown_b1)

    def update_acb_dropdown_b2(self, change):
        """
        Handles event of changing the plane in the bump plane dropdown
        """
        self.update_acb_dropdown('beam 2', self.bump_plane_dropdown_b2, self.acb_knob_dropdown_b2)

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
                value=date.today(),            # Sets the default value to today's date
                style={'description_width': 'initial'}, # Ensures the description width fits the content
                layout=Layout(width='300px'))           # Sets the width of the widget

        self.time_input = Text(
                description='Enter Time (HH:MM:SS):',
                value=datetime.now().strftime('%H:%M:%S'), # Sets the default value to the current time
                placeholder='10:53:15',                 # Provides a placeholder text for the expected format
                style={'description_width': 'initial'}, # Ensures the description width fits the content
                layout=Layout(width='300px'))           # Sets the width of the widget
     

    def initialise_timber_data(self):
        """
        Initializes timber-related data and UI components if the `spark` attribute is provided.

        This method sets up UI elements and data handlers for interacting with timber data. 
        If the `spark`  Update UI components
        Returns:
            list: List of UI components related to timber data, or None if `spark` is not provided.
        """
        
        # Only add timber buttons if spark given as an argument
        if self.spark:

            self.collimator_data = CollimatorsData(self.spark)
            self.BPM_data = BPMData(self.spark)
            
            # Create buttons to load BPM and collimator data
            self.load_BPMs_button = Button(
                description="Load BPMs",
                style=widgets.ButtonStyle(button_color='pink'),
                tooltip='Load BPM data from timber for the specified time.'
            )
            self.load_BPMs_button.on_click(self.on_load_BPMs_button_clicked)

            self.load_cols_button = Button(
                description="Load collimators",
                style=widgets.ButtonStyle(button_color='pink'),
                tooltip='Load collimator data from timber for the specified time.'
            )
            self.load_cols_button.on_click(self.on_load_cols_button_clicked)

            # Time selection widgets
            self.create_time_widgets()

            # Define layout depending if timber buttons present or not
            timber_row_controls = [self.date_picker, self.time_input, self.load_cols_button, self.load_BPMs_button]
            self.widgets += timber_row_controls

        else: self.BPM_data, self.collimator_data, timber_row_controls = None, None, None
            
        return timber_row_controls

    def create_ls_controls(self):
        """
        Initialises controls for least squares fitting line into BPM data
        """
        if self.spark: 
            angle_knobs = []

            # Dropdown to select whic angle to vary in the optimisation
            self.ls_dropdown = Dropdown(
                    options=angle_knobs,
                    description='Select knob:',
                    layout=Layout(width='200px'),
                    disabled=False)
                
            # Float box to input the inital guess 
            self.init_angle_input = FloatText(
                    value=0,                    # Initial value (empty string)
                    description='Initial guess:',    # Label for the widget 
                    style={'description_width': 'initial'}, # Adjust the width of the description label
                    layout=Layout(width='150px'))           # Set the width of the widget

            # Dropdown to select IR for fitting
            self.ir_dropdown = Dropdown(
                    options=['IR1', 'IR2', 'IR3', 'IR4', 'IR5', 'IR6', 'IR7', 'IR8', 'other'],
                    description='Select knob:',
                    layout=Layout(width='200px'),
                    disabled=False)

            # Attach the observe function to the dropdown
            self.ir_dropdown.observe(self.on_ir_dropdown_change, names='value')

            # Range slider to specify s
            self.s_range_slider = widgets.FloatRangeSlider(
                    value=[0, 26658],
                    min=0.0,
                    max=26658,
                    step=1,
                    description='Range:',
                    continuous_update=False,
                    layout=Layout(width='400px'),
                    readout_format='d'
                )
            
            self.fit_button = Button(
                description="Fit to data", 
                style=widgets.ButtonStyle(button_color='pink'), 
                tooltip='Perform least squares fitting.'
            )
            self.fit_button.on_click(self.on_fit_button_clicked)

            # Output with best fit angle and its uncertainty
            self.result_output = widgets.Output()

            # Group controls and append to all widgets
            ls_row_controls = [self.ls_dropdown, self.init_angle_input, self.ir_dropdown, self.s_range_slider, self.fit_button, self.result_output]
            self.widgets += ls_row_controls

            return ls_row_controls
            
        else: return None

    def on_ir_dropdown_change(self, change):
        """
        Handles event when ir dropdown was changed
        """
        if change['new'] == 'other':
            self.s_range_slider.disabled = False  # Disable the slider
        else:
            self.s_range_slider.disabled = True  # Enable the slider

    def on_fit_button_clicked(self, b):
        """
        Handles event when button Fit to data is clicked
        """
        init_angle = self.init_angle_input.value
        knob = self.ls_dropdown.value
        ir=self.ir_dropdown.value
        
        if ir == 'other': s_range = self.s_range_slider.value
        else: s_range = self.aperture_data.get_ir_boundries(ir)        

        if s_range[0]>s_range[1]: print_and_clear('Try cycling the graph first so that the IR is not on the edge.')
        else: 
            self.best_fit_angle, self.best_fit_uncertainty = self.BPM_data.least_squares_fit(self.aperture_data, init_angle, knob, self.plane, self.angle_range, s_range)

            with self.result_output:
                self.result_output.clear_output()  # Clear previous output
                print(f'Best fit angle: {self.best_fit_angle} Uncertainty: {self.best_fit_uncertainty}')

            self.update_graph()

    def create_graph_container(self):

        # Create an empty VBox container for the graph
        self.graph_container = HBox(layout=Layout(
            justify_content='center',
            align_items='center',
            width='100%',
            padding='10px',
            border='solid 2px #eee'))
        
        self.cross_section_container = HBox(
            [self.cross_section_b1],
            layout=Layout(
            justify_content='center',
            align_items='center',
            width='70%',
            padding='0px',
            border='solid 2px #eee'))

    def group_all_widgets(self):

        # Group controls together
        self.widgets = self.file_chooser_controls+self.knob_controls+self.options_controls+self.main_bump_controls+self.acb_knob_controls_b1+self.acb_knob_controls_b2     
        # If spark was not given this will return a None  
        self.timber_row_controls = self.initialise_timber_data()    
        self.ls_row_controls = self.create_ls_controls()
    
    def define_widget_layout(self):
        """
        Define and arrange the layout of the widgets.
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
            self.knob_controls,
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox

        # Create layout for the second row of controls
        second_row_layout = HBox(
            self.options_controls,
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox
        
        # Group main controls into a Vbox
        cross_section_vbox = VBox(
            [self.element_input, self.beam_dropdown_2d_plot, self.generate_2d_plot_button, self.add_trace_to_2d_plot_button],
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='0px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox
        
        full_cross_section_box = HBox(
            [self.cross_section_container, cross_section_vbox],
            layout=Layout(
                justify_content='center',   # Center items horizontally, allowing space on sides
                align_items='stretch',      # Avoid extra vertical space
                width='100%',               # Full width of the container
                padding='0px 10px',         # Padding only on left and right, none vertically
                border='solid 2px #ccc'     # Border for the outer HBox
            )
        )

        # Group main controls into a Vbox
        main_vbox = VBox(
            [file_chooser_layout, first_row_layout, self.knob_box, second_row_layout],
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox
        
        main_bump_row_layout = HBox(
            self.main_bump_controls,
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox
        
        acb_row_layout_b1 = HBox(
            self.acb_knob_controls_b1,
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc')) 
        
        acb_row_layout_b2 = HBox(
            self.acb_knob_controls_b2,
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc')) 
        
        local_bump_vbox = VBox(
            [main_bump_row_layout, acb_row_layout_b1, self.acb_knob_box_b1, acb_row_layout_b2, self.acb_knob_box_b2],
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox

        # Main controls layout
        define_bump_box = widgets.HBox([self.bump_selection_dropdown, self.sort_knobs_plane_dropdown, self.sort_knobs_beam_dropdown, self.bump_knob_dropdown, self.add_bump_knob_button], layout=widgets.Layout(
            justify_content='space-around', 
            align_items='center', 
            width='100%', 
            padding='10px', 
            border='solid 2px #ccc'
        ))

        # Controls for the final bump section
        final_controls_box = widgets.HBox([self.final_bump_dropdown, self.add_final_bump_button, self.bump_apply_button], layout=widgets.Layout(
            justify_content='space-around', 
            align_items='center', 
            width='100%', 
            padding='10px', 
            border='solid 2px #ccc'
        ))
        
        # Main controls layout
        define_bump_first_row_box = widgets.HBox([self.define_bump_button, self.remove_bumps_button], layout=widgets.Layout(
            justify_content='space-around', 
            align_items='center', 
            width='100%', 
            padding='10px', 
            border='solid 2px #ccc'
        ))

        # Display the layout
        define_local_bump_box = widgets.VBox([
            widgets.HTML("<h4>Define and Configure Bumps</h4>"),
            define_bump_first_row_box,
            define_bump_box,
            self.main_bump_box,
            widgets.HTML("<h4>Select Bumps for Final Calculation</h4>"),
            final_controls_box,
            self.final_bump_container
        ], layout=widgets.Layout(
            border='solid 2px #ccc', 
            padding='10px', 
            width='100%'
        ))
        
        if self.spark: 
            # Create layout for the timber row of controls
            timber_row_layout = HBox(
                self.timber_row_controls,
                layout=Layout(
                    justify_content='space-around', # Distribute space evenly
                    align_items='center',           # Center align all items
                    width='100%',                   # Full width of the container
                    padding='10px',                 # Add padding around controls
                    border='solid 2px #ccc'))       # Border around the HBox

            # Create layout for the timber row of controls
            ls_row_layout = HBox(
                self.ls_row_controls,
                layout=Layout(
                    justify_content='space-around', # Distribute space evenly
                    align_items='center',           # Center align all items
                    width='100%',                   # Full width of the container
                    padding='10px',                 # Add padding around controls
                    border='solid 2px #ccc'))       # Border around the HBox
            
            # Group timber controls into a Vbox
            spark_vbox = VBox(
            [timber_row_layout, ls_row_layout],
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                align_items='center',           # Center align all items
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'))       # Border around the HBox

            # Create an accordion to toggle visibility of controls
            tab = Tab(children=[main_vbox, define_local_bump_box, full_cross_section_box, spark_vbox])
            tab.set_title(3, 'Timber data')

        else: tab = Tab(children=[main_vbox, define_local_bump_box, full_cross_section_box])
            
        tab.set_title(0, 'Main')
        tab.set_title(1, 'Define local bump')
        tab.set_title(2, 'Cross-section')
        tab.layout.width = '100%'
        full_column = [tab, self.graph_container]

        # Combine both rows, knob box, and graph container into a VBox layout
        self.full_layout = VBox(
            full_column,
            layout=Layout(
                justify_content='center',       # Center align the VBox content horizontally
                align_items='center',           # Center align all items vertically
                width='100%',                    # Limit width to 80% of the page
                margin='0 auto',                # Center the VBox horizontally
                padding='20px',                 # Add p0dding around the whole container
                border='solid 2px #ddd'))       # Border around the VBox

    def on_load_all_button_clicked(self, b):

        if self.path_line != self.file_chooser_line.selected:
            self.path_line = self.file_chooser_line.selected
            self._handle_load_button_click(
                path = self.path_line,
                expected_extension='.json',
                path_replacement={'b1': 'b2'},
                load_function=self._load_line_data
            )

        if self.path_aperture != self.file_chooser_aperture.selected:
            self.path_aperture = self.file_chooser_aperture.selected
            self._handle_load_button_click(
                path=self.path_aperture,
                expected_extension='.tfs',
                path_replacement={'B1': 'B4'},
                load_function=self._load_aperture_data
            )

        if self.path_optics != self.file_chooser_optics.selected:
            self.path_optics = self.file_chooser_optics.selected
            self._handle_load_button_click(
                path=self.path_optics,
                expected_extension='.tfs',
                path_replacement=None,
                load_function=self._load_optics_data
            )

        self.update_graph()

    def _handle_load_button_click(self, path, expected_extension, path_replacement, load_function):
        """
        Handles common file validation and loading logic for various buttons.

        Parameters:
            file_chooser: The file chooser widget used to select the file.
            expected_extension: The expected file extension (e.g., '.json', '.tfs').
            path_replacement: Dictionary for path replacement (e.g., {'b1': 'b2'}). If None, no replacement is done.
            load_function: The function to call to load the data.
        """

        if not path:
            print_and_clear('Please select a file by clicking the Select button.')
            return

        _, actual_extension = os.path.splitext(path)
        if actual_extension != expected_extension:
            print_and_clear(f'Invalid file type. Please select a {expected_extension} file.')
            return

        if path_replacement:
            path_to_check = str(path)
            for old, new in path_replacement.items():
                path_to_check = path_to_check.replace(old, new)
            if not os.path.exists(path_to_check):
                print_and_clear(f"Path for the corresponding file doesn't exist.")  # TODO: Add an option for path selection
                return

        print_and_clear(f'Loading new {expected_extension[1:].upper()} data...')
        load_function(path)
        

    def _load_line_data(self, path):
        """
        Loads line data and re-loads associated aperture and optics data if available.

        Args:
            path (str): The path to the line data file.
        """
        # Preserve previous envelope and first element data if available
        n, first_element = None, None
        if hasattr(self, 'aperture_data'):
            n = self.aperture_data.n
            first_element = getattr(self.aperture_data, 'first_element', None)

        # Load new aperture data
        self.aperture_data = ApertureData(path_b1=path)

        # Make sure not to load the aperture and optics twice
        # So only load if the path was already provided and not changed
        if self.path_aperture and self.path_aperture == self.file_chooser_aperture.selected:
            # Re-load aperture and optics data if selected
            print_and_clear('Re-loading aperture data...')
            self.aperture_data.load_aperture(self.file_chooser_aperture.selected)

        if self.path_optics and self.path_optics == self.file_chooser_optics.selected:
            print_and_clear('Re-loading optics elements...')
            self.aperture_data.load_elements(self.file_chooser_optics.selected)

        # Restore previous envelope and cycle settings
        if n:
            self.aperture_data.envelope(n)
        if first_element:
            self.aperture_data.cycle(first_element)

        # Update UI components
        self.enable_widgets()
        self.update_knob_dropdown()
        self.update_acb_dropdown('beam 1', self.bump_plane_dropdown_b1, self.acb_knob_dropdown_b1)
        self.update_acb_dropdown('beam 2', self.bump_plane_dropdown_b2, self.acb_knob_dropdown_b2)
        self.bump_knob_dropdown.options = self.aperture_data.acbh_knobs_b1['knob']

    def _load_aperture_data(self, path):
        """
        Loads aperture data from the selected file.

        Args:
            path (str): The path to the aperture data file.
        """
        if hasattr(self, 'aperture_data'):
            self.aperture_data.load_aperture(path)
        else:
            print_and_clear('You need to load a line first.')

    def _load_optics_data(self, path):
        """
        Loads optics elements from the selected file.

        Args:
            path (str): The path to the optics data file.
        """
        if hasattr(self, 'aperture_data'):
            self.aperture_data.load_elements(path)
        else:
            print_and_clear('You need to load a line first.')

    def handle_timber_loading(self, data_loader, data_type, update_condition):
        """
        A helper method to handle the loading of BPM or collimator data and updating the graph.
        
        Parameters:
            data_loader: The method responsible for loading the data.
            data_type: A string indicating the type of data being loaded ('BPM' or 'Collimator').
            update_condition: A condition to check if the graph should be updated.
        """
        # Retrieve the selected date and time from the widgets
        selected_date = self.date_picker.value
        selected_time_str = self.time_input.value

        if not selected_date or not selected_time_str:
            print_and_clear(f"Select both a date and a time to load {data_type} data.")
            return

        try:
            # Parse the time string to extract hours, minutes, and seconds
            selected_time = datetime.strptime(selected_time_str, '%H:%M:%S').time()
            combined_datetime = datetime(
                selected_date.year, selected_date.month, selected_date.day,
                selected_time.hour, selected_time.minute, selected_time.second
            )

            # Load data using the provided loader
            data_loader(combined_datetime)

            # Check if the data meets the update condition and update the graph
            if update_condition():
                self.update_graph()
            else:
                print_and_clear(f"{data_type} data not found for the specified time.")

        except ValueError:
            print_and_clear("Invalid time format. Please use HH:MM:SS.")

    def on_load_BPMs_button_clicked(self, b):
        """
        Handle the event when the Load BPMs button is clicked. 
        Parse the date and time inputs, load BPM data, and update the graph if data is available.
        """
        self.handle_timber_loading(
            data_loader=self.BPM_data.load_data,
            data_type='BPM',
            update_condition=lambda: isinstance(self.BPM_data.data, pd.DataFrame)  # Condition to check if BPM data is available
        )

    def on_load_cols_button_clicked(self, b):
        """
        Handle the event when the Load Collimators button is clicked. 
        Parse the date and time inputs, load collimator data, and update the graph if data is available.
        """
        self.handle_timber_loading(
            data_loader=self.collimator_data.load_data,
            data_type='Collimator',
            update_condition=lambda: not all(
                df.empty for df in [
                    self.collimator_data.colx_b1, self.collimator_data.colx_b2, 
                    self.collimator_data.coly_b1, self.collimator_data.coly_b2
                ]
            )  # Condition to check if collimator data is available
        )

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

    def on_apply_changes_button_clicked(self, b):
        """
        Handles the event when the 'Plane' button is clicked.

        This method updates the current plane selection based on the value from the plane dropdown,
        and updates the graph to reflect the change.
        """

        if self.path_line != self.file_chooser_line.selected:
            self.path_line = self.file_chooser_line.selected
            self._handle_load_button_click(
                path = self.path_line,
                expected_extension='.json',
                path_replacement={'b1': 'b2'},
                load_function=self._load_line_data
            )

        if self.path_aperture != self.file_chooser_aperture.selected:
            self.path_aperture = self.file_chooser_aperture.selected
            self._handle_load_button_click(
                path=self.path_aperture,
                expected_extension='.tfs',
                path_replacement={'B1': 'B4'},
                load_function=self._load_aperture_data
            )

        if self.path_optics != self.file_chooser_optics.selected:
            self.path_optics = self.file_chooser_optics.selected
            self._handle_load_button_click(
                path=self.path_optics,
                expected_extension='.tfs',
                path_replacement=None,
                load_function=self._load_optics_data
            )

        if self.check_mismatches():
            # Update knobs dictionary based on current values in the knob widgets
            try:
                for knob, widget in self.knob_widgets.items():
                    self.aperture_data.change_knob(knob, widget.value)

                # Re-twiss
                self.aperture_data.twiss()
            except: 
                print_and_clear('Could not compute twiss. Try again with different knob values.')

        # Retrieve the selected element from the widget
        first_element = self.cycle_input.value
        if first_element != '':
            # First check if changed
            if hasattr(self.aperture_data, 'first_element'): 
                # if this is different than the current one
                if self.aperture_data.first_element != first_element:
                    print_and_clear(f'Setting {first_element} as the first element...')
                    # Cycle
                    self.aperture_data.cycle(first_element)
            # If the first element was not set before, cycle
            else: 
                print_and_clear(f'Setting {first_element} as the first element...')
                self.aperture_data.cycle(first_element)

        # If new, change the size of the envelope
        selected_size = self.envelope_input.value
        if self.aperture_data.n != selected_size:
            print_and_clear(f'Setting envelope size to {selected_size}...')
            self.aperture_data.envelope(selected_size)

        # Switch plane
        selected_plane = self.plane_dropdown.value
        self.plane = selected_plane

        # Update the graph
        self.update_graph()

    def check_mismatches(self):
        # Loop through each widget in the dictionary
        for knob_name, widget in self.knob_widgets.items():
            # Filter the DataFrame to find the row with the matching knob name
            row = self.aperture_data.knobs[self.aperture_data.knobs['knob'] == knob_name]

            # Extract the 'current value' from the DataFrame
            df_current_value = row['current value'].values[0]

            # Compare the widget's value with the DataFrame's 'current value'
            if widget.value != df_current_value:
                # Return True if there is a mismatch
                return True
        # Return False if no mismatches were found
        return False

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
            self.values[knob] = self.aperture_data.knobs[self.aperture_data.knobs['knob']==knob]['current value']  # Initialize knob for new value

            # Create a new FloatText widget for the selected knob
            knob_widget = FloatText(
                value=self.values[knob],
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

    def disable_buttons(self):
        """
        Disables first row controls
        """
        filtered_buttons = [widget for widget in self.widgets if isinstance(widget, Button)]

        for i in filtered_buttons:
            i.disabled = True
        filtered_buttons[3].disabled = False

    def enable_widgets(self):
        """
        Enables all buttons
        """
        for i in self.widgets:
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
            # Disable all butons if the line not loaded
            self.disable_buttons()

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
        
    def create_empty_cross_section(self):
        
        # Create the figure
        fig = go.Figure()

        # Update layout for the figure with custom width and height
        fig.update_layout(
            plot_bgcolor='white',
            xaxis_title='x [m]',
            yaxis_title='y [m]',
            showlegend=False,
            width=450,  # Set the width of the figure
            height=450  # Set the height of the figure
        )

        # Add gridlines for both axes
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgrey', zeroline=True, zerolinewidth=1, zerolinecolor='lightgrey')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgrey', zeroline=True, zerolinewidth=1, zerolinecolor='lightgrey')

        # Set axis limits to -0.05 to 0.05 for both x and y axes
        fig.update_xaxes(range=[-0.05, 0.05])
        fig.update_yaxes(range=[-0.05, 0.05])

        return go.FigureWidget(fig)

    def create_figure(self):
        """
        Create a Plotly figure with multiple traces based on the available attributes.
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
        """
        # Set layout
        self.fig.update_layout(height=self.height, width=self.width, showlegend=False, plot_bgcolor='white')

        # Change x limits and labels
        self.fig.update_xaxes(title_text="s [m]", tickformat=',', row=self.row, col=self.col)

        # Change y limits and labels
        if self.plane == 'horizontal': title = 'x [m]'
        elif self.plane == 'vertical': title = 'y [m]'

        self.fig.update_yaxes(title_text=title, tickformat=',', range = [-0.05, 0.05], row=self.row, col=self.col)

        if hasattr(self, 'aperture_data'): 
            self.fig.update_layout(updatemenus=[
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
            

