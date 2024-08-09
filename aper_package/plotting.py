import sys
sys.path.append('/eos/home-i03/m/morwat/.local/lib/python3.9/site-packages/')

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ipywidgets import widgets, VBox, HBox, Button, Layout, FloatText
from IPython.display import display

def plot(data, plane, BPMs = None, collimators = None):

    global knob_dropdown, add_button, remove_button, apply_button, graph_container, knob_box
    global values, selected_knobs, knob_widgets
    global aper_data, aper_plane, beam_position_data, col_data

    aper_data = data          #TODO: make the names make sense
    aper_plane = plane
    beam_position_data = BPMs
    col_data = collimators

    fig, visibility_b1, visibility_b2, row, col = create_figure(aper_data, aper_plane, beam_position_data, col_data)

    # Dictionary to store multipliers for each option
    values = {}
    selected_knobs = []
    knob_widgets = {}

    # Create a dropdown to select a knob
    knob_dropdown = add_knob_dropdown()

    # Button to add selection
    add_button = Button(description="Add", button_style='success')
    # Button to remove selection
    remove_button = Button(description="Remove", button_style='danger')
    # Button to apply selection and update graph
    apply_button = Button(description="Apply", button_style='primary')

    # Create an empty VBox container for the graph and multiplier widgets
    graph_container = VBox(layout=Layout(
        justify_content='center',
        align_items='center',
        width='100%',
        padding='10px',
        border='solid 2px #eee'
    ))
    
    knob_box = VBox(layout=Layout(
        justify_content='center',
        align_items='center',
        width='100%',
        padding='10px',
        border='solid 2px #eee'
    ))

    # Arrange widgets in a layout
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
    
    # Combine everything into the main VBox layout
    everything = VBox(
        [controls, knob_box, graph_container],
        layout=Layout(
            justify_content='center',
            align_items='center',
            width='80%',                     # Limit width to 80% of the page
            margin='0 auto',                 # Center the VBox horizontally
            padding='20px',                  # Add padding around the whole container
            border='solid 2px #ddd'
        )
    )

    # Display the widgets
    display(everything)

    # Set up event handlers
    add_button.on_click(on_add_button_clicked)
    remove_button.on_click(on_remove_button_clicked)
    apply_button.on_click(on_apply_button_clicked)

    update_graph(aper_data, aper_plane, beam_position_data, col_data)

# Function to handle adding a selected option
def on_add_button_clicked(b):
    knob = knob_dropdown.value
    if knob and knob not in selected_knobs:
        selected_knobs.append(knob)
        values[knob] = 1.0  # Initialize multiplier for new option

        # Create a new FloatText widget for the selected option
        knob_widget = FloatText(
            value=1.0,
            description=f'{knob}',
            disabled=False,
            layout=Layout(width='270px')  # Adjust width as needed
        )
        knob_widgets[knob] = knob_widget

        # Update selected options label and display multiplier widgets
        update_knob_box()

# Function to handle removing a selected option
def on_remove_button_clicked(b):
    knob = knob_dropdown.value
    if knob in selected_knobs:
        selected_knobs.remove(knob)
        del values[knob]  # Remove multiplier for the option
        if knob in knob_widgets:
            del knob_widgets[knob]  # Remove the multiplier widget
        
        # Update selected options label and display multiplier widgets
        update_knob_box()
        
# Function to update the knob_box layout
def update_knob_box():
    # Group the widgets into sets of three per row
    rows = []
    for i in range(0, len(selected_knobs), 3):
        row = HBox([knob_widgets[knob] for knob in selected_knobs[i:i+3]],
                   layout=Layout(align_items='flex-start'))  # Align to left
        rows.append(row)

    # Update the knob_box with the new rows
    knob_box.children = rows

# Function to apply changes and update the graph
def on_apply_button_clicked(b):
    # Update multipliers dictionary based on current values in multiplier widgets
    for knob, widget in knob_widgets.items():
        aper_data.change_knob(knob, widget.value)
    
    aper_data.twiss()
        
    update_graph(aper_data, aper_plane, beam_position_data, col_data)

