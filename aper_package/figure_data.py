import numpy as np
import pandas as pd

import plotly.graph_objects as go
from typing import List, Tuple

def plot_BPM_data(data: object, 
                  plane: str, 
                  twiss: object) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Assign all BPMs to positions s based on twiss data and generate Plotly traces.

    Parameters:
        data: An object BPMData, expected to have attribute data.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).
        twiss: An ApertureData object containing aperture data used for processing BPM positions.

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing an array of booleans and a list of Plotly scatter traces.
    """
    # Assign BPMs to some position along the ring s by merging with twiss
    data.process(twiss)

    # Select data based on plane
    if plane == 'horizontal': y_b1, y_b2 = data.b1.x, data.b2.x
    elif plane == 'vertical': y_b1, y_b2 = data.b1.y, data.b2.y

    # Make sure the units are in meters like twiss data
    b1 = go.Scatter(x=data.b1.s, y=y_b1/1e6, mode='markers', 
                          line=dict(color='blue'), text = data.b1.name, name='BPM beam 1')
    
    b2 = go.Scatter(x=data.b2.s, y=y_b2/1e6, mode='markers', 
                          line=dict(color='red'), text = data.b2.name, name='BPM beam 2', visible=False)
    
    return np.array([True, False]), [b1, b2]

def plot_machine_components(data: object) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Generates Plotly traces for various machine components based on their type and position.

    Parameters:
        data: An ApertureData object containing machine element data, expected to have a DataFrame 'elements'
              with columns 'KEYWORD', 'S', 'L', 'K1L', and 'NAME'.

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing an array of visibility flags and a list of Plotly scatter traces.
    """
    # Specify the elements to plot and corresponding colors
    objects = ["SBEND", "COLLIMATOR", "SEXTUPOLE", "RBEND", "QUADRUPOLE"]
    colors = ['lightblue', 'black', 'hotpink', 'green', 'red']

    # Dictionary to store combined data for each object type
    combined_traces = {obj: {'x': [], 'y': [], 'name': []} for obj in objects}
    centers = {obj: {'x': [], 'y': [], 'name': []} for obj in objects}

    # Iterate over all object types
    for obj in objects:
        obj_df = data.elements[data.elements['KEYWORD'] == obj]

        for i in range(obj_df.shape[0]):
            # Calculate x-coordinates
            x0 = obj_df.iloc[i]['S'] - obj_df.iloc[i]['L'] / 2
            x1 = obj_df.iloc[i]['S'] + obj_df.iloc[i]['L'] / 2

            # Calculate y-coordinates
            if obj == 'QUADRUPOLE':
                y0, y1 = 0, np.sign(obj_df.iloc[i]['K1L']).astype(int)
                if y0 == y1:  # Skip if K1L is 0
                    continue
            else:
                y0, y1 = -0.5, 0.5

            # Append coordinates, separated by `None`
            combined_traces[obj]['x'].extend([x0, x0, x1, x1, None])
            combined_traces[obj]['y'].extend([y0, y1, y1, y0, None])
            # Calculate the center of the polygon
            x_center = np.mean([x0, x1])
            y_center = np.mean([y0, y1])
            centers[obj]['x'].append(x_center)
            centers[obj]['y'].append(y_center)
            centers[obj]['name'].append(obj_df.iloc[i]['NAME'])

    # Convert combined traces to Plotly Scatter objects
    traces = []
    for obj in objects:
        trace_data = combined_traces[obj]
        trace = go.Scatter(
            x=trace_data['x'],
            y=trace_data['y'],
            fill='toself',
            mode='lines',
            showlegend=False,
            hoverinfo='skip',
            fillcolor=colors[objects.index(obj)],
            line=dict(color=colors[objects.index(obj)])
        )
        traces.append(trace)

        # Add a trace for the names in the middle of the rectangles
        center_trace = go.Scatter(
            x=centers[obj]['x'],
            y=centers[obj]['y'],
            mode='none',
            text=centers[obj]['name'],
            showlegend=False,
            hoverinfo='text'
        )
        traces.append(center_trace)

    # Visibility flags for all objects
    visibility_arr = np.full(len(objects) * 2, True)

    return visibility_arr, traces

