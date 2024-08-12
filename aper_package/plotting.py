import sys
sys.path.append('/eos/home-i03/m/morwat/.local/lib/python3.9/site-packages/')

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ipywidgets import widgets, VBox, HBox, Button, Layout, FloatText
from IPython.display import display

def plot(data, plane, BPM_data = None, collimator_data = None, width=1000, height=600, additional_traces=None):

    global knob_dropdown, add_button, remove_button, apply_button, graph_container, knob_box, cycle_button, cycle_input
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

    # Create a dropdown to select a knob
    knob_dropdown = create_knob_dropdown(data)

    # Button to add selection
    add_button = Button(description="Add", button_style='success')
    # Button to remove selection
    remove_button = Button(description="Remove", button_style='danger')
    # Button to apply selection and update graph
    apply_button = Button(description="Apply", button_style='primary')
    # Button to shift the graph
    cycle_button = Button(description="Cycle", style=widgets.ButtonStyle(button_color='pink'))
    # Reset knobs
    reset_button = Button(description="Reset knobs", button_style='warning')

    # To specify cycle start
    cycle_input = widgets.Text(
        value='',                  # Initial value (empty string)
        description='First element:',      # Label for the widget
        placeholder='e. g. ip3',  # Placeholder text when the input is empty
        style={'description_width': 'initial'},  # Adjust the width of the description label
        layout=widgets.Layout(width='300px')  # Set the width of the widget
    )

    # Create an empty VBox container for the graph and widgets
    graph_container = VBox(layout=Layout(
        justify_content='center',
        align_items='center',
        width='100%',
        padding='10px',
        border='solid 2px #eee'
    ))
    
    # Create a box to store selected knobs
    knob_box = VBox(layout=Layout(
        justify_content='center',
        align_items='center',
        width='100%',
        padding='10px',
        border='solid 2px #eee'
    ))

    # Arrange knob dropdown and buttons in a horizontal layout
    controls = HBox(
        [knob_dropdown, add_button, remove_button, apply_button],
        layout=Layout(
            justify_content='space-around',  # Distribute space evenly
            align_items='center',            # Center align all items
            width='100%',
            padding='10px',                  # Add padding around controls
            border='solid 2px #ccc'
        )
    )

    # Arrange knob dropdown and buttons in a horizontal layout
    more_controls = HBox(
        [cycle_input, cycle_button, reset_button],
        layout=Layout(
            justify_content='space-around',  # Distribute space evenly
            align_items='center',            # Center align all items
            width='100%',
            padding='10px',                  # Add padding around controls
            border='solid 2px #ccc'
        )
    )
    
    # Combine everything into the main VBox layout
    everything = VBox(
        [controls, knob_box, more_controls, graph_container],
        layout=Layout(
            justify_content='center',
            align_items='center',
            width='80%',                     # Limit width to 80% of the page
            margin='0 auto',                 # Center the VBox horizontally
            padding='20px',                  # Add padding around the whole container
            border='solid 2px #ddd'
        )
    )

    # Display the widgets and the graph
    display(everything)

    # Set up event handlers
    add_button.on_click(on_add_button_clicked)
    remove_button.on_click(on_remove_button_clicked)
    apply_button.on_click(on_apply_button_clicked)
    cycle_button.on_click(on_cycle_button_clicked)
    reset_button.on_click(on_reset_button_clicked)

    # Plot all traces
    update_graph(global_data, global_plane, global_BPM_data, global_collimator_data, global_additional_traces)

def on_reset_button_clicked(b):

    # Re-twiss
    global_data.reset_knobs()

    # Update the figure
    update_graph(global_data, global_plane, global_BPM_data, global_collimator_data, global_additional_traces)

def on_cycle_button_clicked(b):

    first_element = cycle_input.value

    # Re-twiss
    global_data.cycle(first_element)
    
    # Update the figure
    update_graph(global_data, global_plane, global_BPM_data, global_collimator_data, global_additional_traces)

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
            value=1.0,
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
    update_graph(global_data, global_plane, global_BPM_data, global_collimator_data, global_additional_traces)

def update_graph(data, plane, BPM_data, collimator_data, additional_traces):
    """
    Function to update the graph
    """
    # Create figure
    fig, visibility_b1, visibility_b2, row, col = create_figure(data, plane, BPM_data, collimator_data, additional_traces)
    # Update figure layout
    update_layout(fig, plane, row, col, visibility_b1, visibility_b2)
    
    # Change to a widget
    fig_widget = go.FigureWidget(fig)
    # Put the figure in the graph container
    graph_container.children = [fig_widget]
        
