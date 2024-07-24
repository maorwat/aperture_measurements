import sys
sys.path.append('/eos/home-i03/m/morwat/.local/lib/python3.9/site-packages/')

import numpy as np
import pandas as pd
import tfs
import yaml

import warnings
warnings.filterwarnings('ignore')

import xtrack as xt

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from aper_package.utils import shift_by
from aper_package.utils import select_file

def plot(data, plane):
    
    fig = make_subplots(rows=2, cols=1, row_heights=[0.2, 0.8], shared_xaxes=True)

    if hasattr(data, 'elements'):
        visibility_b1, elements = machine_components(data)
        for i in data.elements:
            fig.add_trace(i, row=1, col=1)
        
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

    if plane == 'h': y_b1, y_b2 = data.nom_b1.x, data.nom_b1.x
    elif plane == 'v': y_b1, y_b2 = data.nom_b2.y, data.nom_b2.y

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

def add_velo(data):

    ip8 = data.tw_b1.loc[data.tw_b1['name'] == 'ip8', 's'].values[0]


