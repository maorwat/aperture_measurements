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

class AperPlot:
    
    #TODO define all the arguments as optional or not
    def __init__(self,
                 ip = 'ip5',
                 n = 0,
                 emitt = 3.5e-6,
                 path1 = "/home/morwat/cernbox/aperture_measurements/madx/2023/all_optics_B1.tfs", 
                 path2 = "/home/morwat/cernbox/aperture_measurements/madx/2023/all_optics_B4.tfs",
                 line1 = '/home/morwat/cernbox/aperture_measurements/madx/2023/xsuite/Martas_injection_b1.json',
                 line2 = '/home/morwat/cernbox/aperture_measurements/madx/2023/xsuite/Martas_injection_b2.json',
                 machine_components_path = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B1.tfs',
                 collimators_path = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/colldbs/injection.yaml'):
        
        # Define necessary variables
        self.emitt = emitt
        self.n = n
        self.ip = ip

        self.machine_components_path = machine_components_path
        self.collimators_path = collimators_path   

        # Drop uneeded columns
        df_b1 = tfs.read(path1)[['S', 'NAME', 'APER_1', 'APER_2']]
        df_b2 = tfs.read(path2)[['S', 'NAME', 'APER_1', 'APER_2']]

        self.length = df_b1.S.iloc[-1]

        # Drop duplicates
        df_b1.drop_duplicates(subset=['S'])
        df_b2.drop_duplicates(subset=['S'])
        
        # Get rid of undefined and unnecessary values
        self.aper_b1 = df_b1[(df_b1['APER_1'] < 1) & (df_b1['APER_1'] != 0) & (df_b1['APER_2'] < 1) & (df_b1['APER_2'] != 0)]
        self.aper_b2 = df_b2[(df_b2['APER_1'] < 1) & (df_b2['APER_1'] != 0) & (df_b2['APER_2'] < 1) & (df_b2['APER_2'] != 0)]
        
        # Shift the aperture if ip1 such that ip1 is in the middle
        if self.ip == 'ip1':
            self.aper_b1 = shift_by(self.aper_b1, self.length/2, 'S')
            self.aper_b2 = shift_by(self.aper_b2, self.length/2, 'S')

        # Load a line and build tracker
        self.line_b1 = xt.Line.from_json(line1)
        self.line_b2 = xt.Line.from_json(line2)

        # Define gamma using loaded line
        self.gamma = self.line_b1.particle_ref.to_pandas()['gamma0'][0]

        # Twiss
        self.twiss()
        self.aper_b2 = shift_by(self.aper_b2, self.ip_diff, 'S')

        # Keep the nominal crossing seperately for calculations
        self._define_nominal_crossing()

    def twiss(self):

        # Generate twiss
        print('Computing twiss for beam 1...')
        tw_b1 = self.line_b1.twiss(skip_global_quantities=True).to_pandas()
        print('Computing twiss for beam 2...')
        tw_b2 = self.line_b2.twiss(skip_global_quantities=True).to_pandas()
        print('Done computing twiss.')

        # Remove the aperture and drift
        tw_b1 = tw_b1[~tw_b1.name.str.contains('aper')]
        tw_b2 = tw_b2[~tw_b2.name.str.contains('aper')]
        tw_b1 = tw_b1[~tw_b1.name.str.contains('drift')]
        tw_b2 = tw_b2[~tw_b2.name.str.contains('drift')]

        # Drop unnecessary columns
        self.tw_b1 = tw_b1[['s', 'name', 'x', 'y', 'betx', 'bety']]
        self.tw_b2 = tw_b2[['s', 'name', 'x', 'y', 'betx', 'bety']]

        # Redefine y axis
        self.tw_b2.loc[:, 'y'] = -self.tw_b2['y']
        
        # Shift the aperture if ip1 such that ip5 is at s=0
        if self.ip == 'ip1':
            self.tw_b1 = shift_by(self.tw_b1, self.length/2, 's')
            self.tw_b2 = shift_by(self.tw_b2, self.length/2, 's')

        # Align the IPs of interest for both beams
        self.ip_diff = self.tw_b1.loc[self.tw_b1['name'] == self.ip, 's'].values[0]-self.tw_b2.loc[self.tw_b2['name'] == self.ip, 's'].values[0]
        self.tw_b2 = shift_by(self.tw_b2, self.ip_diff, 's')

        # Define attributes
        self._define_sigma()
        self.envelope(self.n)

    def change_ip(self, ip):

        #TODO improve?
        self.ip = ip

        # Align the IPs of interest for both beams
        self.ip_diff = self.tw_b1.loc[self.tw_b1['name'] == self.ip, 's'].values[0]-self.tw_b2.loc[self.tw_b2['name'] == self.ip, 's'].values[0]
        
        # Shift the twiss, aperture, and nominal twiss
        self.tw_b2 = shift_by(self.tw_b2, self.ip_diff, 's')
        self.aper_b2 = shift_by(self.aper_b2, self.ip_diff, 'S')
        self.nom_b2 = shift_by(self.nom_b2, self.ip_diff, 's')

        # Recalculate envelope
        self.envelope(self.n)

    def _define_nominal_crossing(self):

        # Define the nominal crossing for given configuration
        self.nom_b1 = self.tw_b1[['name', 'x', 'y', 's']].copy()
        self.nom_b2 = self.tw_b2[['name', 'x', 'y', 's']].copy()

    def _define_sigma(self):

        # Ensure tw_b1 is not a slice
        self.tw_b1 = self.tw_b1.copy()
        self.tw_b2 = self.tw_b2.copy()

        # Add columns for horizontal and vertical sigma
        self.tw_b1.loc[:, 'sigma_x'] = np.sqrt(self.tw_b1['betx'] * self.emitt / self.gamma)
        self.tw_b1.loc[:, 'sigma_y'] = np.sqrt(self.tw_b1['bety'] * self.emitt / self.gamma)

        self.tw_b2.loc[:, 'sigma_x'] = np.sqrt(self.tw_b2['betx'] * self.emitt / self.gamma)
        self.tw_b2.loc[:, 'sigma_y'] = np.sqrt(self.tw_b2['bety'] * self.emitt / self.gamma) 

    def envelope(self, n):

        self.n = n

        # Ensure tw_b1 is not a slice
        self.tw_b1 = self.tw_b1.copy()
        self.tw_b2 = self.tw_b2.copy()
        
        # Recalculate the envelope edges for the new envelope size
        self.tw_b1.loc[:, 'x_up'] = self.tw_b1['x'] + n * self.tw_b1['sigma_x']
        self.tw_b1.loc[:, 'x_down'] = self.tw_b1['x'] - n * self.tw_b1['sigma_x']
        self.tw_b1.loc[:, 'y_up'] = self.tw_b1['y'] + n * self.tw_b1['sigma_y']
        self.tw_b1.loc[:, 'y_down'] = self.tw_b1['y'] - n * self.tw_b1['sigma_y']

        self.tw_b2.loc[:, 'x_up'] = self.tw_b2['x'] + n * self.tw_b2['sigma_x']
        self.tw_b2.loc[:, 'x_down'] = self.tw_b2['x'] - n * self.tw_b2['sigma_x']
        self.tw_b2.loc[:, 'y_up'] = self.tw_b2['y'] + n * self.tw_b2['sigma_y']
        self.tw_b2.loc[:, 'y_down'] = self.tw_b2['y'] - n * self.tw_b2['sigma_y']

    def _add_collimators(self, fig, plane, row, column, beam):

        # Load the file
        with open(self.collimators_path, 'r') as file:
            f = yaml.safe_load(file)
    
        # Create pandas dataframes for collimators b1 and b2
        col_b1 = pd.DataFrame(f['collimators']['b1']).loc[['gap', 'angle']]
        col_b2 = pd.DataFrame(f['collimators']['b2']).loc[['gap', 'angle']]

        # Get names of vertical and horizontal collimators
        xname_b1 = col_b1.columns[col_b1.loc['angle'] == 0].to_numpy()
        yname_b1 = col_b1.columns[col_b1.loc['angle'] == 90].to_numpy()
        xname_b2 = col_b2.columns[col_b2.loc['angle'] == 0].to_numpy()
        yname_b2 = col_b2.columns[col_b2.loc['angle'] == 90].to_numpy()

        def get_df(name, yaml_df, twiss_data, sigma_key, x_key):

            # Load collimators for specified beam and plane
            col = yaml_df[name]
            # Remove nans
            gap = np.array([np.nan if x is None else x for x in col.loc['gap']])
            # Find the selected collimators in twiss data
            indx = np.where(np.isin(twiss_data["name"], name))[0]
            # Load their positions, x, and sigma
            s_col = twiss_data["s"].to_numpy()[indx]
            x_col = twiss_data[x_key].to_numpy()[indx]
            sigma = twiss_data[sigma_key].to_numpy()[indx]
            # Calculate gap in meters
            top_gap_col = sigma * gap + x_col
            bottom_gap_col = -sigma * gap + x_col

            # Create a DataFrame out of the above data
            data = {'NAME': name,
                    'GAPt': top_gap_col,
                    'GAPb': bottom_gap_col,
                    'S': s_col}
 
            df = pd.DataFrame(data)
            df = df.dropna()
            return df
        
        # Create the DataFrames
        dfx_b1 = get_df(xname_b1, col_b1, self.tw_b1, 'sigma_x', 'x')
        dfy_b1 = get_df(yname_b1, col_b1, self.tw_b1, 'sigma_y', 'y')

        dfx_b2 = get_df(xname_b2, col_b2, self.tw_b2, 'sigma_x', 'x')
        dfy_b2 = get_df(yname_b2, col_b2, self.tw_b2, 'sigma_y', 'y')
  
        # Plot
        if plane == 'h':
            # Add x collimators
            if beam == 1:
                for i in range(dfx_b1.shape[0]):
                    x0, y0b, y0t, x1, y1 = dfx_b1.S.iloc[i] - 0.5, dfx_b1.GAPb.iloc[i], dfx_b1.GAPt.iloc[i], dfx_b1.S.iloc[i] + 0.5, 0.05
                    fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0t, y1, y1, y0t], fill="toself", mode='lines',
                                fillcolor='black', line=dict(color='black'), name=dfx_b1.NAME.iloc[i]), row=2, col=1)
                    fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0b, -y1, -y1, y0b], fill="toself", mode='lines',
                                fillcolor='black', line=dict(color='black'), name=dfx_b1.NAME.iloc[i]), row=2, col=1)
            if beam == 2:    
                for i in range(dfx_b2.shape[0]):
                    x0, y0b, y0t, x1, y1 = dfx_b2.S.iloc[i] - 0.5, dfx_b2.GAPb.iloc[i], dfx_b2.GAPt.iloc[i], dfx_b2.S.iloc[i] + 0.5, 0.05
                    fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0t, y1, y1, y0t], fill="toself", mode='lines',
                                fillcolor='black', line=dict(color='black'), name=dfx_b2.NAME.iloc[i]), row=2, col=1)
                    fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0b, -y1, -y1, y0b], fill="toself", mode='lines',
                                fillcolor='black', line=dict(color='black'), name=dfx_b2.NAME.iloc[i]), row=2, col=1)

        if plane == 'v':
            # Add y collimators
            if beam == 1:
                for i in range(dfy_b1.shape[0]):
                    x0, y0b, y0t, x1, y1 = dfy_b1.S.iloc[i] - 0.5, dfy_b1.GAPb.iloc[i], dfy_b1.GAPt.iloc[i], dfy_b1.S.iloc[i] + 0.5, 0.05
                    fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0t, y1, y1, y0t], fill="toself", mode='lines',
                                fillcolor='black', line=dict(color='black'), name=dfy_b1.NAME.iloc[i]), row=2, col=1)
                    fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0b, -y1, -y1, y0b], fill="toself", mode='lines',
                                fillcolor='black', line=dict(color='black'), name=dfy_b1.NAME.iloc[i]), row=2, col=1)
            if beam == 2:
                for i in range(dfy_b2.shape[0]):
                    x0, y0b, y0t, x1, y1 = dfy_b2.S.iloc[i] - 0.5, dfy_b2.GAPb.iloc[i], dfy_b2.GAPt.iloc[i], dfy_b2.S.iloc[i] + 0.5, 0.05
                    fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0t, y1, y1, y0t], fill="toself", mode='lines',
                                fillcolor='black', line=dict(color='black'), name=dfy_b2.NAME.iloc[i]), row=2, col=1)
                    fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0b, -y1, -y1, y0b], fill="toself", mode='lines',
                                fillcolor='black', line=dict(color='black'), name=dfy_b2.NAME.iloc[i]), row=2, col=1)

    def _add_machine_components(self, fig, row, column):
        
        # Load the file
        df = tfs.read(self.machine_components_path)

        # Shift if IP1
        if self.ip == 'ip1': df = shift_by(df, self.length/2, 'S')

        # Specify the elements to plot and corresponding colors
        objects = ["SBEND", "COLLIMATOR", "SEXTUPOLE", "RBEND", "QUADRUPOLE"]
        colors = ['lightblue', 'black', 'hotpink', 'green', 'red']

        # Iterate over all object types
        for n, obj in enumerate(objects):
            
            obj_df = df[df['KEYWORD'] == obj]
            
            # Add elements to the plot
            for i in range(obj_df.shape[0]):

                x0, x1 = obj_df.iloc[i]['S']-obj_df.iloc[i]['L']/2, obj_df.iloc[i]['S']+obj_df.iloc[i]['L']/2                
                if obj=='QUADRUPOLE': y0, y1 = 0, np.sign(obj_df.iloc[i]['K1L']).astype(int)                    
                else: y0, y1 = -0.5, 0.5

                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor=colors[n], line=dict(color=colors[n]), name=obj_df.iloc[i]['NAME']), row=row, col=column) 

    def _distance_to_aperture(self, fig, plane, beam):
        
        # Rename x and y columns so they don't get mixed up
        nom_b1 = self.nom_b1.rename(columns={'x': 'nom_x', 'y': 'nom_y'}).drop(columns=['name'])
        nom_b2 = self.nom_b2.rename(columns={'x': 'nom_x', 'y': 'nom_y'}).drop(columns=['name'])

        # Merge twiss, nominal, and aperture data
        merged_b1 = pd.merge_asof(self.tw_b1, self.aper_b1, left_on='s', right_on='S', direction='nearest', tolerance=0.00001)
        merged_b2 = pd.merge_asof(self.tw_b2, self.aper_b2, left_on='s', right_on='S', direction='nearest', tolerance=0.00001)

        merged_b1 = pd.merge_asof(merged_b1, nom_b1, left_on='s', right_on='s', direction='nearest', tolerance=0.00001)
        merged_b2 = pd.merge_asof(merged_b2, nom_b2, left_on='s', right_on='s', direction='nearest', tolerance=0.00001)

        # Drop all the rows with NaNs
        merged_b1 = merged_b1.dropna()
        merged_b2 = merged_b2.dropna()

        # Drop repeat columns
        merged_b1 = merged_b1.drop(columns=['S', 'NAME'])
        merged_b2 = merged_b2.drop(columns=['S', 'NAME'])

        if plane == 'h':

            # Calculate distance from the envelope to the nominal beam
            merged_b1['from_nom_to_top'] = (merged_b1['x_up'] - merged_b1['nom_x'])*1000
            merged_b2['from_nom_to_top'] = (merged_b2['x_up'] - merged_b2['nom_x'])*1000

            merged_b1['from_nom_to_bottom'] = (-merged_b1['x_down'] + merged_b1['nom_x'])*1000
            merged_b2['from_nom_to_bottom'] = (-merged_b2['x_down'] + merged_b2['nom_x'])*1000

            # Calculate distance from the envelope to the aperture
            merged_b1['from_top_to_aper'] = merged_b1['APER_1'] - merged_b1['x_up']
            merged_b2['from_top_to_aper'] = merged_b2['APER_1'] - merged_b2['x_up']

            merged_b1['from_bottom_to_aper'] = merged_b1['x_down'] + merged_b1['APER_1']
            merged_b2['from_bottom_to_aper'] = merged_b2['x_down'] + merged_b2['APER_1']

        elif plane == 'v':

            # Calculate distance from the envelope to the nominal beam
            merged_b1['from_nom_to_top'] = (merged_b1['y_up'] - merged_b1['nom_y'])*1000
            merged_b2['from_nom_to_top'] = (merged_b2['y_up'] - merged_b2['nom_y'])*1000

            merged_b1['from_nom_to_bottom'] = (-merged_b1['y_down'] + merged_b1['nom_y'])*1000
            merged_b2['from_nom_to_bottom'] = (-merged_b2['y_down'] + merged_b2['nom_y'])*1000

            # Calculate distance from the envelope to the aperture
            merged_b1['from_top_to_aper'] = merged_b1['APER_2'] - merged_b1['y_up']
            merged_b2['from_top_to_aper'] = merged_b2['APER_2'] - merged_b2['y_up']

            merged_b1['from_bottom_to_aper'] = merged_b1['y_down'] + merged_b1['APER_2']
            merged_b2['from_bottom_to_aper'] = merged_b2['y_down'] + merged_b2['APER_2']

        # Check if the envelope touched the aperture
        touched_top_b1 = (merged_b1['from_top_to_aper'] < 0)
        touched_bottom_b1 = (merged_b1['from_bottom_to_aper'] < 0)

        touched_top_b2 = (merged_b2['from_top_to_aper'] < 0)
        touched_bottom_b2 = (merged_b2['from_bottom_to_aper'] < 0)

        # Define hover template with customdata
        hover_template = ("s: %{x} [m]<br>"
                            "x: %{y} [m]<br>"
                            "name: %{text}<br>"
                            "distance from nominal: %{customdata} [mm]")

        # If beam 1 touched the top aperture
        if touched_top_b1.any():

            # Find the elements touched, their locations, and distance from the nominal
            elements = merged_b1[touched_top_b1]['name'].tolist()
            s = merged_b1[touched_top_b1]['s'].tolist()
            d = merged_b1[touched_top_b1]['from_nom_to_top'].tolist()
            if plane == 'h': x = merged_b1[touched_top_b1]['x_up'].tolist()
            elif plane == 'v': x = merged_b1[touched_top_b1]['y_up'].tolist()

            if beam == 1:
                # Mark where the aperture was touched on the plot
                trace_top_b1 = go.Scatter(x=s, y=x, mode='markers', marker=dict(color='orange'), text=elements, name = 'Touched aperture b1',
                                      customdata=d, hovertemplate = hover_template)
                fig.add_trace(trace_top_b1, row=2, col=1)

            # Print where the aperture was touched and store it in a df attribute
            print(f'Top aperture touched by beam 1 between element {elements[0]} and {elements[-1]}.')
            self.touched_top_elements_b1 = pd.DataFrame({'element': elements, 'distance_from_nominal': d})
        
        # If beam 2 touched the top aperture
        if touched_top_b2.any():

            # Find the elements touched, their locations, and distance from the nominal
            elements = merged_b2[touched_top_b2]['name'].tolist()
            s = merged_b2[touched_top_b2]['s'].tolist()
            d = merged_b2[touched_top_b2]['from_nom_to_top'].tolist()
            if plane == 'h': x = merged_b2[touched_top_b2]['x_up'].tolist()
            elif plane == 'v': x = merged_b2[touched_top_b2]['y_up'].tolist()

            if beam == 2:
                # Mark where the aperture was touched on the plot
                trace_top_b2 = go.Scatter(x=s, y=x, mode='markers', marker=dict(color='orange'), text=elements, name = 'Touched aperture b2',
                                      customdata=d, hovertemplate = hover_template)
                fig.add_trace(trace_top_b2, row=2, col=1)

            # Keep the elements where the aperture was touched as an attribute
            self.touched_top_elements_b2 = pd.DataFrame({'element': elements, 'distance_from_nominal': d})

        # If beam 1 touched the bottom aperture
        if touched_bottom_b1.any():

            # Find the elements touched, their locations, and distance from the nominal
            elements = merged_b1[touched_bottom_b1]['name'].tolist()
            s = merged_b1[touched_bottom_b1]['s'].tolist()
            d = merged_b1[touched_bottom_b1]['from_nom_to_bottom'].tolist()
            if plane == 'h': x = merged_b1[touched_bottom_b1]['x_down'].tolist()
            elif plane == 'v': x = merged_b1[touched_bottom_b1]['y_down'].tolist()

            if beam == 1:
                # Mark where the aperture was touched on the plot
                trace_bottom_b1 = go.Scatter(x=s, y=x, mode='markers', marker=dict(color='orange'), text=elements, name = 'Touched aperture b1',
                                         customdata=d, hovertemplate = hover_template)
                fig.add_trace(trace_bottom_b1, row=2, col=1)

            # Keep the elements where the aperture was touched as an attribute
            self.touched_bottom_elements_b1 = pd.DataFrame({'element': elements, 'distance_from_nominal': d})

        # If beam 2 touched the bottom aperture
        if touched_bottom_b2.any():
            
            # Find the elements touched, their locations, and distance from the nominal
            elements = merged_b2[touched_bottom_b2]['name'].tolist()
            s = merged_b2[touched_bottom_b2]['s'].tolist()
            d = merged_b2[touched_bottom_b2]['from_nom_to_bottom'].tolist()
            if plane == 'h': x = merged_b2[touched_bottom_b2]['x_down'].tolist()
            elif plane == 'v': x = merged_b2[touched_bottom_b2]['y_down'].tolist()

            if beam == 2:
                # Mark where the aperture was touched on the plot
                trace_bottom_b2 = go.Scatter(x=s, y=x, mode='markers', marker=dict(color='orange'), text=elements, name = 'Touched aperture b2',
                                         customdata=d, hovertemplate = hover_template)
                fig.add_trace(trace_bottom_b2, row=2, col=1)

            # Keep the elements where the aperture was touched as an attribute
            self.touched_bottom_elements_b2 = pd.DataFrame({'element': elements, 'distance_from_nominal': d})

        # If aperture was not touched
        if not (touched_top_b1.any() or touched_bottom_b1.any() or touched_top_b2.any() or touched_bottom_b2.any()):
            print('Aperture not touched.')

    def change_crossing_angle(self, ip, angle, plane = 'h'):
    
        if ip == 'ip1':
            self.line_b1.vars['on_x1'] = angle
            self.line_b2.vars['on_x1'] = angle
        elif ip == 'ip2':
            if plane == 'v':
                self.line_b1.vars['on_x2v'] = angle
                self.line_b2.vars['on_x2v'] = angle
            elif plane == 'h':
                self.line_b1.vars['on_x2h'] = angle
                self.line_b2.vars['on_x2h'] = angle
        elif ip =='ip5':
            self.line_b1.vars['on_x5'] = angle
            self.line_b2.vars['on_x5'] = angle
        elif ip == 'ip8':
            if plane == 'v':
                self.line_b1.vars['on_x8v'] = angle
                self.line_b2.vars['on_x8v'] = angle
            elif plane == 'h':
                self.line_b1.vars['on_x8h'] = angle
                self.line_b2.vars['on_x8h'] = angle

    def add_separation_bump(self, ip, value, plane = 'h'):

        if ip == 'ip1':
            self.line_b1.vars['on_sep1'] = value
            self.line_b2.vars['on_sep1'] = value
        elif ip == 'ip2':
            if plane == 'v':
                self.line_b1.vars['on_sep2v'] = value
                self.line_b2.vars['on_sep2v'] = value
            elif plane == 'h':
                self.line_b1.vars['on_sep2h'] = value
                self.line_b2.vars['on_sep2h'] = value
        elif ip =='ip5':
            self.line_b1.vars['on_sep5'] = value
            self.line_b2.vars['on_sep5'] = value
        elif ip == 'ip8':
            if plane == 'v':
                self.line_b1.vars['on_sep8v'] = value
                self.line_b2.vars['on_sep8v'] = value
            elif plane == 'h':
                self.line_b1.vars['on_sep8h'] = value
                self.line_b2.vars['on_sep8h'] = value

    def spectrometer(self, ip, value):

        if ip == 'ip2':
            self.line_b1.vars['on_alice'] = value
            self.line_b2.vars['on_alice'] = value
        elif ip == 'ip8':
            self.line_b1.vars['on_lhcb'] = value
            self.line_b2.vars['on_lhcb'] = value

    def show(self, 
             plane,
             beam = 1,
             show_collimators = True):

        # Create figure
        fig = make_subplots(rows=2, cols=1, row_heights=[0.2, 0.8], shared_xaxes=True)
        
        if plane == 'h':
            
            # Aperture
            top_aper_b1 = go.Scatter(x=self.aper_b1.S, y=self.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = self.aper_b1.NAME, name='Aperture b1')
            bottom_aper_b1 = go.Scatter(x=self.aper_b1.S, y=-self.aper_b1.APER_1, mode='lines', line=dict(color='gray'), text = self.aper_b1.NAME, name='Aperture b1')     
            top_aper_b2 = go.Scatter(x=self.aper_b2.S, y=self.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = self.aper_b2.NAME, name='Aperture b2')
            bottom_aper_b2 = go.Scatter(x=self.aper_b2.S, y=-self.aper_b2.APER_1, mode='lines', line=dict(color='gray'), text = self.aper_b2.NAME, name='Aperture b2') 

            # Beam positions and nominal beam positions
            b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.x, mode='lines', line=dict(color='blue'), text = self.tw_b1.name, name='Beam 1')
            b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.x, mode='lines', line=dict(color='red'), text = self.tw_b2.name, name='Beam 2')
            nom_b1 = go.Scatter(x=self.nom_b1.s, y=self.nom_b1.x, mode='lines', line=dict(color='blue', dash='dash'), text = self.nom_b1.name, name='Beam 1')
            nom_b2 = go.Scatter(x=self.nom_b2.s, y=self.nom_b2.x, mode='lines', line=dict(color='red', dash='dash'), text = self.nom_b2.name, name='Beam 2')
            
            # Envelopes
            upper_b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.x_up, mode='lines', text = self.tw_b1.name, name='Upper envelope beam 1', fill=None, line=dict(color='rgba(0,0,255,0)'))
            lower_b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.x_down, mode='lines', text = self.tw_b1.name, name='Lower envelope beam 1', line=dict(color='rgba(0,0,255,0)'), 
                          fill='tonexty', fillcolor='rgba(0,0,255,0.1)')
            
            upper_b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.x_up, mode='lines', text = self.tw_b2.name, name='Upper envelope beam 2', fill=None, line=dict(color='rgba(255,0,0,0)'))
            lower_b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.x_down, mode='lines', text = self.tw_b2.name, name='Lower envelope beam 2', line=dict(color='rgba(255,0,0,0)'), 
                           fill='tonexty', fillcolor='rgba(255,0,0,0.1)')
            
            # Axes range and title
            fig.update_yaxes(range=[-0.05, 0.05], title_text="x [m]", row=2, col=1)
            
        elif plane == 'v':
            
            # Aperture
            top_aper_b1 = go.Scatter(x=self.aper_b1.S, y=self.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = self.aper_b1.NAME, name='Aperture b1')
            bottom_aper_b1 = go.Scatter(x=self.aper_b1.S, y=-self.aper_b1.APER_2, mode='lines', line=dict(color='gray'), text = self.aper_b1.NAME, name='Aperture b1')
            top_aper_b2 = go.Scatter(x=self.aper_b2.S, y=self.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = self.aper_b2.NAME, name='Aperture b2')
            bottom_aper_b2 = go.Scatter(x=self.aper_b2.S, y=-self.aper_b2.APER_2, mode='lines', line=dict(color='gray'), text = self.aper_b2.NAME, name='Aperture b2') 
            
            # Beam positions and nominal beam positions
            b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.y, mode='lines', line=dict(color='blue'), text = self.tw_b1.name, name='Beam 1')
            b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.y, mode='lines', line=dict(color='red'), text = self.tw_b2.name, name='Beam 2')
            nom_b1 = go.Scatter(x=self.nom_b1.s, y=self.nom_b1.y, mode='lines', line=dict(color='blue', dash='dash'), text = self.nom_b1.name, name='Beam 1')
            nom_b2 = go.Scatter(x=self.nom_b2.s, y=self.nom_b2.y, mode='lines', line=dict(color='red', dash='dash'), text = self.nom_b2.name, name='Beam 2')
            
            # Envelopes
            upper_b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.y_up, mode='lines', text = self.tw_b1.name, name='Upper envelope beam 1', fill=None, line=dict(color='rgba(0,0,255,0)'))
            lower_b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.y_down, mode='lines', text = self.tw_b1.name, name='Lower envelope beam 1', line=dict(color='rgba(0,0,255,0)'), 
                          fill='tonexty', fillcolor='rgba(0,0,255,0.1)')
            
            upper_b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.y_up, mode='lines', text = self.tw_b2.name, name='Upper envelope beam 2', fill=None, line=dict(color='rgba(255,0,0,0)'))
            lower_b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.y_down, mode='lines', text = self.tw_b2.name, name='Lower envelope beam 2', line=dict(color='rgba(255,0,0,0)'), 
                           fill='tonexty', fillcolor='rgba(255,0,0,0.1)')

            # Axes range and title
            fig.update_yaxes(range=[-0.05, 0.05], title_text="y [m]", row=2, col=1)

        else: print('Incorrect plane')

        if beam == 1:
            fig.add_trace(top_aper_b1, row=2, col=1)
            fig.add_trace(bottom_aper_b1, row=2, col=1)
        
        if beam == 2:
            fig.add_trace(top_aper_b2, row=2, col=1)
            fig.add_trace(bottom_aper_b2, row=2, col=1)

        # List of traces to be added to the graph
        traces_b1 = [b1, nom_b1, upper_b1, lower_b1]
        traces_b2 = [b2, nom_b2, upper_b2, lower_b2]

        for i in traces_b1:
            fig.add_trace(i, row=2, col=1) 
        for i in traces_b2:
            fig.add_trace(i, row=2, col=1)  

        if show_collimators:
            self._add_collimators(fig=fig, plane = plane, row=2, column=1, beam=beam)

        self._add_machine_components(fig=fig, row=1, column=1)
        self._distance_to_aperture(fig=fig, plane=plane, beam=beam)

        # Set layout
        fig.update_layout(height=800, width=800, plot_bgcolor='white', showlegend=False)

        # Change the axes limits and labels
        fig.update_yaxes(range=[-1, 1], showticklabels=False, showline=False, row=1, col=1)
        fig.update_xaxes(showticklabels=False, showline=False, row=1, col=1)
        fig.update_xaxes(title_text="s [m]", row=2, col=1)

        fig.show()
        

                