def create_figure(data, plane, BPM_data, collimator_data, additional_traces):

    # These correspond to swapping between visibilities of aperture/collimators for beam 1 and 2
    visibility_b1 = np.array([], dtype=bool)
    visibility_b2 = np.array([], dtype=bool)

    # If thick machine elements are loaded
    if hasattr(data, 'elements'):

        # Create 2 subplots: for elements and the plot
        fig = make_subplots(rows=2, cols=1, row_heights=[0.2, 0.8], shared_xaxes=True)
        # Update layout of the upper plot (machine components plot)
        fig.update_yaxes(range=[-1, 1], showticklabels=False, showline=False, row=1, col=1)
        fig.update_xaxes(showticklabels=False, showline=False, row=1, col=1)
        elements_visibility, elements = plot_machine_components(data)

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
    if additional_traces:
        for i in additional_traces:
            fig.add_trace(i, row=row, col=col)
            visibility_b1 = np.append(visibility_b1, True)
            visibility_b2 = np.append(visibility_b2, True)

    # If there is aperture data
    if hasattr(data, 'aper_b1'):
        aper_visibility, apertures = plot_aperture(data, plane)
        for i in apertures:
            fig.add_trace(i, row=row, col=col)

        # Show only aperture for one beam
        visibility_b1 = np.append(visibility_b1, aper_visibility)
        visibility_b2 = np.append(visibility_b2, np.logical_not(aper_visibility))

    # If there are collimators loaded from yaml file
    if hasattr(data, 'colx_b1'):
        collimator_visibility, collimator = plot_collimators_from_yaml(data, plane)
        for i in collimator:
            fig.add_trace(i, row=row, col=col)

        # Show only collimators for one beam
        visibility_b1 = np.append(visibility_b1, collimator_visibility)
        visibility_b2 = np.append(visibility_b2, np.logical_not(collimator_visibility))

    # If collimators were loaded from timber
    if collimator_data:
        collimator_visibility, collimator = plot_collimators_from_timber(collimator_data, data, plane)
        for i in collimator:
            fig.add_trace(i, row=row, col=col)

        # Show only collimators for one beam
        visibility_b1 = np.append(visibility_b1, collimator_visibility)
        visibility_b2 = np.append(visibility_b2, np.logical_not(collimator_visibility))

    # Add beam positions from twiss data
    beam_visibility, beams = plot_beam_positions(data, plane)
    for i in beams:
        fig.add_trace(i, row=row, col=col)

    # Always show both beams
    visibility_b1 = np.append(visibility_b1, beam_visibility)
    visibility_b2 = np.append(visibility_b2, beam_visibility)

    # Add nominal beam positions
    nominal_beam_visibility, nominal_beams = plot_nominal_beam_positions(data, plane)
    for i in nominal_beams:
        fig.add_trace(i, row=row, col=col)

    # Always show both beams
    visibility_b1 = np.append(visibility_b1, nominal_beam_visibility)
    visibility_b2 = np.append(visibility_b2, nominal_beam_visibility)

    # Add envelopes
    envelope_visibility, envelope = plot_envelopes(data, plane)
    for i in envelope:
        fig.add_trace(i, row=row, col=col)
    
    # Always show both envelopes
    visibility_b1 = np.append(visibility_b1, envelope_visibility)
    visibility_b2 = np.append(visibility_b2, envelope_visibility)

    # If BPM data was loaded from timber
    if BPM_data:
        BPM_visibility, BPM_traces = plot_BPM_data(BPM_data, plane, data)
        for i in BPM_traces:
            fig.add_trace(i, row=row, col=col)

        # Always show BPM data for both beams
        visibility_b1 = np.append(visibility_b1, BPM_visibility)
        visibility_b2 = np.append(visibility_b2, BPM_visibility)

    return fig, visibility_b1, visibility_b2, row, col

def create_knob_dropdown(data):  

    # Dropdown widget for knob selection
    dropdown_widget = widgets.Dropdown(
        options=data.knobs['knob'].to_list(),
        description='Select knob:',
        disabled=False)
    
    return dropdown_widget

def update_layout(fig, plane, row, col, visibility_b1, visibility_b2):

    # Set layout
    fig.update_layout(height=global_height, width=global_width, showlegend=False, xaxis=dict(tickformat=','), yaxis=dict(tickformat=','), plot_bgcolor='white')

    # Change x limits and labels
    fig.update_xaxes(title_text="s [m]", row=row, col=col)

    # Change y limits and labels
    if plane == 'h': title = 'x [m]'
    elif plane == 'v': title = 'y [m]'
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

def plot_BPM_data(data, plane, twiss):
    
    data.process(twiss)

    if plane == 'h': y_b1, y_b2 = data.b1.x, data.b2.x
    elif plane == 'v': y_b1, y_b2 = data.b1.y, data.b2.y

    # Make sure the units are in meters like twiss data
    b1 = go.Scatter(x=data.b1.s, y=y_b1/1e6, mode='markers', 
                          line=dict(color='blue'), text = data.b1.name, name='BPM beam 1')
    
    b2 = go.Scatter(x=data.b2.s, y=y_b2/1e6, mode='markers', 
                          line=dict(color='red'), text = data.b2.name, name='BPM beam 2')
    
    return np.full(2, True), [b1, b2]