# Function to update the graph
def update_graph(data, plane, BPMs, collimators):
    fig, visibility_b1, visibility_b2, row, col = create_figure(data, plane, BPMs, collimators)
    # Update figure layout
    update_layout(fig, plane, row, col, visibility_b1, visibility_b2)
        
    fig_widget = go.FigureWidget(fig)

    graph_container.children = [fig_widget]
        
def create_figure(data, plane, BPMs, collimators):

    # For buttons
    visibility_b1 = np.array([], dtype=bool)
    visibility_b2 = np.array([], dtype=bool)

    if hasattr(data, 'elements'):

        fig = make_subplots(rows=2, cols=1, row_heights=[0.2, 0.8], shared_xaxes=True)
        fig.update_yaxes(range=[-1, 1], showticklabels=False, showline=False, row=1, col=1)
        fig.update_xaxes(showticklabels=False, showline=False, row=1, col=1)
        el_vis, elements = machine_components(data)

        for i in elements:
            fig.add_trace(i, row=1, col=1)
        # Row and col for other traces
        row, col = 2, 1

        visibility_b1 = np.append(visibility_b1, el_vis)
        visibility_b2 = np.append(visibility_b2, el_vis)

    else:
        fig = make_subplots(rows=1, cols=1)
        # Row and col for other traces
        row, col = 1, 1

    # If there is aperture data
    if hasattr(data, 'aper_b1'):
        aper_vis, apertures = aperture(data, plane)
        for i in apertures:
            fig.add_trace(i, row=row, col=col)

        visibility_b1 = np.append(visibility_b1, aper_vis)
        visibility_b2 = np.append(visibility_b2, np.logical_not(aper_vis))

    # If there are collimators 
    if hasattr(data, 'colx_b1'):
        col_vis, collimator = collimators_from_yaml(data, plane)
        for i in collimator:
            fig.add_trace(i, row=row, col=col)

        visibility_b1 = np.append(visibility_b1, col_vis)
        visibility_b2 = np.append(visibility_b2, np.logical_not(col_vis))

    if collimators:
        col_vis, collimator = collimators_from_timber(collimators, data, plane)
        for i in collimator:
            fig.add_trace(i, row=row, col=col)

        visibility_b1 = np.append(visibility_b1, col_vis)
        visibility_b2 = np.append(visibility_b2, np.logical_not(col_vis))

    # Add beam positions
    beam_vis, beams = beam_positions(data, plane)
    for i in beams:
        fig.add_trace(i, row=row, col=col)

    visibility_b1 = np.append(visibility_b1, beam_vis)
    visibility_b2 = np.append(visibility_b2, beam_vis)

    # Add nominal beam positions
    nom_beam_vis, nom_beams = nominal_beam_positions(data, plane)
    for i in nom_beams:
        fig.add_trace(i, row=row, col=col)

    visibility_b1 = np.append(visibility_b1, nom_beam_vis)
    visibility_b2 = np.append(visibility_b2, nom_beam_vis)

    # Add envelopes
    env_vis, envelope = envelopes(data, plane)
    for i in envelope:
        fig.add_trace(i, row=row, col=col)
    
    visibility_b1 = np.append(visibility_b1, env_vis)
    visibility_b2 = np.append(visibility_b2, env_vis)

    if BPMs:
        BPM_vis, BPM_traces = BPM_data(BPMs, plane)
        for i in BPM_traces:
            fig.add_trace(i, row=row, col=col)

        visibility_b1 = np.append(visibility_b1, BPM_vis)
        visibility_b2 = np.append(visibility_b2, BPM_vis)

    return fig, visibility_b1, visibility_b2, row, col

def add_knob_dropdown():

    knobs = ['on_x1', 'on_x2h', 'on_x2v', 'on_x5', 'on_x8h', 'on_x8v',
             'on_sep1', 'on_sep2h', 'on_sep2v', 'on_sep5', 'on_sep8h', 'on_sep8v',
             'on_alice', 'on_lhcb']
    
    # Dropdown widget
    dropdown_widget = widgets.Dropdown(
        options=knobs,
        description='Select knob:',
        disabled=False)
    
    return dropdown_widget

