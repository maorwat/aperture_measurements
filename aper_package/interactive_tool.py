import numpy as np
import os
import pandas as pd
import copy
from datetime import datetime, date
from typing import Optional, List, Tuple, Any

import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ipywidgets import widgets, Tab, VBox, HBox, Button, Layout, FloatText, DatePicker, Text, Dropdown, Label
from IPython.display import display, Latex
from ipyfilechooser import FileChooser

from aper_package.figure_data import *
from aper_package.timber_data import *
from aper_package.aperture_data import ApertureData

class InteractiveTool():
    
    def __init__(self,
                spark: Optional[Any] = None,
                initial_path: Optional[str] = '/eos/project-c/collimation-team/machine_configurations/', 
                angle_range = (-800, 800)):
        
        """Create and display an interactive plot with widgets for controlling and visualizing data.

        Parameters:
            initial_path: initial path for FileChoosers
            spark: SWAN spark session
            angle_range: range for BPM angle fitting
        """
        # Initially, set all the paths to None
        self.path_line = None
        self.path_aperture = None
        self.path_optics = None

        # Initially, set the plot range from 0 to 26k
        self.plot_range = [0, 26_000]
        # By default show horizontal plane first
        self.plane = 'horizontal'
        
        self.initial_path = initial_path
        self.spark = spark
        self.angle_range = angle_range

        # Create empty plots for the 2D view
        self.cross_section_b1 = self.create_empty_cross_section()
        self.cross_section_b2 = self.create_empty_cross_section()
        self.cross_section_both = self.create_empty_cross_section()

        # Create an empty list to store all of the widgets
        self.widgets = []

        # Put all the widgets together into a nice layout
        self.define_widget_layout()

    def create_file_choosers(self):
        """Create file chooser widgets and corresponding load buttons for the user interface.

        This method creates three file chooser widgets for selecting different types of files
        (line, aperture, and optics) and their corresponding labels.
        """

        # Create filechoosers
        self.file_chooser_line = FileChooser(self.initial_path, layout=Layout(width='350px'))
        self.file_chooser_aperture = FileChooser(self.initial_path, layout=Layout(width='350px'))
        self.file_chooser_optics = FileChooser(self.initial_path, layout=Layout(width='350px'))

        # Add to self.widgets list
        self.widgets.extend([
            self.file_chooser_line, 
            self.file_chooser_aperture, 
            self.file_chooser_optics
        ])

        # Create descriptions for each file chooser
        line_chooser_with_label = HBox([
            Label("Select Line File:"), self.file_chooser_line
        ])
        aperture_chooser_with_label = HBox([
            Label("Select Aperture File:"), self.file_chooser_aperture
        ])
        optics_chooser_with_label = HBox([
            Label("Select Optics File:"), self.file_chooser_optics
        ])

        # Group together
        file_chooser_controls = [
            line_chooser_with_label, 
            aperture_chooser_with_label, 
            optics_chooser_with_label
        ]

        # Create layout for the first row of controls
        file_chooser_layout = HBox(
            file_chooser_controls,
            layout=Layout(
                justify_content="space-around",
                align_items="flex-start",
                width="100%",
                padding="10px",
                border="solid 2px #ccc",
            ),
        )
        
        return file_chooser_layout
    
    def create_knob_controls(self):
        """Create the knob controls for the user interface. 

        This method sets up the necessary containers and widgets to manage knob selections, 
        including a dropdown for selecting knobs and a box to display the selected knobs. 
        It handles the initialization based on whether the `aperture_data` attribute exists 
        and contains valid knob data.
        """
        # Dictionaries and list to store selected knobs, corresponding widgets, and current widget values
        self.selected_knobs = []
        self.knob_widgets = {}
        self.values = {}

        # Create a dropdown to select a knob
        self.knob_dropdown = Dropdown(
                options=[],
                description='Select knob:',
                disabled=False)
            
        # Create a box to store selected knobs
        self.knob_box = VBox(
            layout=Layout(
                justify_content='center',
                align_items='center',
                width='100%',
                padding='10px',
                border='solid 2px #eee'
                )
            )
        
        # Button to add selection
        self.add_button = Button(
            description="Add", 
            style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)'), 
            tooltip='Add the selected knob to the list of adjustable knobs.'
            )

        # Button to reset knobs    
        self.reset_button = Button(
            description="Reset knobs", 
            style=widgets.ButtonStyle(button_color='rgb(255, 242, 174)'), 
            tooltip='Reset all knobs to their default or nominal values.'
            )

        # Assign function to buttons
        self.add_button.on_click(self.on_add_button_clicked)
        self.reset_button.on_click(self.on_reset_button_clicked)

        # Add widgets to the full list
        knob_controls = [
            self.knob_dropdown, 
            self.add_button, 
            self.reset_button
            ]
        self.widgets.extend(knob_controls)

        # Put all together in a hbox
        first_row_layout = HBox(
            knob_controls,
            layout=Layout(
                justify_content='space-around',
                align_items='center',
                width='100%',
                padding='10px',
                border='solid 2px #ccc'))
        
        return first_row_layout

    def on_add_button_clicked(self, b):
        """Handle the event when the Add button is clicked. 
        
        Add a new knob to the selected list and create a widget for it.
        """
        knob = self.knob_dropdown.value  # Knob selected in the dropdown menu

        if not knob or knob in self.selected_knobs:
            return  # Do nothing if knob is empty or already selected

        self.selected_knobs.append(knob)

        # Initialize knob with its current value
        self.values[knob] = self.aperture_data.knobs[
            self.aperture_data.knobs["knob"] == knob
        ]["current value"]

        # Create a FloatText widget for the knob
        knob_widget = FloatText(
            value=self.values[knob],
            description=f"{knob}",
            disabled=False,
        )

        # Create a remove button for the knob
        remove_button = Button(
            description="Remove",
            style={"button_color": "rgb(249, 123, 114)"},
            tooltip="Remove this knob from the list.",
        )

        remove_button.on_click(lambda b, k=knob: self.on_remove_button_clicked(k))

        # Add the widget to the dictionary of knob widgets
        self.knob_widgets[knob] = (knob_widget, remove_button)

        # Update the knob box display
        self.update_knob_box()

    def on_remove_button_clicked(self, knob):
        """Handle the event when the Remove button is clicked.
        
        Remove the selected knob from the list and delete its widget.
        """
        if knob in self.selected_knobs:
            self.selected_knobs.remove(knob)
            del self.values[knob]
            if knob in self.knob_widgets:
                del self.knob_widgets[knob]
            self.update_knob_box()

    def update_knob_box(self):
        """Update the layout of the knob_box with current knob widgets."""
        rows = []
        number_of_knobs_per_line = 4
        for i in range(0, len(self.selected_knobs), number_of_knobs_per_line):
            row_widgets = []
            for knob in self.selected_knobs[i:i + number_of_knobs_per_line]:
                knob_widget, remove_button = self.knob_widgets[knob]
                row_widgets.append(HBox([knob_widget, remove_button], layout=Layout(align_items='center')))
            row = HBox(row_widgets, layout=Layout(align_items='flex-start'))
            rows.append(row)

        self.knob_box.children = rows

    def update_knob_dropdown(self):
        """Update the knob dropdown with 
        a list of knobs read from loaded JSON file.
        """
        # Create a dropdown to select a knob
        self.knob_dropdown.options = self.aperture_data.knobs['knob'].to_list()
        # If spark was given as an argument, also update the dropdown for angle fitting to BPM data
        if self.spark: 
            self.ls_dropdown.options = [
                knob 
                for knob in self.aperture_data.knobs['knob'].to_list() 
                if 'on_x' in knob and 'aux' not in knob or 'on_sep' in knob
                ]

    def create_options_controls(self):
        """Create controls for the third row."""
        # Dropdown to select an IR to show
        self.main_ir_dropdown = Dropdown(
                    options=[
                        'all', 'IR1', 'IR2', 'IR3', 'IR4', 
                        'IR5', 'IR6', 'IR7', 'IR8'
                        ],
                    description='IR:',
                    layout=Layout(width='200px'),
                    disabled=False
                    )
        
        # Text widget to specify cycle start
        self.cycle_input = Text(
            value='',
            description='First element:',
            placeholder='e. g. ip3',
            style={'description_width': 'initial'},
            layout=Layout(width='300px')
            )

        # Input for changing the envelope size
        self.envelope_input = FloatText(
            value=4,
            description='Envelope size [σ]:',
            style={'description_width': 'initial'},
            layout=Layout(width='300px')
            )

        # Dropdown to select a plane
        self.plane_dropdown = Dropdown(
            options=['horizontal', 'vertical'],
            description='Plane:'
            )
        
        # Button to switch between horizontal and vertical planes
        self.apply_changes_button = Button(
            description="Apply changes", 
            style=widgets.ButtonStyle(button_color='pink'))
        
        # Assign method to the button
        self.apply_changes_button.on_click(self.on_apply_changes_button_clicked)

        # Group in a list and add to widget list
        options_controls = [
            self.main_ir_dropdown, 
            self.cycle_input, 
            self.envelope_input, 
            self.plane_dropdown, 
            self.apply_changes_button
            ]
        
        self.widgets.extend(options_controls)

        second_row_layout = HBox(
            options_controls,
            layout=Layout(
                justify_content='space-around',
                align_items='center',
                width='100%',
                padding='10px',
                border='solid 2px #ccc'
                )
            )
        
        return second_row_layout

    def define_main_tab(self):
        """Group all the controls for the main tab into a vbox."""
        # Create layout for the first row of controls
        file_chooser_layout = self.create_file_choosers()
        # Create layout for the first row of controls
        # Corresponds to the knobs for crossing angle and separation bumps
        first_row_layout = self.create_knob_controls()
        # Create layout for the second row of controls
        second_row_layout = self.create_options_controls()

        # Group main controls into a Vbox
        main_vbox = VBox(
            [
            widgets.HTML("<h4>Select and load files</h4>"), 
             file_chooser_layout,
             widgets.HTML("<h4>Select and adjust knobs</h4>"), 
             first_row_layout, 
             self.knob_box, 
             widgets.HTML("<h4>Change line and graph properties</h4>"), 
             second_row_layout
             ],
            layout=Layout(
                justify_content='space-around', # Distribute space evenly
                width='100%',                   # Full width of the container
                padding='10px',                 # Add padding around controls
                border='solid 2px #ccc'       # Border around the HBox
                )
            )

        return main_vbox

    def create_local_bump_controls(self):
        """Create widgets necessary to add a local bump to the line.

        Includes controls to define a bump using kicks 
        given in urad from YASP and then to scale it.
        """
        # Dictionary to hold all created bumps (key: bump_name, value: VBox containing bump details)
        self.bump_dict = {}
        
        # First row
        # Button to define a new bump
        self.define_bump_button = Button(
            description="Define a new bump", 
            style=widgets.ButtonStyle(button_color='pink'))
        # Assign a method
        self.define_bump_button.on_click(self.define_bump)

        # Button to remove al bumps
        self.remove_bumps_button = Button(
            description="Remove all bumps", 
            style=widgets.ButtonStyle(button_color='rgb(255, 242, 174)')
            )
        #Assign a method
        self.remove_bumps_button.on_click(self.on_remove_bumps_button_clicked)

        first_row_controls = [self.define_bump_button, self.remove_bumps_button]
        self.widgets.extend(first_row_controls)

        # First row layout
        first_row_box = widgets.HBox(
            first_row_controls, 
            layout=widgets.Layout(
                justify_content='space-around', 
                align_items='center', 
                width='100%', 
                padding='10px', 
                border='solid 2px #ccc'))
        
        # Second row
        # Dropdown to select the bump to which knobs will be added
        self.bump_selection_dropdown = Dropdown(
            options=[], 
            description="Select Bump:", 
            layout=widgets.Layout(width='200px')
            )
        
        # Dropdowns to sort correctors
        self.sort_knobs_plane_dropdown = Dropdown(
            options=['horizontal', 'vertical'], 
            description="Plane:", 
            layout=widgets.Layout(width='200px')
            )
        
        self.sort_knobs_beam_dropdown = Dropdown(
            options=['beam 1', 'beam 2'], 
            description="Beam:", 
            layout=widgets.Layout(width='200px')
            )
        
        self.sort_knobs_regions_dropdown = Dropdown(
            options=[
                'l1','r1','l2','r2','l3','r3','l4','r4',
                'l5','r5','l6','r6','l7','r7','l8','r8'
                ], 
            description="Region:", 
            layout=widgets.Layout(width='200px')
            )

        # Dropdown to select the corrector
        self.bump_knob_dropdown = Dropdown(
            options=[], 
            description="Corrector:", 
            layout=widgets.Layout(width='200px'))
        
        
        # Observe plane, beam, and region dropdowns to sort
        self.sort_knobs_plane_dropdown.observe(
            self.update_bump_knob_dropdown, names='value'
            )
        self.sort_knobs_beam_dropdown.observe(
            self.update_bump_knob_dropdown, names='value'
            )
        self.sort_knobs_regions_dropdown.observe(
            self.update_bump_knob_dropdown, names='value'
            )

        # Button to add the selected knob
        self.add_bump_knob_button = Button(
            description="Add corrector", 
            layout=widgets.Layout(width='150px'), 
            style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)')
            )
        # Assign a method
        self.add_bump_knob_button.on_click(self.add_knob)

        # Box to store all the bumps definitions, initially empty
        self.main_bump_box = widgets.VBox([])

        second_row_controls = [
            self.bump_selection_dropdown, 
            widgets.HTML("Sort correctors by plane, beam, region:"),
            self.sort_knobs_plane_dropdown, 
            self.sort_knobs_beam_dropdown, 
            self.sort_knobs_regions_dropdown, 
            self.bump_knob_dropdown, 
            self.add_bump_knob_button
            ]
        self.widgets.extend(second_row_controls)

        # Second row layout
        second_row_box = widgets.HBox(
            second_row_controls, 
                layout=widgets.Layout(
                justify_content='space-around', 
                align_items='center', 
                width='100%', 
                padding='10px', 
                border='solid 2px #ccc'
                )
            )

        # Third row
        # Dropdown to select bump for final addition to the line and scaling
        self.final_bump_dropdown = Dropdown(
            options=[], 
            description="Final Bump", 
            layout=widgets.Layout(width='200px')
            )
        
        # Button to add the selected bump to the final container
        self.add_final_bump_button = Button(
            description="Add Bump", 
            layout=widgets.Layout(width='150px'), 
            style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)')
            )
        # Assign a method
        self.add_final_bump_button.on_click(self.add_final_bump)

        # Button to apply operation
        self.bump_apply_button = Button(
            description="Apply", 
            style=widgets.ButtonStyle(button_color='pink'), 
            layout=widgets.Layout(width='150px')
            )
        # Assign a method
        self.bump_apply_button.on_click(self.apply_operation)

        # Container to hold bumps added to the final HBox with floats
        self.final_bump_container = widgets.GridBox(
            [], 
            layout=widgets.Layout(
                grid_template_columns="repeat(4, 500px)", # 4 boxes each 500 px wide
                width='100%'
                )
            )

        # Add all widgets to the list
        third_row_controls = [
            self.final_bump_dropdown, 
            self.add_final_bump_button, 
            self.bump_apply_button
            ]
        self.widgets.extend(third_row_controls)
    
        # Controls for the final bump section
        third_row_box = widgets.HBox(
            third_row_controls, 
            layout=widgets.Layout(
                justify_content='space-around', 
                align_items='center', 
                width='100%', 
                padding='10px', 
                border='solid 2px #ccc'
                )
            )
        
        if self.spark:

            # Range slider to specify s
            self.s_range_yasp_bump_slider = widgets.FloatRangeSlider(
                        value=[0, 26658],
                        min=0.0,
                        max=26658,
                        step=1,
                        description='s range [m]:',
                        continuous_update=False,
                        layout=Layout(width='400px'),
                        readout_format='d'
                        )
                
            self.fit_yasp_bump_button = Button(
                    description="Fit to data", 
                    style=widgets.ButtonStyle(button_color='pink'), 
                    tooltip='Perform least squares fitting.'
                    )

            self.fit_yasp_bump_button.on_click(self.fit_yasp_bump_clicked)  

            # Output with best fit angle and its uncertainty
            self.yasp_bump_result_output = widgets.Output()

            # Add all widgets to the list
            fourth_row_controls = [
                self.s_range_yasp_bump_slider, 
                self.fit_yasp_bump_button, 
                self.yasp_bump_result_output
                ]
            self.widgets.extend(fourth_row_controls)
            
            # Controls for the final bump section
            fourth_row_box = widgets.HBox(
                fourth_row_controls, 
                layout=widgets.Layout(
                    justify_content='space-around', 
                    align_items='center', 
                    width='100%', 
                    padding='10px', 
                    border='solid 2px #ccc'
                    )
                )
        
        else: fourth_row_box = widgets.Output()
        
        return first_row_box, second_row_box, third_row_box, fourth_row_box
    
    def fit_yasp_bump_clicked(self, b):
        
        s_range = self.s_range_yasp_bump_slider.value

        try:
            self.best_fit_yasp_size, self.best_fit_size_yasp_uncertainty = (
                self.BPM_data.yasp_bump_least_squares_fit(
                    self.aperture_data, 
                    s_range, 
                    self.final_bump_container, 
                    self.bump_dict
                    )
                )

            with self.yasp_bump_result_output:
                self.yasp_bump_result_output.clear_output()
                for i, (param, uncertainty) in enumerate(
                    zip(self.best_fit_yasp_size, self.best_fit_size_yasp_uncertainty)
                ):
                    bump_name = self.final_bump_container.children[i].children[0].value
                    print(
                        f"{bump_name}: Best Fit Value = {round(param, 2)}, "
                        f"Uncertainty = {round(uncertainty, 2)}"
                    )
            self.update_graph()
        
        except:
            with self.yasp_bump_result_output:
                self.yasp_bump_result_output.clear_output()
                print(f'Fitting failed')

    def on_remove_bumps_button_clicked(self, b):
        """
        Handles event of clicking Remove all bumps button
        """
        self.aperture_data.reset_all_acb_knobs()
        self.selected_mcbs_hbox.children = ()  # Clear the HBox
        self.selected_mcbs_list.clear()  # Clear the list
        self.update_graph()
        
    def update_bump_knob_dropdown(self, change):
        """Sort the knobs in bump_knob_dropdown by beam and plane."""
        if hasattr(self, 'aperture_data'):
            beam = self.sort_knobs_beam_dropdown.value
            plane = self.sort_knobs_plane_dropdown.value
            region = self.sort_knobs_regions_dropdown.value

            self.bump_knob_dropdown.options = self.aperture_data.sort_acb_knobs_by_region(beam, plane, region)

    def define_bump(self, b):
        """Define a new bump with kicks."""
        bump_name = f"Bump {len(self.bump_dict) + 1}"  # Unique bump name
        # Create a dropdown to specify to which beam the bump should be applied
        beam_dropdown = widgets.Dropdown(
            options=['beam 1', 'beam 2'], 
            description=f'{bump_name}: Beam', 
            layout=widgets.Layout(width='400px'), 
            style={'description_width': '150px'}
            )

        # Container for knobs in a grid
        knob_container = widgets.GridBox(
            [], 
            layout=widgets.Layout(
                grid_template_columns="repeat(4, 400px)", # 4 boxes each 400 px wide
                width='100%'
                )
            ) 

        # Create the HBox for each bump (beam + knobs) 
        bump_definition_vbox = widgets.HBox(
            [beam_dropdown, knob_container], 
            layout=widgets.Layout(
                width='100%', 
                padding='10px', 
                border='solid 2px #ccc'
                )
            )

        # Add the new bump to the main box
        # Box with all the define bumps
        self.main_bump_box.children += (bump_definition_vbox,)

        # Store the bump in the dictionary
        self.bump_dict[bump_name] = {
            'vbox': bump_definition_vbox,
            'knobs': knob_container,
            'added_knobs': [],  # List to track added knobs
            'float_inputs': []  # List to store float inputs for each knob
        }

        # Update the bump selection dropdown to include the new bump
        # Dropdown to select where the selected knobs will be added
        self.bump_selection_dropdown.options = list(self.bump_dict.keys())
        # Dropdown to select which bumps to apply to the line
        # Update the dropdown for the final section
        self.final_bump_dropdown.options = list(self.bump_dict.keys())
        
    def add_knob(self, b):
        """Add a knob to the bump definition."""
        # Which bump to add the new knob to
        selected_bump = self.bump_selection_dropdown.value
        # Get knob name from the dropdown selection
        knob_name = self.bump_knob_dropdown.value

        # Check if the knob is already added
        if knob_name not in self.bump_dict[selected_bump]['added_knobs']:
            # Create a widget to specify the kick
            float_input = widgets.FloatText(
                description=knob_name, 
                layout=widgets.Layout(width='200px')
                )
            # Button to remove the knob from the selected
            remove_button = widgets.Button(
                description="Remove", 
                style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'), 
                layout=widgets.Layout(width='100px')
                )

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

            # Group the float and button in a HBox
            knob_hbox = widgets.HBox(
                [float_input, remove_button], 
                layout=widgets.Layout(
                    width='100%',
                    padding='5px',
                    align_items='center'
                    )
                )
            remove_button.on_click(remove_knob)

            # Add the knob to the corresponding bump's knob container
            self.bump_dict[selected_bump]['knobs'].children += (knob_hbox,)

            # Add the knob to the added_knobs list and float_inputs list
            self.bump_dict[selected_bump]['added_knobs'].append(knob_name)
            self.bump_dict[selected_bump]['float_inputs'].append(float_input)
            
    def add_final_bump(self, b):
        """Add a bump for final calculation - scaling of the defined kick."""
        selected_bump = self.final_bump_dropdown.value
        # Check if already added
        if selected_bump and selected_bump not in [
            child.children[0].value 
            for child in self.final_bump_container.children
            ]:
            # Create a float input and a remove button
            float_input = widgets.FloatText(
                description="Value", 
                layout=widgets.Layout(width='200px')
                )
            remove_button = widgets.Button(
                description="Remove", 
                style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'), 
                layout=widgets.Layout(width='100px')
                )

            # Create HBox with bump dropdown and float input
            bump_hbox = widgets.HBox(
                [widgets.Label(
                    selected_bump, 
                    layout=widgets.Layout(width='50px', align_items='center')
                    ), float_input, remove_button], 
                layout=widgets.Layout(
                    width='400px', 
                    padding='5px', 
                    align_items='center'
                    )
                )

            # Function to remove bump from final container
            def remove_bump(btn):
                self.final_bump_container.children = [
                    child 
                    for child in self.final_bump_container.children 
                    if child is not bump_hbox
                    ]

            remove_button.on_click(remove_bump)
            self.final_bump_container.children += (bump_hbox,)
            
    def apply_operation(self, b):
        """Add the bumps in final_bump_container to the line."""
        # Iterate over all bumps in the container
        for bump_hbox in self.final_bump_container.children:
            bump_name = bump_hbox.children[0].value
            bump_float_value = bump_hbox.children[1].value

            float_inputs = self.bump_dict[bump_name]['float_inputs']
            selected_beam = self.bump_dict[bump_name]['vbox'].children[0].value  # Get the selected beam

            # Iterate over all knobs in the bump definition and scale them accordingly    
            for i in float_inputs:
                self.aperture_data.change_acb_knob(i.description, i.value*bump_float_value*1e-6, selected_beam)
        
        # Twiss and update the graph
        self.aperture_data.twiss()
        self.update_graph()
    
    def define_local_bump_tab(self):
        """Group all the widgets for the local bump into one vbox."""
        first_row_box, second_row_box, third_row_box, fourth_row_box = self.create_local_bump_controls()

        if self.spark:
            local_bump_controls = [
                widgets.HTML("<h4>Define and configure bumps</h4>"),
                first_row_box,
                second_row_box,
                self.main_bump_box,
                widgets.HTML("<h4>Select bumps for final calculation</h4>"),
                third_row_box,
                self.final_bump_container,
                widgets.HTML("<h4>Perform least-squares fitting</h4>"),
                fourth_row_box
                ]

        else:
            local_bump_controls = [
                widgets.HTML("<h4>Define and configure bumps</h4>"),
                first_row_box,
                second_row_box,
                self.main_bump_box,
                widgets.HTML("<h4>Select bumps for final calculation</h4>"),
                third_row_box,
                self.final_bump_container
                ]

        # Display the layout
        local_bump_box = widgets.VBox(
            local_bump_controls, 
            layout=widgets.Layout(
                border='solid 2px #ccc', 
                padding='10px', 
                width='100%'
                )
            )
        
        return local_bump_box
    
    def create_bump_matching_controls(self):
        """Create widgets for adding a local bump with line.match."""
        # Input to type the element at wchich the peak of the bump is
        self.local_bump_element_input = Text(
            value='',                               # Initial value (empty string)
            description='Element:',                 # Label for the widget       
            style={'description_width': 'initial'}, # Adjust the width of the description label
            layout=Layout(width='200px')
            )  
        
        # Input to type the size of the bump
        self.bump_size_input = FloatText(
            description=r"Bump size [mm]:",    
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='200px')
            ) 

        first_row_controls = [
            self.local_bump_element_input, 
            self.bump_size_input, 
            self.remove_bumps_button
            ]
        self.widgets.extend(first_row_controls)
        
        # Controls for the final bump section
        first_row_box = widgets.HBox(
            first_row_controls, 
            layout=widgets.Layout(
                justify_content='space-around', 
                align_items='center', 
                width='100%', 
                padding='10px', 
                border='solid 2px #ccc')
                )
          
        # Dropdown to sort mcbs by beam
        self.sort_mcbs_beam_dropdown = Dropdown(
            options=['beam 1', 'beam 2'], 
            description='Beam:', 
            layout=widgets.Layout(width='200px')
            )
        # Dropdown to sort mcbs by plane
        self.sort_mcbs_plane_dropdown = Dropdown(
            options=['horizontal', 'vertical'], 
            description='Plane:', 
            layout=widgets.Layout(width='200px')
            )
        # Dropdown to sort mcbs by region
        self.sort_mcbs_regions_dropdown = Dropdown(
            options=['l1','r1','l2','r2','l3','r3','l4','r4','l5','r5','l6','r6','l7','r7','l8','r8'], 
            description="Region:", 
            layout=widgets.Layout(width='200px')
            )
        
        # Observe plane, beam, and region dropdowns to sort
        self.sort_mcbs_plane_dropdown.observe(self.update_bump_mcbs_dropdown, names='value')
        self.sort_mcbs_beam_dropdown.observe(self.update_bump_mcbs_dropdown, names='value')
        self.sort_mcbs_regions_dropdown.observe(self.update_bump_mcbs_dropdown, names='value')
        
        # Dropdown to select mcbs
        self.mcbs_dropdown = Dropdown(
            options=[], 
            description="Corrector:", 
            layout=widgets.Layout(width='200px')
            )
        
        # Button to add the selected mcbs to the container
        self.add_mcbs_button = Button(
            description="Add corrector", 
            layout=widgets.Layout(width='150px'), 
            style=widgets.ButtonStyle(button_color='rgb(179, 222, 105)')
            )
        # Assign a method
        self.add_mcbs_button.on_click(self.add_mcbs_button_clicked)

        # Create an HBox to display selected correctors
        self.selected_mcbs_hbox = HBox(
            layout=widgets.Layout(
                width='100%', 
                padding='10px', 
                border='solid 2px #ccc')
                )
        self.selected_mcbs_list = []  # List to keep track of selected correctors

        # Button to perform matching
        self.match_button = Button(
            description="Match", 
            style=widgets.ButtonStyle(button_color='pink')
            )
        # Assign a function
        self.match_button.on_click(self.match_button_clicked)  

        second_row_controls = [
            self.sort_mcbs_beam_dropdown, 
            self.sort_mcbs_plane_dropdown, 
            self.sort_mcbs_regions_dropdown,
            self.mcbs_dropdown, 
            self.add_mcbs_button, 
            self.match_button
            ]
        self.widgets.extend(second_row_controls)
        
        # Controls for the final bump section
        second_row_box = widgets.HBox(
            second_row_controls, 
            layout=widgets.Layout(
                justify_content='space-around', 
                align_items='center', 
                width='100%', 
                padding='10px', 
                border='solid 2px #ccc'
                )
            )
        
        if self.spark:

            # Input to type the size of the bump
            self.initial_guess_bump_size_input = FloatText(
                description=r"Initial guess [mm]:",    
                style={'description_width': 'initial'},
                layout=widgets.Layout(width='200px')
                ) 
            
            # Range slider to specify s
            self.s_range_local_bump_slider = widgets.FloatRangeSlider(
                        value=[0, 26658],
                        min=0.0,
                        max=26658,
                        step=1,
                        description='s range [m]:',
                        continuous_update=False,
                        layout=Layout(width='400px'),
                        readout_format='d'
                        )
            
            # Range slider to specify s
            self.local_bump_size_range_slider = widgets.FloatRangeSlider(
                        value=[-20, 20],
                        min=-20.0,
                        max=20.0,
                        step=1,
                        description='Bump size range [mm]:',
                        continuous_update=False,
                        layout=Layout(width='400px'),
                        readout_format='d'
                        )
                
            self.fit_local_bump_button = Button(
                    description="Fit to data", 
                    style=widgets.ButtonStyle(button_color='pink'), 
                    tooltip='Perform least squares fitting.'
                    )

            self.fit_local_bump_button.on_click(self.fit_local_bump_clicked)  

            # Output with best fit angle and its uncertainty
            self.local_bump_result_output = widgets.Output()

            third_row_controls = [
                self.initial_guess_bump_size_input, 
                self.s_range_local_bump_slider,
                self.local_bump_size_range_slider, 
                self.fit_local_bump_button, 
                self.local_bump_result_output
                ]
            self.widgets.extend(third_row_controls)

            third_row_box = widgets.HBox(
            third_row_controls, 
            layout=widgets.Layout(
                justify_content='space-around', 
                align_items='center', 
                width='100%', 
                padding='10px', 
                border='solid 2px #ccc')
                )
            
        else:
            # Just a place holder is spark was not given
            third_row_box = widgets.Output()
        
        return first_row_box, second_row_box, third_row_box    

    def fit_local_bump_clicked(self, b):

        init_size = self.initial_guess_bump_size_input.value
        s_range = self.s_range_local_bump_slider.value
        element = self.local_bump_element_input.value
        beam = self.sort_mcbs_beam_dropdown.value
        plane = self.sort_mcbs_plane_dropdown.value
        relevant_mcbs = self.selected_mcbs_list
        size_range = self.local_bump_size_range_slider.value

        try:
            self.best_fit_size, self.best_fit_size_uncertainty = (
                self.BPM_data.local_bump_least_squares_fit(
                    element,
                    self.aperture_data,
                    init_size,
                    relevant_mcbs,
                    beam,
                    plane,
                    size_range, 
                    s_range
                    )
                )

            with self.local_bump_result_output:
                self.local_bump_result_output.clear_output()  # Clear previous output
                print(f'Best fit angle: {self.best_fit_size} Uncertainty: {self.best_fit_size_uncertainty}')

            self.update_graph()
        
        except:
            with self.local_bump_result_output:
                self.local_bump_result_output.clear_output()  # Clear previous output
                print(f'Fitting failed')

    def update_bump_mcbs_dropdown(self, change):
        """Sort the knobs in bump_knob_dropdown by beam and plane."""
        if hasattr(self, 'aperture_data'):
            beam = self.sort_mcbs_beam_dropdown.value
            plane = self.sort_mcbs_plane_dropdown.value
            region = self.sort_mcbs_regions_dropdown.value

            self.mcbs_dropdown.options = self.aperture_data.sort_mcbs_by_region(beam, plane, region)
    
    def match_button_clicked(self, b):

        element = self.local_bump_element_input.value
        size = self.bump_size_input.value
        beam = self.sort_mcbs_beam_dropdown.value
        plane = self.sort_mcbs_plane_dropdown.value

        update = self.aperture_data.match_local_bump(
            element, self.selected_mcbs_list, 
            size, beam, plane)
        if update: self.update_graph()

    def add_mcbs_button_clicked(self, b):

        corrector_name = self.mcbs_dropdown.value

        if corrector_name not in self.selected_mcbs_list:
            self.selected_mcbs_list.append(corrector_name)
            # Create a horizontal box for the corrector label and its remove button
            corrector_box = HBox(
                [Label(
                    value=corrector_name,
                    layout=Layout(
                        width='150px',
                        margin='5px',
                        padding='5px',
                        border='solid 1px #ccc',
                        border_radius='5px',
                        display='flex',
                        justify_content='center',
                        align_items='center'
                        )
                    ),
                # Create a remove button for the specific corrector
                Button(
                    description='Remove',
                    style=widgets.ButtonStyle(button_color='rgb(249, 123, 114)'),
                    layout=Layout(margin='5px')
                    )
                ]
            )
            
            # Add event handler for the remove button
            corrector_box.children[1].on_click(lambda b, name=corrector_name: self.remove_corrector(name, corrector_box))
            # Add the corrector box to HBox
            self.selected_mcbs_hbox.children += (corrector_box,)
    
    def remove_corrector(self, corrector_name, corrector_box):
        """Function to remove the specified corrector from the HBox and list."""
        self.selected_mcbs_hbox.children = [
            box 
            for box in self.selected_mcbs_hbox.children 
            if box.children[0].value != corrector_name
            ]  # Remove from HBox
        self.selected_mcbs_list.remove(corrector_name)

    def define_bump_matching_tab(self):
        """Group all the widgets for the local bump into one vbox."""
        first_row_box, second_row_box, third_row_box = self.create_bump_matching_controls()

        if self.spark: 
            bump_matching_controls = [
                widgets.HTML("<h4>Add a local bump using line.match</h4>"),
                first_row_box, second_row_box, 
                widgets.HTML("<h4>Correctors to be varied for matching</h4>"),
                self.selected_mcbs_hbox,
                widgets.HTML("<h4>Perform least-squares fitting</h4>"),
                third_row_box
                ]
        else: 
            bump_matching_controls = [
                widgets.HTML("<h4>Add a local bump using line.match</h4>"),
                first_row_box, second_row_box, 
                widgets.HTML("<h4>Correctors to be varied for matching</h4>"),
                self.selected_mcbs_hbox
                ]

        # Display the layout
        bump_matching_box = widgets.VBox(
            bump_matching_controls,
            layout=widgets.Layout(
                border='solid 2px #ccc', 
                padding='10px', 
                width='100%'
                )
            )
            
        return bump_matching_box

    def create_2d_plot_controls(self):
        """Create widgets for the cross-section."""
        # First row
        # Element at which the cross-section will be visualised
        self.element_input = Text(
            value='',
            description='Element:',
            placeholder='e. g. mq.21l3.b1',
            style={'description_width': 'initial'},
            layout=Layout(width='200px')
            )  
        
        self.aper_tolerances_dropdown = Dropdown(
            options=['Default aperture tolerances', 'Customise aperture tolerances'],
            description=''
            )
        # Assign a method to add a row for aper tolerances inputs
        self.aper_tolerances_dropdown.observe(self.toggle_aper_tols, names='value')

        # Group into a hbox and add to widgets
        first_row_controls = [self.element_input, self.aper_tolerances_dropdown]
        self.widgets.extend(first_row_controls)

        element_and_aper_toggle = widgets.HBox(
            first_row_controls, 
            layout=widgets.Layout(
                padding='5px', 
                justify_content='space-around'
                )
            )

        # Second row
        # Widgets for n1 calculations
        self.delta_co_input = FloatText(
            description=r"$\Delta$co [m]", 
            layout=widgets.Layout(width='200px'), 
            value=0.002
            )  
        self.delta_beta_input = FloatText(
            description=r"$\Delta \beta$ [%]", 
            layout=widgets.Layout(width='200px')
            ) 
        self.delta_input = FloatText(
            description=r"$\delta$", 
            layout=widgets.Layout(width='200px')
            ) 
        
        # Aperture tolerances, only visible if 'Customise aperture tolerances' selected
        self.rtol_input = FloatText(
            description="rtol [m]", 
            layout=widgets.Layout(width='200px')
            ) 
        self.xtol_input = FloatText(
            description="xtol [m]", 
            layout=widgets.Layout(width='200px')
            ) 
        self.ytol_input = FloatText(
            description="ytol [m]", 
            layout=widgets.Layout(width='200px')
            ) 
        
        error_controls = [
            self.delta_co_input, 
            self.delta_beta_input, 
            self.delta_input
            ]
        aper_tols_controls = [
            self.rtol_input, 
            self.xtol_input, 
            self.ytol_input
            ]
        self.widgets.extend(error_controls+aper_tols_controls)
        
        # Group into a hbox
        error_inputs = HBox(
            error_controls, 
            layout=widgets.Layout(padding='5px', justify_content='space-around')
            )
        self.tol_inputs = HBox(
            aper_tols_controls, 
            layout=widgets.Layout(padding='5px', justify_content='space-around')
            )
        # Initially hide the HBox
        self.tol_inputs.layout.display = 'none'
        
        # Third row
        # Droptdown to select for which beam n1 is calculated
        self.beam_dropdown_for_n1 = Dropdown(
            options=['beam 1', 'beam 2'], 
            description='Beam:', 
            layout=widgets.Layout(width='200px')
            )
        
        # Button to calculate n1
        self.calculate_n1_button = Button(
            description="Calculate n1", 
            style=widgets.ButtonStyle(button_color='pink')
            )
        # Assign a function
        self.calculate_n1_button.on_click(self.calculate_n1_button_clicked)  

        # Output with n1 result
        self.n1_output = widgets.Output()
        with self.n1_output:
            display(Latex(f'Horizontal: $n_1 = $ Vertical: $n_1 = $ '))

        n1_controls = [
            self.beam_dropdown_for_n1, 
            self.calculate_n1_button, 
            self.n1_output
            ]
        self.widgets.extend(n1_controls)
        n1_button_and_output = widgets.HBox(
            n1_controls, 
            layout=widgets.Layout(padding='5px', justify_content='space-around')
            )

        # Last row
        # Switch to toggle between showing errors on the 2d view graph and not
        self.toggle_switch = widgets.ToggleButton(
            value=False,
            description='Errors not shown',
            disabled=False,
            button_style='',
            tooltip='Toggle me',
            icon='times'
            )
        # Observe changes in the toggle button
        self.toggle_switch.observe(self.on_toggle_change, 'value')
        
        # Button to generate a new plot
        self.generate_2d_plot_button = Button(
            description="Generate", 
            style=widgets.ButtonStyle(button_color='pink'), 
            tooltip='Generate a new plot of the 2D view'
            )
        # Button to add a new trace to the existing plot
        self.add_trace_to_2d_plot_button = Button(
            description="Add trace", 
            style=widgets.ButtonStyle(button_color='pink'), 
            tooltip='Add a 2D view to the existing plot'
            )  
        # Assign functions to the buttons
        self.generate_2d_plot_button.on_click(self.generate_2d_plot_button_clicked)
        self.add_trace_to_2d_plot_button.on_click(self.add_trace_to_2d_plot_button_clicked)    
        
        # Add to self.widgets and group into a hbox
        last_row_controls = [
            self.toggle_switch, 
            self.generate_2d_plot_button, 
            self.add_trace_to_2d_plot_button
            ]
        self.widgets.extend(last_row_controls)

        add_and_generate_2d_plot_buttons = HBox(
            last_row_controls, 
            layout=widgets.Layout(
                align_items='stretch', 
                justify_content='space-around', 
                width='600px'
                )
            )
        
        # Group main controls into a Vbox
        cross_section_vbox = VBox(
            [
            widgets.HTML("<h4>Show 2D view at the specified element</h4>"), 
            element_and_aper_toggle, 
            error_inputs, 
            self.tol_inputs, 
            n1_button_and_output, 
            add_and_generate_2d_plot_buttons
            ],
            layout=Layout(
                justify_content='space-around',
                align_items='center',
                width='40%',
                padding='0px',
                    border='solid 2px #ccc'
                )   
            )    
        return cross_section_vbox

    def toggle_aper_tols(self, change):
        """Toggle the display of aperture tolerance inputs 
        based on user selection.
        """
        self.tol_inputs.layout.display = (
            "flex" if change["new"] == "Customise aperture tolerances" else "none"
        )

    def on_toggle_change(self, change):
        """Update the toggle switch description and icon based on its state."""
        self.toggle_switch.description = (
            "Errors shown" if self.toggle_switch.value else "Errors not shown"
        )
        self.toggle_switch.icon = "check" if self.toggle_switch.value else "times"

    def calculate_n1_button_clicked(self, b):
        """Calculate the n1 values and display them 
        if aperture data is available.
        """
        if not hasattr(self.aperture_data, "aper_b1"):
            self.progress_label.value = "Load the aperture data"
            return

        beam = self.beam_dropdown_for_n1.value
        delta_beta = self.delta_beta_input.value
        delta = self.delta_input.value
        element = self.element_input.value
        delta_co = self.delta_co_input.value

        # Set aperture tolerances
        if self.aper_tolerances_dropdown.value == "Customise aperture tolerances":
            rtol = self.rtol_input.value
            xtol = self.xtol_input.value
            ytol = self.ytol_input.value
        else:
            rtol, xtol, ytol = None, None, None

        try:
            _, _, n1_x, _, _, n1_y = self.aperture_data.calculate_n1(
                delta_beta, delta, beam, element, rtol, xtol, ytol, delta_co
            )

            with self.n1_output:
                self.n1_output.clear_output()  # Clear previous output
                display(
                    Latex(
                        f"Horizontal: $n_1 =$ {n1_x:.2f}$\sigma$ "
                        f"Vertical: $n_1 =$ {n1_y:.2f}$\sigma$"
                    )
                )
        except Exception as e:
            with self.n1_output:
                self.n1_output.clear_output()
                display(Latex("Incorrect element"))

    def add_trace_to_2d_plot_button_clicked(self, b):
        """Add a trace to the existing cross-section."""
        n = self.aperture_data.n
        element = self.element_input.value

        if self.toggle_switch.value:
            delta_beta = self.delta_beta_input.value
            delta = self.delta_input.value
        else: delta, delta_beta = 0, 0
        
        # Update the cross-section attributes
        # Beam 1
        traces_b1 = add_beam_trace(element, 'beam 1', self.aperture_data, 
                                   n, delta_beta=delta_beta, delta=delta)
        for i in traces_b1[:3]:
            self.cross_section_b1.add_trace(i)
            self.cross_section_both.add_trace(i)

        # Beam 2
        traces_b2 = add_beam_trace(element, 'beam 2', self.aperture_data, 
                                   n, delta_beta=delta_beta, delta=delta)
        for i in traces_b2[:3]:
            self.cross_section_b2.add_trace(i)
            self.cross_section_both.add_trace(i)

        self.cross_section_container.children = [
            self.cross_section_b1, 
            self.cross_section_b2, 
            self.cross_section_both
            ]
    
    def generate_2d_plot_button_clicked(self, b):
        """Create a new cross-section based on the current state of the line."""
        
        n = self.aperture_data.n
        element = self.element_input.value

        # Set aperture tolerances
        if self.aper_tolerances_dropdown.value == "Customise aperture tolerances":
            rtol = self.rtol_input.value
            xtol = self.xtol_input.value
            ytol = self.ytol_input.value
        else:
            rtol, xtol, ytol = None, None, None

        # Set delta values
        if self.toggle_switch.value:
            delta_beta = self.delta_beta_input.value
            delta = self.delta_input.value
            delta_co = self.delta_co_input.value
        else:
            delta_beta, delta, delta_co, rtol, xtol, ytol = 0, 0, 0, 0, 0, 0

        self.progress_label.value = "Generating the cross-section..."

        # Generate and store cross-sections
        self.cross_section_b1 = generate_2d_plot(
            element, "beam 1", self.aperture_data, n,
            rtol, xtol, ytol, delta_beta, delta, delta_co, 450, 450
        )
        self.cross_section_b2 = generate_2d_plot(
            element, "beam 2", self.aperture_data, n,
            rtol, xtol, ytol, delta_beta, delta, delta_co, 450, 450
        )
        self.cross_section_both = generate_2d_plot(
            element, "both", self.aperture_data, n,
            rtol, xtol, ytol, delta_beta, delta, delta_co, 450, 450
        )

        self.cross_section_container.children = [
            self.cross_section_b1,
            self.cross_section_b2,
            self.cross_section_both
        ]
    
    def define_2d_view_tab(self):
        """Group all the widgets for the 2d view into one hbox"""
        cross_section_vbox = self.create_2d_plot_controls()
        
        self.cross_section_container = HBox(
            [self.cross_section_b1, self.cross_section_b2, self.cross_section_both],
            layout=Layout(
                justify_content='center',
                align_items='center',
                width='80%',
                padding='0px',
                border='solid 2px #eee'
                )
            )
        
        full_cross_section_box = HBox(
            [cross_section_vbox, self.cross_section_container],
            layout=Layout(
                justify_content='center',
                align_items='stretch',
                width='100%',
                padding='0px 10px',
                border='solid 2px #ccc'
                )
            )

        return full_cross_section_box
    
    def create_time_widgets(self):
        """Create and configure date and time input widgets."""
        # Create date and time input widgets
        self.date_picker = DatePicker(
                description='Select Date:',
                value=date.today(),
                style={'description_width': 'initial'},
                layout=Layout(width='300px')
                )
        
        self.time_input = Text(
                description='Enter Time (HH:MM:SS):',
                value=datetime.now().strftime('%H:%M:%S'),
                placeholder='10:53:15',
                style={'description_width': 'initial'},
                layout=Layout(width='300px')
                )
        
    def initialise_timber_data(self):
        """Initialize timber-related data and 
        UI components if the `spark` attribute is provided.

        This method sets up UI elements and data handlers 
        for interacting with timber data. 
        If the `spark`  Update UI components
        """
        # Only add timber buttons if spark given as an argument

        self.collimator_data = CollimatorsData(self.spark, label=self.progress_label)
        self.BPM_data = BPMData(self.spark, label=self.progress_label)
            
        # Time selection widgets
        self.create_time_widgets()
        # Button to load BPM data
        self.load_BPMs_button = Button(
                description="Load BPMs",
                style=widgets.ButtonStyle(button_color='pink'),
                tooltip='Load BPM data from timber for the specified time.'
                )
        self.load_BPMs_button.on_click(self.on_load_BPMs_button_clicked)
        # Button to load collimator data
        self.load_cols_button = Button(
                description="Load collimators",
                style=widgets.ButtonStyle(button_color='pink'),
                tooltip='Load collimator data from timber for the specified time.'
                )
        self.load_cols_button.on_click(self.on_load_cols_button_clicked)

        # Define layout depending if timber buttons present or not
        timber_row_controls = [
            self.date_picker,
            self.time_input,
            self.load_cols_button,
            self.load_BPMs_button
            ]
        self.widgets.extend(timber_row_controls)

        timber_row_layout = HBox(
                timber_row_controls,
                layout=Layout(
                    justify_content='space-around',
                    align_items='center',
                    width='100%',
                    padding='10px',
                    border='solid 2px #ccc'
                    )
                )
        return timber_row_layout

    def create_ls_controls(self):
        """Initialise controls for least squares fitting line into BPM data."""
        # Dropdown to select which angle to vary in the optimisation
        self.ls_dropdown = Dropdown(
                    options=[],
                    description='Knob to vary:',
                    layout=Layout(width='200px'),
                    disabled=False
                    )
                
        # Float box to input the inital guess 
        self.init_angle_input = FloatText(
                    value=0,
                    description='Initial guess:',
                    style={'description_width': 'initial'},
                    layout=Layout(width='150px')
                    )
        # Dropdown to select IR for fitting
        self.ir_dropdown = Dropdown(
                    options=['IR1', 'IR2', 'IR3', 'IR4', 'IR5', 'IR6', 'IR7', 'IR8', 'other'],
                    description='IR:',
                    layout=Layout(width='200px'),
                    disabled=False
                    )
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
                tooltip='Perform least squares fitting.')
        self.fit_button.on_click(self.on_fit_button_clicked
                                 )

        # Output with best fit angle and its uncertainty
        self.result_output = widgets.Output()

        # Group controls and append to all widgets
        ls_row_controls = [
            self.ls_dropdown, 
            self.init_angle_input, 
            self.ir_dropdown, 
            self.s_range_slider, 
            self.fit_button, 
            self.result_output]
        self.widgets.extend(ls_row_controls)

        # Create layout for the timber row of controls
        ls_row_layout = HBox(
                ls_row_controls,
                layout=Layout(
                    justify_content='space-around',
                    align_items='center',
                    width='100%',
                    padding='10px',
                    border='solid 2px #ccc'
                    )
                )
        
        return ls_row_layout

    def on_ir_dropdown_change(self, change):
        """Handle event when ir dropdown was changed."""
        if change['new'] == 'other':
            self.s_range_slider.disabled = False
        else:
            self.s_range_slider.disabled = True

    def on_fit_button_clicked(self, b):
        """Handle event when button Fit to data is clicked"""
        init_angle = self.init_angle_input.value
        knob = self.ls_dropdown.value
        ir=self.ir_dropdown.value
        
        if ir == 'other': 
            s_range = self.s_range_slider.value
        else: 
            s_range = self.aperture_data.get_ir_boundries(ir)        

        if s_range[0]>s_range[1]: 
            self.progress_label.value = 'Try cycling the graph first so that the IR is not on the edge.'
        else: 
            self.best_fit_angle, self.best_fit_uncertainty = (
                self.BPM_data.least_squares_fit(
                    self.aperture_data, 
                    init_angle, knob, 
                    self.plane, 
                    self.angle_range, 
                    s_range
                    )
                )

            with self.result_output:
                self.result_output.clear_output()  # Clear previous output
                print(f'Best fit angle: {self.best_fit_angle} Uncertainty: {self.best_fit_uncertainty}')

            self.update_graph()

    def define_ls_tab(self):
        """Group all the widgets for the least squares fitting
        and timber data into one vbox.
        """
        # Create layout for the timber row of controls
        timber_row_layout = self.initialise_timber_data()

        # Create layout for the timber row of controls
        ls_row_layout = self.create_ls_controls()
            
        # Group timber controls into a Vbox
        spark_vbox = VBox(
            [
            widgets.HTML("<h4>Load collimator and BPM data</h4>"),
            timber_row_layout, 
            widgets.HTML("<h4>Perform least-squares fitting</h4>"),
            ls_row_layout
            ],
            layout=Layout(
                justify_content='space-around',
                width='100%',
                padding='10px',
                border='solid 2px #ccc'
                )   
            )
        return spark_vbox
        
    def define_widget_layout(self):
        """Define and arrange the layout of the widgets."""
        self.progress_label = Label(
            value='',
            width='100%',
            layout=widgets.Layout(justify_content='flex-start')
        )
        
        # Main tab 
        main_vbox = self.define_main_tab()

        # Local bump tab
        define_local_bump_box = self.define_local_bump_tab()
        bump_matching_box = self.define_bump_matching_tab()
        
        # 2D view and error calculation tab
        full_cross_section_box = self.define_2d_view_tab()
        
        if self.spark: 
            spark_vbox = self.define_ls_tab()

            # Create an accordion to toggle visibility of controls
            tab = Tab(
                children=[
                    main_vbox, 
                    define_local_bump_box, 
                    bump_matching_box, 
                    full_cross_section_box, 
                    spark_vbox
                    ]
                )
            tab.set_title(4, 'Timber data')

        else: 
            self.collimator_data, self.BPM_data = None, None
            tab = Tab(
                children=[
                    main_vbox, 
                    define_local_bump_box, 
                    bump_matching_box, 
                    full_cross_section_box
                    ]
                )
            
        tab.set_title(0, 'Main')
        tab.set_title(1, 'Define local bump')
        tab.set_title(2, 'Match local bump')
        tab.set_title(3, '2D view')
        tab.layout.width = '100%'

        self.graph_container = HBox(
            layout=Layout(
                justify_content='center',
                align_items='center',
                width='100%',
                padding='10px',
                border='solid 2px #eee'
                )
            )
        
        full_column = [tab, self.progress_label, self.graph_container]

        # Combine both rows, knob box, and graph container into a VBox layout
        self.full_layout = VBox(
            full_column,
            layout=Layout(
                align_items='flex-start',       # Center align all items vertically
                width='100%',                   # Limit width to 80% of the page
                margin='0 auto',                # Center the VBox horizontally
                padding='20px',                 # Add p0dding around the whole container
                border='solid 2px #ddd'         # Border around the VBox
                )
            )

    def handle_timber_loading(self, data_loader, data_type, update_condition):
        """Handle the loading of BPM or collimator data and updating the graph.
        
        Parameters:
            data_loader: The method responsible for loading the data.
            data_type: A string indicating the type of data being loaded ('BPM' or 'Collimator').
            update_condition: A condition to check if the graph should be updated.
        """
        # Retrieve the selected date and time from the widgets
        selected_date = self.date_picker.value
        selected_time_str = self.time_input.value

        if (not selected_date or 
            not selected_time_str):
            self.progress_label.value = f"Select both a date and a time to load {data_type} data."
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
                self.progress_label.value = f"{data_type} data not found for the specified time."

        except ValueError:
            self.progress_label.value = "Invalid time format. Please use HH:MM:SS."

    def on_load_BPMs_button_clicked(self, b):
        """Handle the event when the Load BPMs button is clicked. 
        
        Parse the date and time inputs, load BPM data, 
        and update the graph if data is available.
        """
        self.handle_timber_loading(
            data_loader=self.BPM_data.load_data,
            data_type='BPM',
            update_condition=lambda: isinstance(self.BPM_data.data, pd.DataFrame)  # Condition to check if BPM data is available
        )

    def on_load_cols_button_clicked(self, b):
        """Handle the event when the Load Collimators button is clicked. 
        
        Parse the date and time inputs, load collimator data, 
        and update the graph if data is available.
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
        """Handle the event when the Reset button is clicked. 
        
        Remove all selected knobs, reset their values, 
        and update the display and graph.
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
            
    def _handle_load_button_click(
            self, path, expected_extension, 
            path_replacement, load_function):
        """Handle common file validation and loading logic for various buttons.

        Parameters:
            file_chooser: The file chooser widget used to select the file.
            expected_extension: The expected file extension (e.g., '.json', '.tfs').
            path_replacement: Dictionary for path replacement (e.g., {'b1': 'b2'}). If None, no replacement is done.
            load_function: The function to call to load the data.
        """
        if not path:
            self.progress_label.value = 'Please select a file by clicking the Select button.'
            return

        _, actual_extension = os.path.splitext(path)
        if actual_extension != expected_extension:
            self.progress_label.value = f'Invalid file type. Please select a {expected_extension} file.'
            return
        
        # Create a path for beam 2
        if path_replacement:
            path_to_check = str(path)
            for old, new in path_replacement.items():
                path_to_check = path_to_check.replace(old, new)
            if not os.path.exists(path_to_check):
                self.progress_label.value = f"Path for the corresponding file doesn't exist."  # TODO: Add an option for path selection
                return

        self.progress_label.value = f'Loading new {expected_extension[1:].upper()} data...'
        load_function(path)
        
    def _load_line_data(self, path):
        """Load line data and re-loads associated aperture and optics data if available.

        Args:
            path (str): The path to the line data file.
        """
        # Preserve previous envelope and first element data if available before loading new
        n, first_element = None, None
        if hasattr(self, 'aperture_data'):
            n = self.aperture_data.n
            first_element = getattr(self.aperture_data, 'first_element', None)

            # Remove all knobs from selected
            for knob in self.selected_knobs[:]:
                self.selected_knobs.remove(knob)
                del self.values[knob]  # Remove the value of the knob
                del self.knob_widgets[knob]  # Remove the widget
            # Update selected knobs and display value
            self.update_knob_box()

        # Load new aperture data
        self.aperture_data = ApertureData(path_b1=path, label=self.progress_label)

        # Make sure not to load the aperture and optics twice
        # So only load if the path was already provided and not changed
        if (self.path_aperture and 
            self.path_aperture == self.file_chooser_aperture.selected):
            # Re-load aperture and optics data if selected
            self.progress_label.value = 'Re-loading aperture data...'
            self.aperture_data.load_aperture(self.file_chooser_aperture.selected)

        if (self.path_optics and 
            self.path_optics == self.file_chooser_optics.selected):
            self.progress_label.value = 'Re-loading optics elements...'
            self.aperture_data.load_elements(self.file_chooser_optics.selected)

        # Restore previous envelope and cycle settings
        if n:
            self.aperture_data.envelope(n)
        if first_element:
            self.aperture_data.cycle(first_element)

        # Update UI components
        self.enable_widgets()
        self.update_knob_dropdown()

        # This won't work if a file without deferred expressions was loaded
        try:
            beam = self.sort_mcbs_beam_dropdown.value
            plane = self.sort_mcbs_plane_dropdown.value
            region = self.sort_mcbs_regions_dropdown.value

            self.mcbs_dropdown.options = self.aperture_data.sort_mcbs_by_region(beam, plane, region)

            beam = self.sort_knobs_beam_dropdown.value
            plane = self.sort_knobs_plane_dropdown.value
            region = self.sort_knobs_regions_dropdown.value

            self.bump_knob_dropdown.options = self.aperture_data.sort_acb_knobs_by_region(beam, plane, region)
        except: self.progress_label.value = 'If you want to use knobs, load a JSON file with deffered expressions.'

    def _load_aperture_data(self, path):
        """Load aperture data from the selected file.

        Args:
            path (str): The path to the aperture data file.
        """
        if hasattr(self, 'aperture_data'):
            self.aperture_data.load_aperture(path)
        else:
            self.progress_label.value = 'You need to load a line first.'

    def _load_optics_data(self, path):
        """Load optics elements from the selected file.

        Args:
            path (str): The path to the optics data file.
        """
        if hasattr(self, 'aperture_data'):
            self.aperture_data.load_elements(path)
        else:
            self.progress_label.value = 'You need to load a line first.'

    def on_apply_changes_button_clicked(self, b):
        """Handle the event when the 'Apply changes' button is clicked."""

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
                for knob, (widget, remove_button) in self.knob_widgets.items():
                    self.aperture_data.change_knob(knob, widget.value)

                # Re-twiss
                self.aperture_data.twiss()
            except: 
                self.progress_label.value = 'Could not compute twiss. Try again with different knob values.'

        # Retrieve the selected element from the widget
        first_element = self.cycle_input.value
        if first_element and (
            not hasattr(self.aperture_data, "first_element")
            or self.aperture_data.first_element != first_element
        ): 
            self.progress_label.value = f'Setting {first_element} as the first element...'
            self.aperture_data.cycle(first_element)

        # If new, change the size of the envelope
        selected_size = self.envelope_input.value
        if self.aperture_data.n != selected_size:
            self.progress_label.value = f'Setting envelope size to {selected_size}...'
            self.aperture_data.envelope(selected_size)

        ir = self.main_ir_dropdown.value
        if self.plot_range != self.aperture_data.get_ir_boundries(ir):       

            self.plot_range = self.aperture_data.get_ir_boundries(ir)
            if self.plot_range[0]>self.plot_range[1]: 
                ip = f"ip{(int(ir[2:]) - 1) or 8}"
                self.progress_label.value = 'Oops, to see this IR you need to cycle the graph first...'
                self.aperture_data.cycle(ip)
                self.cycle_input.value = ip
                self.plot_range = self.aperture_data.get_ir_boundries(ir)  

        # Switch plane
        selected_plane = self.plane_dropdown.value
        self.plane = selected_plane

        # Update the graph
        self.update_graph()
            
    def check_mismatches(self):
        """Check for mismatches between knob widget values and the stored 
        aperture data.
        """
        return any(
            widget.value != row["current value"].iat[0]
            for knob_name, (widget, _) in self.knob_widgets.items()
            if not self.aperture_data.knobs[
                self.aperture_data.knobs["knob"] == knob_name
            ].empty
            for row in [
                self.aperture_data.knobs[
                    self.aperture_data.knobs["knob"] == knob_name
                ]
            ]
        )

    def disable_buttons(self):
        """Disable first row controls"""
        filtered_buttons = [
            widget 
            for widget in self.widgets 
            if isinstance(widget, Button)
            ]

        for i in filtered_buttons:
            i.disabled = True
        self.apply_changes_button.disabled = False

    def enable_widgets(self):
        """Enable all buttons"""
        for i in self.widgets:
            i.disabled = False

    def update_graph(self):
        """Update the graph displayed in the graph_container."""
        
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
             width: Optional[int] = 2000, 
             height: Optional[int] = 600):
        """Show tool"""
        self.width = width
        self.height = height
        
        # Display the widgets and the graph
        display(self.full_layout)

        # Plot all traces
        self.update_graph()
        
    def create_empty_cross_section(self):
        """Create an empty graph to hold space"""
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
        fig.update_xaxes(showgrid=True, gridwidth=1, 
                         gridcolor='lightgrey', zeroline=True, 
                         zerolinewidth=1, zerolinecolor='lightgrey')
        fig.update_yaxes(showgrid=True, gridwidth=1, 
                         gridcolor='lightgrey', zeroline=True, 
                         zerolinewidth=1, zerolinecolor='lightgrey')

        # Set axis limits to -0.05 to 0.05 for both x and y axes
        fig.update_xaxes(range=[-0.05, 0.05])
        fig.update_yaxes(range=[-0.05, 0.05])

        return go.FigureWidget(fig)
    
    def _add_traces(self, trace_function, *args):
        """Add traces and update visibility lists."""
        visibility, traces = trace_function(*args)
        for trace in traces:
            self.fig.add_trace(trace, row=self.row, col=self.col)
        self.visibility_b1 = np.append(self.visibility_b1, visibility)
        self.visibility_b2 = np.append(self.visibility_b2, ~np.array(visibility))

    def create_figure(self):
        """Create a Plotly figure with multiple traces 
        based on the available attributes."""
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
            self._add_traces(plot_aperture, self.aperture_data, self.plane)

        # If there are collimators loaded from yaml file
        if hasattr(self.aperture_data, 'colx_b1'):
            self._add_traces(plot_collimators_from_yaml, self.aperture_data, self.plane)

        # If collimators were loaded from timber
        if (self.collimator_data and 
            hasattr(self.collimator_data, 'colx_b1')):
            self._add_traces(plot_collimators_from_timber, self.collimator_data, self.aperture_data, self.plane)

        # If BPM data was loaded from timber
        if (self.BPM_data and 
            hasattr(self.BPM_data, 'data')):
            self._add_traces(plot_BPM_data, self.BPM_data, self.plane, self.aperture_data)
            
        self._add_traces(plot_beam_positions, self.aperture_data, self.plane)
        self._add_traces(plot_nominal_beam_positions, self.aperture_data, self.plane)
        self._add_traces(plot_envelopes, self.aperture_data, self.plane)

        # Convert lists to NumPy arrays and finalize visibility settings
        self.visibility_b1 = np.array(self.visibility_b1, dtype=bool)
        self.visibility_b2 = np.array(self.visibility_b2, dtype=bool)
        self.visibility_both = np.full(len(self.visibility_b1), True)
       
    def update_layout(self):
        """Update the layout of the given figure 
        with appropriate settings and visibility toggles.
        """
        # Set layout
        self.fig.update_layout(height=self.height, width=self.width, 
                               showlegend=False, plot_bgcolor='white')

        # Change x limits and labels
        self.fig.update_xaxes(title_text="s [m]", tickformat=',', 
                              row=self.row, col=self.col, 
                              range = self.plot_range)

        # Change y limits and labels
        if self.plane == 'horizontal': title = 'x [m]'
        elif self.plane == 'vertical': title = 'y [m]'

        self.fig.update_yaxes(title_text=title, tickformat=',', 
                              range = [-0.05, 0.05], row=self.row, col=self.col)

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
                                args=[{"visible": self.visibility_both}])
                                ]
                            )
                        )
                    ]
                )
            