def plot_machine_components(data):

    # Specify the elements to plot and corresponding colors
    objects = ["SBEND", "COLLIMATOR", "SEXTUPOLE", "RBEND", "QUADRUPOLE"]
    colors = ['lightblue', 'black', 'hotpink', 'green', 'red']

    # Array to store visibility of the elements
    visibility_arr = np.array([], dtype=bool)

    elements = []

    # Iterate over all object types
    for n, obj in enumerate(objects):
            
        obj_df = data.elements[data.elements['KEYWORD'] == obj]
            
        # Add elements to the plot
        for i in range(obj_df.shape[0]):

            x0, x1 = obj_df.iloc[i]['S']-obj_df.iloc[i]['L']/2, obj_df.iloc[i]['S']+obj_df.iloc[i]['L']/2                
            if obj=='QUADRUPOLE': y0, y1 = 0, np.sign(obj_df.iloc[i]['K1L']).astype(int)                    
            else: y0, y1 = -0.5, 0.5

            element = go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor=colors[n], line=dict(color=colors[n]), name=obj_df.iloc[i]['NAME'])

            elements.append(element)

        # Append to always show the elements
        visibility_arr = np.append(visibility_arr, np.full(obj_df.shape[0], True))
        
    return visibility_arr, elements

def plot_collimators_from_yaml(data, plane):
    
    visibility_arr_b1, collimators = plot_collimators(data, plane)
    
    return visibility_arr_b1, collimators

def plot_collimators_from_timber(collimator_data, data, plane):
    
    collimator_data.process(data)
    
    visibility_arr_b1, processed_collimator_data = plot_collimators(collimator_data, plane)
    
    return visibility_arr_b1, processed_collimator_data

def plot_collimators(data, plane):

    if plane == 'h': df_b1, df_b2 = data.colx_b1, data.colx_b2
    elif plane == 'v': df_b1, df_b2 = data.coly_b1, data.coly_b2

    # Create empty lists for traces
    collimators = []

    # Plot
    for df, vis in zip([df_b1, df_b2], [True, False]):

        for i in range(df.shape[0]):
            x0, y0b, y0t, x1, y1 = df.s.iloc[i] - 0.5, df.bottom_gap_col.iloc[i], df.top_gap_col.iloc[i], df.s.iloc[i] + 0.5, 0.1

            top_col = go.Scatter(x=[x0, x0, x1, x1], y=[y0t, y1, y1, y0t], fill="toself", mode='lines',
                            fillcolor='black', line=dict(color='black'), name=df.name.iloc[i], visible=vis)
            bottom_col = go.Scatter(x=[x0, x0, x1, x1], y=[y0b, -y1, -y1, y0b], fill="toself", mode='lines',
                            fillcolor='black', line=dict(color='black'), name=df.name.iloc[i], visible=vis)
            
            collimators.append(top_col)
            collimators.append(bottom_col)
        
    # As default show only beam 1 collimators
    visibility_arr_b1 = np.concatenate((np.full(df_b1.shape[0]*2, True), np.full(df_b2.shape[0]*2, False)))

    return visibility_arr_b1, collimators