def plot_collimators_from_yaml(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot collimators based on YAML data.

    Parameters:
        data: An ApertureData object containing collimator data.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and the list of Plotly scatter traces.
    """
    
    return plot_collimators(data, plane)

def plot_collimators_from_timber(collimator_data: object, data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    
    """
    Plot collimators after processing data from TIMBER.

    Parameters:
        collimator_data: A CollimatorData object containing raw collimator data.
        data: An ApertureData object containing additional data needed for processing.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and the list of Plotly scatter traces.
    """
    collimator_data.process(data)
    
    return plot_collimators(collimator_data, plane)

def plot_collimators(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot collimators for a given plane.

    Parameters:
        data: An object containing collimator data with attributes `colx_b1`, `colx_b2`, `coly_b1`, `coly_b2`.
        plane: A string indicating the plane ('horizontal' for horizontal, 'vertical' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and the list of Plotly scatter traces.
    """
    # Select the appropriate DataFrames based on the plane
    if plane == 'horizontal':
        df_b1, df_b2 = data.colx_b1, data.colx_b2
    elif plane == 'vertical':
        df_b1, df_b2 = data.coly_b1, data.coly_b2

    # Initialize lists for combined coordinates for Beam 1 and Beam 2
    combined_traces = {
        'beam1': {'x': [], 'y': [], 'names': [], 'centers_x': [], 'centers_y': []},
        'beam2': {'x': [], 'y': [], 'names': [], 'centers_x': [], 'centers_y': []}
    }

    # Function to append collimator data to the combined traces
    def add_collimator_traces(df, beam_key):
        for i in range(df.shape[0]):
            x0 = df.s.iloc[i] - 0.5
            x1 = df.s.iloc[i] + 0.5
            y0t = df.top_gap_col.iloc[i]
            y0b = df.bottom_gap_col.iloc[i]
            y1 = 0.1

            # Top and bottom collimator combined in the same trace
            combined_traces[beam_key]['x'].extend([x0, x0, x1, x1, None, x0, x0, x1, x1, None])
            combined_traces[beam_key]['y'].extend([y0t, y1, y1, y0t, None, y0b, -y1, -y1, y0b, None])

            # Calculate the center of the collimator's filled area
            x_center = np.mean([x0, x1])
            y_center_top = np.mean([y0t, 0.05])
            y_center_bottom = np.mean([y0b, -0.05])
            combined_traces[beam_key]['centers_x'].append(x_center)
            combined_traces[beam_key]['centers_x'].append(x_center)
            combined_traces[beam_key]['centers_y'].append(y_center_top)
            combined_traces[beam_key]['centers_y'].append(y_center_bottom)
            # Use the name from the DataFrame
            combined_traces[beam_key]['names'].append(df.name.iloc[i])
            combined_traces[beam_key]['names'].append(df.name.iloc[i])

    # Add data for both beams
    add_collimator_traces(df_b1, 'beam1')
    add_collimator_traces(df_b2, 'beam2')

    # Create traces for the collimators
    collimators = []
    for beam_key in combined_traces:
        trace_data = combined_traces[beam_key]
        # Trace for filled areas
        collimator_trace = go.Scatter(
            x=trace_data['x'],
            y=trace_data['y'],
            fill="toself",
            mode='lines',
            fillcolor='black',
            hoverinfo='skip',
            showlegend=False,
            line=dict(color='black'),
            visible=True if beam_key == 'beam1' else False
        )
        collimators.append(collimator_trace)

        # Trace for names in the middle of the collimators
        center_trace = go.Scatter(
            x=trace_data['centers_x'],
            y=trace_data['centers_y'],
            mode='none',
            text=trace_data['names'],
            showlegend=False,
            hoverinfo='text',
            visible=True if beam_key == 'beam1' else False
        )
        collimators.append(center_trace)

    # Visibility array: show only Beam 1 collimators by default
    visibility_arr = np.array([True, True, False, False])

    return visibility_arr, collimators

def plot_envelopes(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the beam envelopes for a given plane.

    Parameters:
        data: An ApertureData object containing beam envelope data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    # Define hover template with customdata
    hover_template = ("s: %{x} [m]<br>"
                        "x: %{y} [m]<br>"
                        "element: %{text}<br>"
                        "distance from nominal: %{customdata} [mm]")

    if plane == 'horizontal':

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
                                  fill=None, line=dict(color='rgba(255,0,0,0)'), visible=False,
                                  customdata=data.tw_b2.x_from_nom_to_top, hovertemplate=hover_template)
        lower_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.x_down, mode='lines', 
                                  text = data.tw_b2.name, name='Lower envelope beam 2', visible=False, 
                                  line=dict(color='rgba(255,0,0,0)'), fill='tonexty', fillcolor='rgba(255,0,0,0.1)', 
                                  customdata=data.tw_b2.x_from_nom_to_bottom, hovertemplate=hover_template)
        
    elif plane == 'vertical':

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
                                  fill=None, line=dict(color='rgba(255,0,0,0)'), visible=False,
                                  customdata=data.tw_b2.y_from_nom_to_top, hovertemplate=hover_template)
        lower_b2 = go.Scatter(x=data.tw_b2.s, y=data.tw_b2.y_down, mode='lines', 
                                  text = data.tw_b2.name, name='Lower envelope beam 2', visible=False, 
                                  line=dict(color='rgba(255,0,0,0)'), fill='tonexty', fillcolor='rgba(255,0,0,0.1)',
                                  customdata=data.tw_b2.y_from_nom_to_bottom, hovertemplate=hover_template)
        
    visibility = np.array([True, True, False, False])
    traces = [upper_b1, lower_b1, upper_b2, lower_b2]

    return visibility, traces