def update_layout(fig, plane, row, col, visibility_b1, visibility_b2):

    # Set layout
    fig.update_layout(height=600, width=800, showlegend=False)

    # Change the axes limits and labels
    fig.update_xaxes(title_text="s [m]", row=row, col=col)

    if plane == 'h': title = 'x [m]'
    elif plane == 'v': title = 'y [m]'
    fig.update_yaxes(title_text=title, range = [-0.05, 0.05], row=row, col=col)
    
    # Update the x-axis and y-axis tick format
    fig.update_layout(xaxis=dict(tickformat=','), yaxis=dict(tickformat=','), plot_bgcolor='white')

    if hasattr(aper_data, 'aper_b1') or hasattr(aper_data, 'colx_b1') or col_data:

        fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                x=0.62,
                y=1.2,
                buttons=list([
                    dict(label="Beam 1 aperture/collimation",
                        method="update",
                        args=[{"visible": visibility_b1}]),
                    dict(label="Beam 2 aperture/collimation",
                        method="update",
                        args=[{"visible": visibility_b2}])]))])

def BPM_data(data, plane):
    
    if plane == 'h': y_b1, y_b2 = data.b1_positions.X, data.b2_positions.X
    elif plane == 'v': y_b1, y_b2 = data.b1_positions.Y, data.b2_positions.Y

    # Make sure the units are in meters like twiss data
    b1 = go.Scatter(x=data.b1_positions.S, y=y_b1/1e6, mode='markers', 
                          line=dict(color='blue'), text = data.b1_positions.NAME, name='BPM beam 1')
    
    b2 = go.Scatter(x=data.b2_positions.S, y=y_b2/1e6, mode='markers', 
                          line=dict(color='red'), text = data.b2_positions.NAME, name='BPM beam 2')
    
    return np.full(2, True), [b1, b2]

def machine_components(data):

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

def collimators_from_yaml(data, plane):
    
    visibility_arr_b1, collimators = collimators(data, plane)
    
    return visibility_arr_b1, collimators

def collimators_from_timber(col_data, twiss_data, plane):
    
    col_data.process(twiss_data) #TODO: make the names make sense!!!
    
    visibility_arr_b1, collimators_data = collimators(col_data, plane)
    
    return visibility_arr_b1, collimators_data

def collimators(data, plane):

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

def envelopes(data, plane):

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

def beam_positions(data, plane):

    if plane == 'h': y_b1, y_b2 = data.tw_b1.x, data.tw_b2.x
    elif plane == 'v': y_b1, y_b2 = data.tw_b1.y, data.tw_b2.y

    b1 = go.Scatter(x=data.tw_b1.s, y=y_b1, mode='lines', line=dict(color='blue'), text = data.tw_b1.name, name='Beam 1')
    b2 = go.Scatter(x=data.tw_b2.s, y=y_b2, mode='lines', line=dict(color='red'), text = data.tw_b2.name, name='Beam 2')
    
    return np.full(2, True), [b1, b2]

def nominal_beam_positions(data, plane):

    if plane == 'h': y_b1, y_b2 = data.nom_b1.x, data.nom_b2.x
    elif plane == 'v': y_b1, y_b2 = data.nom_b1.y, data.nom_b2.y

    b1 = go.Scatter(x=data.nom_b1.s, y=y_b1, mode='lines', line=dict(color='blue', dash='dash'), text = data.nom_b1.name, name='Nominal beam 1')
    b2 = go.Scatter(x=data.nom_b2.s, y=y_b2, mode='lines', line=dict(color='red', dash='dash'), text = data.nom_b2.name, name='Nominal beam 2')
    
    return np.full(2, True), [b1, b2]

def aperture(data, plane):

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

def add_velo(data, fig, row, col):

    ip8 = data.tw_b1.loc[data.tw_b1['name'] == 'ip8', 's'].values[0]

    fig.add_shape(type="rect",
                x0=(ip8-0.2), x1=(ip8+0.8),
                y0=-0.05, y1=0.05,
                xref='x',
                yref='y',
                line=dict(
                    color="Orange",
                    width=1), row=row, col=col)