def plot_envelopes(data, plane):

    # Define hover template with customdata
    hover_template = ("s: %{x} [m]<br>"
                            "x: %{y} [m]<br>"
                            "element: %{text}<br>"
                            "distance from nominal: %{customdata} [mm]")

    if plane == 'h':

        upper_b1 = go.Scatter(x=data.tw_b1.s, y=data.tw_b1.x_up, mode='lines', 
                                  text = data.tw_b1.name, name='Upper envelope beam 1', 
                                  fill=None, line=dict(color='rgba(0,0,255,0)'),
                                  customdata=data.tw_b1.x_from_nom_to_top, hovertemplate=hover_template)
        lower_b1 = go.Scatter(x=data.tw_b1.s, y=data.tw_b1.x_down, mode='lines', 
                                  text = data.tw_b1.name, name='Lower envelope beam 1', 
                                  line=dict(color='rgba(0,0,255,0)'), fill='tonexty', fillcolor='rgba(0,0,255,0.1)',
                                  customdata=data.tw_b1.x_from_nom_to_bottom, hovertemplate=hover_template)
        upper_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.x_up, mode='lines', 
                                  text = data.tw_b2.name, name='Upper envelope beam 2', 
                                  fill=None, line=dict(color='rgba(255,0,0,0)'),
                                  customdata=data.tw_b2.x_from_nom_to_top, hovertemplate=hover_template)
        lower_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.x_down, mode='lines', 
                                  text = data.tw_b2.name, name='Lower envelope beam 2', 
                                  line=dict(color='rgba(255,0,0,0)'), fill='tonexty', fillcolor='rgba(255,0,0,0.1)', 
                                  customdata=data.tw_b2.x_from_nom_to_bottom, hovertemplate=hover_template)
        
    elif plane == 'v':

        upper_b1 = go.Scatter(x=data.tw_b1.s, y=data.tw_b1.y_up, mode='lines', 
                                  text = data.tw_b1.name, name='Upper envelope beam 1', 
                                  fill=None, line=dict(color='rgba(0,0,255,0)'),
                                  customdata=data.tw_b1.y_from_nom_to_top, hovertemplate=hover_template)
        lower_b1 = go.Scatter(x=data.tw_b1.s, y=data.tw_b1.y_down, mode='lines', 
                                  text = data.tw_b1.name, name='Lower envelope beam 1', 
                                  line=dict(color='rgba(0,0,255,0)'), fill='tonexty', fillcolor='rgba(0,0,255,0.1)',
                                  customdata=data.tw_b1.y_from_nom_to_bottom, hovertemplate=hover_template)
        upper_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.y_up, mode='lines', 
                                  text = data.tw_b2.name, name='Upper envelope beam 2', 
                                  fill=None, line=dict(color='rgba(255,0,0,0)'),
                                  customdata=data.tw_b2.y_from_nom_to_top, hovertemplate=hover_template)
        lower_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.y_down, mode='lines', 
                                  text = data.tw_b2.name, name='Lower envelope beam 2', 
                                  line=dict(color='rgba(255,0,0,0)'), fill='tonexty', fillcolor='rgba(255,0,0,0.1)',
                                  customdata=data.tw_b2.y_from_nom_to_bottom, hovertemplate=hover_template)
        
    visibility = np.full(4, True)
    traces = [upper_b1, lower_b1, upper_b2, lower_b2]

    return visibility, traces

def plot_beam_positions(data, plane):

    if plane == 'h': y_b1, y_b2 = data.tw_b1.x, data.tw_b2.x
    elif plane == 'v': y_b1, y_b2 = data.tw_b1.y, data.tw_b2.y

    b1 = go.Scatter(x=data.tw_b1.s, y=y_b1, mode='lines', line=dict(color='blue'), text = data.tw_b1.name, name='Beam 1')
    b2 = go.Scatter(x=data.tw_b2.s, y=y_b2, mode='lines', line=dict(color='red'), text = data.tw_b2.name, name='Beam 2')
    
    return np.full(2, True), [b1, b2]

def plot_nominal_beam_positions(data, plane):

    if plane == 'h': y_b1, y_b2 = data.nom_b1.x, data.nom_b2.x
    elif plane == 'v': y_b1, y_b2 = data.nom_b1.y, data.nom_b2.y

    b1 = go.Scatter(x=data.nom_b1.s, y=y_b1, mode='lines', line=dict(color='blue', dash='dash'), text = data.nom_b1.name, name='Nominal beam 1')
    b2 = go.Scatter(x=data.nom_b2.s, y=y_b2, mode='lines', line=dict(color='red', dash='dash'), text = data.nom_b2.name, name='Nominal beam 2')
    
    return np.full(2, True), [b1, b2]

def plot_aperture(data, plane):

    if plane == 'h':
            
        # Aperture
        top_aper_b1 = go.Scatter(x=data.aper_b1.S, y=data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        bottom_aper_b1 = go.Scatter(x=data.aper_b1.S, y=-data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')     
        top_aper_b2 = go.Scatter(x=data.aper_b2.S, y=data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False)
        bottom_aper_b2 = go.Scatter(x=data.aper_b2.S, y=-data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False) 

    elif plane == 'v':
            
        # Aperture
        top_aper_b1 = go.Scatter(x=data.aper_b1.S, y=data.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        bottom_aper_b1 = go.Scatter(x=data.aper_b1.S, y=-data.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        top_aper_b2 = go.Scatter(x=data.aper_b2.S, y=data.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False)
        bottom_aper_b2 = go.Scatter(x=data.aper_b2.S, y=-data.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False) 

    traces = [top_aper_b1, bottom_aper_b1, top_aper_b2, bottom_aper_b2]
    visibility = np.array([True, True, False, False])

    return visibility, traces

def add_velo(data):

    # Find ip8 position
    ip8 = data.tw_b1.loc[data.tw_b1['name'] == 'ip8', 's'].values[0]

    # VELO position
    x0=ip8-0.2
    x1=ip8+0.8
    y0=-0.05
    y1=0.05

    trace = go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines', line=dict(color='orange'), name='VELO')

    return trace