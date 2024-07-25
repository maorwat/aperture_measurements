import sys
sys.path.append('/eos/home-i03/m/morwat/.local/lib/python3.9/site-packages/')

import numpy as np
import pandas as pd

import warnings
warnings.filterwarnings('ignore')

import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot(data, plane, add_VELO=True):

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
        col_vis, collimator = collimators(data, plane)
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

    if add_VELO: add_velo(data, fig=fig, row=row, col=col)

    # Define buttons to toggle aperture and collimator data
    buttons = [
            dict(
                label="Beam 1",
                method="update",
                args=[{"visible": visibility_b1}]),
            dict(
                label="Beam 2",
                method="update",
                args=[{"visible": visibility_b2}])]
    
    # Set initial visibility for the traces
    for i, trace in enumerate(fig.data):
        trace.visible = visibility_b1[i]

    # Set layout
    fig.update_layout(height=800, width=800, plot_bgcolor='white', showlegend=False)

    # Change the axes limits and labels
    fig.update_xaxes(title_text="s [m]", row=row, col=col)
    fig.update_yaxes(range = [-0.05, 0.05], row=row, col=col)

    # Add the buttons to the layout
    fig.update_layout(updatemenus=[{"buttons": buttons, "showactive": True, 'active': 0, 'pad': {"r": 10, "t": 10},
                                    'xanchor': "left", 'yanchor': 'top', 'x': 0.15, 'y': 1.1}])
        
    # Add annotation
    fig.update_layout(annotations=[dict(text="Aperture data:", showarrow=False, 
                    x=0, y=1.075, xref="paper", yref='paper', align="left")])
        
    fig.show()

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

def collimators(data, plane):

    if plane == 'h': df_b1, df_b2 = data.colx_b1, data.colx_b2
    elif plane == 'v': df_b1, df_b2 = data.coly_b1, data.coly_b2

    # Create empty lists for traces
    collimators = []

    # Plot
    for df in [df_b1, df_b2]:
        for i in range(df.shape[0]):
            x0, y0b, y0t, x1, y1 = df.s.iloc[i] - 0.5, df.bottom_gap_col.iloc[i], df.top_gap_col.iloc[i], df.s.iloc[i] + 0.5, 0.05

            top_col = go.Scatter(x=[x0, x0, x1, x1], y=[y0t, y1, y1, y0t], fill="toself", mode='lines',
                            fillcolor='black', line=dict(color='black'), name=df.name.iloc[i])
            bottom_col = go.Scatter(x=[x0, x0, x1, x1], y=[y0b, -y1, -y1, y0b], fill="toself", mode='lines',
                            fillcolor='black', line=dict(color='black'), name=df.name.iloc[i])
            
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

    b1 = go.Scatter(x=data.nom_b1.s, y=y_b1, mode='lines', line=dict(color='blue', dash='dash'), text = data.nom_b1.name, name='Beam 1')
    b2 = go.Scatter(x=data.nom_b2.s, y=y_b2, mode='lines', line=dict(color='red', dash='dash'), text = data.nom_b2.name, name='Beam 2')
    
    return np.full(2, True), [b1, b2]

def aperture(data, plane):

    if plane == 'h':
            
        # Aperture
        top_aper_b1 = go.Scatter(x=data.aper_b1.S, y=data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        bottom_aper_b1 = go.Scatter(x=data.aper_b1.S, y=-data.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')     
        top_aper_b2 = go.Scatter(x=data.aper_b2.S, y=data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2')
        bottom_aper_b2 = go.Scatter(x=data.aper_b2.S, y=-data.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2') 

    elif plane == 'v':
            
        # Aperture
        top_aper_b1 = go.Scatter(x=data.aper_b1.S, y=data.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        bottom_aper_b1 = go.Scatter(x=data.aper_b1.S, y=-data.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b1.NAME, name='Aperture b1')
        top_aper_b2 = go.Scatter(x=data.aper_b2.S, y=data.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2')
        bottom_aper_b2 = go.Scatter(x=data.aper_b2.S, y=-data.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = data.aper_b2.NAME, name='Aperture b2') 

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

