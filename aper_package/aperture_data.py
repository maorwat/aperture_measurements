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

class Data:
    
    def __init__(self,
                 n = 0,
                 emitt = 3.5e-6,
                 line1 = None):
        
        """
        Initialize the AperPlot class with necessary configurations.

        Parameters:
        - ip (str): Interaction point.
        - n (int): An optional parameter, default is 0.
        - emitt (float): Normalised emittance value, default is 3.5e-6.
        - path1 (str): Path to the aperture file for beam 1.
        - line1 (str): Path to the line JSON file for beam 1.
        """
        
        # Define necessary variables
        self.emitt = emitt
        self.n = n
        self.length = 26658.88318

        # Load line data
        self.line_b1, self.line_b2 = self._load_lines_data(line1, 'json file for b1')

        # Define gamma using loaded line
        self.gamma = self.line_b1.particle_ref.to_pandas()['gamma0'][0]

        # Twiss
        self.twiss()

        # Keep the nominal crossing seperately for calculations
        self._define_nominal_crossing()
        self._distance_to_nominal('h')
        self._distance_to_nominal('v')

    def _load_lines_data(self, path1, title):
        """Load line data from a JSON file."""
        path1 = select_file(path1, title, '/eos/user/m/morwat/aperture_measurements/madx/2023/xsuite/')
        path2 = str(path1).replace('b1', 'b2')
        try:
            return xt.Line.from_json(path1), xt.Line.from_json(path2)
        except FileNotFoundError:
            raise FileNotFoundError(f"File {path1} not found.")

    def load_aperture(self, path1=None):
        # Load and process aperture data
        self.aper_b1, self.aper_b2 = self._load_aperture_data(path1, 'Select all_optics_B1.tfs')
    
    def _load_aperture_data(self, path1, title):
        """Load and process aperture data from a file."""
        # Select the aperture files
        path1 = select_file(path1, title, '/eos/user/m/morwat/aperture_measurements/madx/2023/')
        path2 = str(path1).replace('B1', 'B4')
        try:
            # Drop uneeded columns
            df1 = tfs.read(path1)[['S', 'NAME', 'APER_1', 'APER_2']]
            df2 = tfs.read(path2)[['S', 'NAME', 'APER_1', 'APER_2']]
            # Get rid of undefined values
            df1 = df1[(df1['APER_1'] < 1) & (df1['APER_1'] != 0) & (df1['APER_2'] < 1) & (df1['APER_2'] != 0)]
            df2 = df2[(df2['APER_1'] < 1) & (df2['APER_1'] != 0) & (df2['APER_2'] < 1) & (df2['APER_2'] != 0)]
            #Reverse S and X for beam 2
            df2.loc[:, 'S'] = df2['S'].iloc[-1]-df2['S']
        except FileNotFoundError:
            raise FileNotFoundError(f"File {path1} not found.")
        return df1.drop_duplicates(subset=['S']), df2.drop_duplicates(subset=['S'])

    def twiss(self):
        """
        Compute and process the twiss parameters for both beams.
        """
        # Generate twiss
        print('Computing twiss for beam 1...')
        tw_b1 = self.line_b1.twiss(skip_global_quantities=True).to_pandas()
        print('Computing twiss for beam 2...')
        tw_b2 = self.line_b2.twiss(skip_global_quantities=True, reverse=True).to_pandas()
        print('Done computing twiss.')

        # Process the twiss DataFrames
        self.tw_b1 = self._process_twiss(tw_b1)
        self.tw_b2 = self._process_twiss(tw_b2)

        # Define attributes
        self._define_sigma()
        self.envelope(self.n)

        # If retwissing, also calculate distance to nominal orbit
        if hasattr(self, 'nom_b1'):
            self._distance_to_nominal('h')
            self._distance_to_nominal('v')

    def _process_twiss(self, twiss_df):
        """
        Process the twiss DataFrame to remove unnecessary elements and columns.

        Parameters:
        - twiss_df: DataFrame containing the twiss parameters.

        Returns:
        - Processed DataFrame with selected columns and without 'aper' and 'drift' elements.
        """
        # Remove 'aper' and 'drift' elements
        twiss_df = twiss_df[~twiss_df['name'].str.contains('aper|drift')]

        # Select necessary columns
        return twiss_df[['s', 'name', 'x', 'y', 'betx', 'bety']]

    def cycle(self, ip):
        #TODO
        pass

    def _define_nominal_crossing(self):
        """
        Define the nominal crossing points for both beams based on the twiss parameters.
        This method extracts the 'name', 'x', 'y', and 's' columns from the twiss DataFrames
        for both beams and stores them in new attributes 'nom_b1' and 'nom_b2'.
        """

        # Define the nominal crossing for given configuration
        self.nom_b1 = self.tw_b1[['name', 'x', 'y', 's']].copy()
        self.nom_b2 = self.tw_b2[['name', 'x', 'y', 's']].copy()

    def _distance_to_nominal(self, plane):

        if plane == 'h': 
            up, down, nom, from_nom_to_top, from_nom_to_bottom = 'x_up', 'x_down', 'x', 'x_from_nom_to_top', 'x_from_nom_to_bottom'
        elif plane == 'v': 
            up, down, nom, from_nom_to_top, from_nom_to_bottom = 'y_up', 'y_down', 'y', 'y_from_nom_to_top', 'y_from_nom_to_bottom'

        # Ensure tw_b1 is not a slice
        self.tw_b1 = self.tw_b1.copy()
        self.tw_b2 = self.tw_b2.copy()

        self.tw_b1.loc[:, from_nom_to_top] = (self.tw_b1[up] - self.nom_b1[nom])*1000
        self.tw_b1.loc[:, from_nom_to_bottom] = (-self.tw_b1[down] + self.nom_b1[nom])*1000

        self.tw_b2.loc[:, from_nom_to_top] = (self.tw_b2[up] - self.nom_b2[nom])*1000
        self.tw_b2.loc[:, from_nom_to_bottom] = (-self.tw_b2[down] + self.nom_b2[nom])*1000

    def _define_sigma(self):
        """
        Calculate and add sigma_x and sigma_y columns to twiss DataFrames for both beams.
        """

        # Ensure tw_b1 is not a slice
        self.tw_b1 = self.tw_b1.copy()
        self.tw_b2 = self.tw_b2.copy()

        # Add columns for horizontal and vertical sigma
        for df in [self.tw_b1, self.tw_b2]:
            df.loc[:, 'sigma_x'] = np.sqrt(df['betx'] * self.emitt / self.gamma)
            df.loc[:, 'sigma_y'] = np.sqrt(df['bety'] * self.emitt / self.gamma)

    def envelope(self, n):
        """
        Calculate the envelope edges for the twiss DataFrames based on the envelope size.

        Parameters:
        - n (float): The envelope size in sigma units.
        """

        # Envelope size in sigma units
        self.n = n

        # Ensure tw_b1 is not a slice
        self.tw_b1 = self.tw_b1.copy()
        self.tw_b2 = self.tw_b2.copy()
        
        # Calculate the envelope edges for the new envelope size
        for df in [self.tw_b1, self.tw_b2]:
            df['x_up'] = df['x'] + n * df['sigma_x']
            df['x_down'] = df['x'] - n * df['sigma_x']
            df['y_up'] = df['y'] + n * df['sigma_y']
            df['y_down'] = df['y'] - n * df['sigma_y']

    def _get_col_df(self, f, angle, beam, plane):

        if beam == 'b1': twiss_data=self.tw_b1
        elif beam == 'b2': twiss_data=self.tw_b2

        if plane == 'h': sigma_key, x_key='sigma_x', 'x'
        if plane == 'v': sigma_key, x_key='sigma_y', 'y'

        # Create a pandas data frame with only gap and angle
        col = pd.DataFrame(f['collimators'][beam]).loc[['gap', 'angle']].T
        col = col.reset_index().rename(columns={'index': 'name'})
        # Drop undefined values
        col = col[col['angle'] == angle].dropna()
        # Merge with twiss data to find collimator positions
        col = pd.merge(col, twiss_data, on='name', how='left')

        # Calculate gap in meters and add to the dataFrame
        col.loc[:, 'top_gap_col'] = col[sigma_key] * col['gap'] + col[x_key]
        col.loc[:, 'bottom_gap_col'] = -col[sigma_key] * col['gap'] + col[x_key]

        # Return the collimators data
        return col
    
    def load_collimators(self, path=None):

        # Load the file
        collimators_path = select_file(path, 'collimators .yaml file', '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/colldbs/')
        
        with open(collimators_path, 'r') as file:
            f = yaml.safe_load(file)

        # Create the DataFrames
        self.colx_b1 = self._get_col_df(f, 0, 'b1', 'h')
        self.colx_b2 = self._get_col_df(f, 0, 'b2', 'h')

        self.coly_b1 = self._get_col_df(f, 90, 'b1', 'v')
        self.coly_b2 = self._get_col_df(f, 90, 'b2', 'v')
    
    def load_elements(self, path=None):

        # Load the file
        machine_components_path = select_file(path, 'thick all_optics.tfs file', '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/')
        
        self.elements = tfs.read(machine_components_path)
    
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

    def _add_collimators(self, fig, plane, row, column):

        if plane == 'h': df_b1, df_b2 = self.colx_b1, self.colx_b2
        elif plane == 'v': df_b1, df_b2 = self.coly_b1, self.coly_b2

        # Plot
        for df in [df_b1, df_b2]:
            for i in range(df.shape[0]):
                x0, y0b, y0t, x1, y1 = df.s.iloc[i] - 0.5, df.bottom_gap_col.iloc[i], df.top_gap_col.iloc[i], df.s.iloc[i] + 0.5, 0.05
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0t, y1, y1, y0t], fill="toself", mode='lines',
                            fillcolor='black', line=dict(color='black'), name=df.name.iloc[i]), row=2, col=1)
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0b, -y1, -y1, y0b], fill="toself", mode='lines',
                            fillcolor='black', line=dict(color='black'), name=df.name.iloc[i]), row=2, col=1)

        # As default show only beam 1 collimators
        visibility_arr_b1 = np.concatenate((np.full(df_b1.shape[0]*2, True), np.full(df_b2.shape[0]*2, False)))

        return visibility_arr_b1
    
    def _add_machine_components(self, fig, row, column):

        # Specify the elements to plot and corresponding colors
        objects = ["SBEND", "COLLIMATOR", "SEXTUPOLE", "RBEND", "QUADRUPOLE"]
        colors = ['lightblue', 'black', 'hotpink', 'green', 'red']

        # Array to store visibility of the elements
        visibility_arr = np.array([], dtype=bool)

        # Iterate over all object types
        for n, obj in enumerate(objects):
            
            obj_df = self.elements[self.elements['KEYWORD'] == obj]
            
            # Add elements to the plot
            for i in range(obj_df.shape[0]):

                x0, x1 = obj_df.iloc[i]['S']-obj_df.iloc[i]['L']/2, obj_df.iloc[i]['S']+obj_df.iloc[i]['L']/2                
                if obj=='QUADRUPOLE': y0, y1 = 0, np.sign(obj_df.iloc[i]['K1L']).astype(int)                    
                else: y0, y1 = -0.5, 0.5

                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor=colors[n], line=dict(color=colors[n]), name=obj_df.iloc[i]['NAME']), row=row, col=column) 

            # Append to always show the elements
            visibility_arr = np.append(visibility_arr, np.full(obj_df.shape[0], True))
        
        return visibility_arr

    def show(self, 
             plane,
             add_VELO=True):

        # Create figure
        fig = make_subplots(rows=2, cols=1, row_heights=[0.2, 0.8], shared_xaxes=True)

        # Define hover template with customdata
        hover_template = ("s: %{x} [m]<br>"
                            "x: %{y} [m]<br>"
                            "element: %{text}<br>"
                            "distance from nominal: %{customdata} [mm]")
        
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
            upper_b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.x_up, mode='lines', 
                                  text = self.tw_b1.name, name='Upper envelope beam 1', 
                                  fill=None, line=dict(color='rgba(0,0,255,0)'),
                                  customdata=self.tw_b1.x_from_nom_to_top, hovertemplate=hover_template)
            lower_b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.x_down, mode='lines', 
                                  text = self.tw_b1.name, name='Lower envelope beam 1', 
                                  line=dict(color='rgba(0,0,255,0)'), fill='tonexty', fillcolor='rgba(0,0,255,0.1)',
                                  customdata=self.tw_b1.x_from_nom_to_bottom, hovertemplate=hover_template)
            upper_b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.x_up, mode='lines', 
                                  text = self.tw_b2.name, name='Upper envelope beam 2', 
                                  fill=None, line=dict(color='rgba(255,0,0,0)'),
                                  customdata=self.tw_b2.x_from_nom_to_top, hovertemplate=hover_template)
            lower_b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.x_down, mode='lines', 
                                  text = self.tw_b2.name, name='Lower envelope beam 2', 
                                  line=dict(color='rgba(255,0,0,0)'), fill='tonexty', fillcolor='rgba(255,0,0,0.1)', 
                                  customdata=self.tw_b2.x_from_nom_to_bottom, hovertemplate=hover_template)
            
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
            upper_b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.y_up, mode='lines', 
                                  text = self.tw_b1.name, name='Upper envelope beam 1', 
                                  fill=None, line=dict(color='rgba(0,0,255,0)'),
                                  customdata=self.tw_b1.y_from_nom_to_top, hovertemplate=hover_template)
            lower_b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.y_down, mode='lines', 
                                  text = self.tw_b1.name, name='Lower envelope beam 1', 
                                  line=dict(color='rgba(0,0,255,0)'), fill='tonexty', fillcolor='rgba(0,0,255,0.1)',
                                  customdata=self.tw_b1.y_from_nom_to_bottom, hovertemplate=hover_template)
            upper_b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.y_up, mode='lines', 
                                  text = self.tw_b2.name, name='Upper envelope beam 2', 
                                  fill=None, line=dict(color='rgba(255,0,0,0)'),
                                  customdata=self.tw_b2.y_from_nom_to_top, hovertemplate=hover_template)
            lower_b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.y_down, mode='lines', 
                                  text = self.tw_b2.name, name='Lower envelope beam 2', 
                                  line=dict(color='rgba(255,0,0,0)'), fill='tonexty', fillcolor='rgba(255,0,0,0.1)',
                                  customdata=self.tw_b2.y_from_nom_to_bottom, hovertemplate=hover_template)

            # Axes range and title
            fig.update_yaxes(range=[-0.05, 0.05], title_text="y [m]", row=2, col=1)

        else: print('Incorrect plane')

        # List of traces to be added to the graph
        traces_b1 = [b1, nom_b1, upper_b1, lower_b1]
        traces_b2 = [b2, nom_b2, upper_b2, lower_b2]

        for i in traces_b1:
            fig.add_trace(i, row=2, col=1) 
        for i in traces_b2:
            fig.add_trace(i, row=2, col=1) 

        visibility_beams = np.full(8, True)

        fig.add_trace(top_aper_b1, row=2, col=1)
        fig.add_trace(bottom_aper_b1, row=2, col=1)
        fig.add_trace(top_aper_b2, row=2, col=1)
        fig.add_trace(bottom_aper_b2, row=2, col=1)

        visibility_aper_b1 = np.array([True, True, False, False])

        try: 
            visibility_col_b1 = self._add_collimators(fig=fig, plane = plane, row=2, column=1)
        except Exception as e:
            visibility_col_b1 = np.array([], dtype=bool)

        try:
            visibility_elements = self._add_machine_components(fig=fig, row=1, column=1)
        except Exception as e:
            pass

        visibility_b1 = np.concatenate((visibility_beams, visibility_aper_b1, visibility_col_b1, visibility_elements))
        visibility_b2 = np.concatenate((visibility_beams, np.logical_not(visibility_aper_b1), np.logical_not(visibility_col_b1), visibility_elements))

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
        fig.update_yaxes(range=[-1, 1], showticklabels=False, showline=False, row=1, col=1)
        fig.update_xaxes(showticklabels=False, showline=False, row=1, col=1)
        fig.update_xaxes(title_text="s [m]", row=2, col=1)

        # Add the buttons to the layout
        fig.update_layout(updatemenus=[{"buttons": buttons, "showactive": True, 'active': 0, 'pad': {"r": 10, "t": 10},
                                        'xanchor': "left", 'yanchor': 'top', 'x': 0.15, 'y': 1.1}])
        
        # Add annotation
        fig.update_layout(annotations=[dict(text="Aperture data:", showarrow=False, 
                                            x=0, y=1.075, xref="paper", yref='paper', align="left")])
        
        # Add VELO
        ip8 = self.tw_b1.loc[self.tw_b1['name'] == 'ip8', 's']

        if add_VELO:
            fig.add_shape(
                type="rect",
                x0=(ip8.values[0]-0.2), x1=(ip8.values[0]+0.8),
                y0=-0.05, y1=0.05,
                xref='x',
                yref='y',
                line=dict(
                    color="Orange",
                    width=1
                ), row=2, col=1
            )

        fig.show()
        

                