def plot_beam_positions(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the beam positions for a given plane.

    Parameters:
        data: An ApertureData object containing beam position data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    if plane == 'horizontal': y_b1, y_b2 = data.tw_b1.x, data.tw_b2.x
    elif plane == 'vertical': y_b1, y_b2 = data.tw_b1.y, data.tw_b2.y

    b1 = go.Scatter(x=data.tw_b1.s, y=y_b1, mode='lines', line=dict(color='blue'), text = data.tw_b1.name, name='Beam 1')
    b2 = go.Scatter(x=data.tw_b2.s, y=y_b2, mode='lines', line=dict(color='red'), text = data.tw_b2.name, name='Beam 2', visible=False)
    
    return np.array([True, False]), [b1, b2]

def plot_nominal_beam_positions(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the nominal beam positions for a given plane.

    Parameters:
        data: An ApertureData object containing nominal beam position data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    if plane == 'horizontal': y_b1, y_b2 = data.nom_b1.x, data.nom_b2.x
    elif plane == 'vertical': y_b1, y_b2 = data.nom_b1.y, data.nom_b2.y

    b1 = go.Scatter(x=data.nom_b1.s, y=y_b1, mode='lines', line=dict(color='blue', dash='dash'), text = data.nom_b1.name, name='Nominal beam 1')
    b2 = go.Scatter(x=data.nom_b2.s, y=y_b2, mode='lines', line=dict(color='red', dash='dash'), text = data.nom_b2.name, name='Nominal beam 2', visible=False)
    
    return np.array([True, False]), [b1, b2]

def plot_aperture(data: object, plane: str) -> Tuple[np.ndarray, List[go.Scatter]]:
    """
    Plot the aperture for a given plane.

    Parameters:
        data: An ApertureData object containing aperture data for beam 1 and beam 2.
        plane: A string indicating the plane ('h' for horizontal, 'v' for vertical).

    Returns:
        Tuple[np.ndarray, List[go.Scatter]]: A tuple containing the visibility array and a list of Plotly scatter traces.
    """

    if plane == 'horizontal':
            
        # Aperture
        top_aper_b1 = go.Scatter(x=data.aper_b1.S, y=data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        bottom_aper_b1 = go.Scatter(x=data.aper_b1.S, y=-data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')     
        top_aper_b2 = go.Scatter(x=data.aper_b2.S, y=data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False)
        bottom_aper_b2 = go.Scatter(x=data.aper_b2.S, y=-data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False) 

    elif plane == 'vertical':
            
        # Aperture
        top_aper_b1 = go.Scatter(x=data.aper_b1.S, y=data.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        bottom_aper_b1 = go.Scatter(x=data.aper_b1.S, y=-data.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        top_aper_b2 = go.Scatter(x=data.aper_b2.S, y=data.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False)
        bottom_aper_b2 = go.Scatter(x=data.aper_b2.S, y=-data.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2', visible=False) 

    traces = [top_aper_b1, bottom_aper_b1, top_aper_b2, bottom_aper_b2]
    visibility = np.array([True, True, False, False])

    return visibility, traces

def add_velo(data: object) -> go.Scatter:
    """
    Add a VELO trace at the IP8 position.

    Parameters:
        data: An ApertureData object containing twiss data for beam 1.

    Returns:
        go.Scatter: A Plotly scatter trace representing the VELO.
    """

    # Find ip8 position
    ip8 = data.tw_b1.loc[data.tw_b1['name'] == 'ip8', 's'].values[0]

    # VELO position
    x0=ip8-0.2
    x1=ip8+0.8
    y0=-0.05
    y1=0.05

    trace = go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], mode='lines', line=dict(color='orange'), name='VELO')

    return trace