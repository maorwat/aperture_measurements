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
from aper_package.utils import match_with_twiss

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
            df1 = df1[(df1['APER_1'] < 0.2) & (df1['APER_1'] != 0) & (df1['APER_2'] < 0.2) & (df1['APER_2'] != 0)]
            df2 = df2[(df2['APER_1'] < 0.2) & (df2['APER_1'] != 0) & (df2['APER_2'] < 0.2) & (df2['APER_2'] != 0)]
            # Make sure the aperture aligns with twiss data (if cycling was performed)
            df1 = match_with_twiss(self.tw_b1, df1)
            df2 = match_with_twiss(self.tw_b2, df2)
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

        # Check if the data had been cycled
        if hasattr(self, 'first_element'):
            # Find how much to shift the data
            shift = self._get_shift()
            self.tw_b1 = shift_by(self.tw_b1, shift, 's')
            self.tw_b2 = shift_by(self.tw_b2, shift, 's')

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
    
    def _get_shift(self):
        # Find the element to be set as the new zero
        element_position = self.tw_b1.loc[self.tw_b1['name'] == self.first_element, 's'].values[0]
        # To set to zero, shift to the left
        shift = -element_position
        return shift

    def cycle(self, element):
        
        # Save the first element for the case of retwissing
        self.first_element = element
        # Find how much to shift the data
        shift = self._get_shift()

        # Shift all the DataFrames by the same amount
        self.tw_b1 = shift_by(self.tw_b1, shift, 's')
        self.tw_b2 = shift_by(self.tw_b2, shift, 's')
        self.nom_b1 = shift_by(self.nom_b1, shift, 's')
        self.nom_b2 = shift_by(self.nom_b2, shift, 's')

        if hasattr(self, 'aper_b1'):
            self.aper_b1 = shift_by(self.aper_b1, shift, 'S')
            self.aper_b2 = shift_by(self.aper_b2, shift, 'S')

        if hasattr(self, 'colx_b1'):
            self.colx_b1 = shift_by(self.colx_b1, shift, 's')
            self.colx_b2 = shift_by(self.colx_b2, shift, 's')
            self.coly_b1 = shift_by(self.coly_b1, shift, 's')
            self.coly_b2 = shift_by(self.coly_b2, shift, 's')

        if hasattr(self, 'elements'):
            self.elements = shift_by(self.elements, shift, 'S')

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
        df = tfs.read(machine_components_path)

        # Make sure the elements align with twiss data (if cycling was performed)
        self.elements = match_with_twiss(self.tw_b1, df)
    
    
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
        

                

