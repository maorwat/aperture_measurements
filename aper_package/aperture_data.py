import numpy as np
import pandas as pd
import tfs
import yaml
import re
from pathlib import Path

from typing import Any, Dict, Optional
 
import xtrack as xt

from aper_package.utils import *

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=DeprecationWarning)

class ApertureData:
    
    def __init__(self,
                 path_b1: str,
                 path_b2: Optional[str] = None,
                 n: Optional[float] = 0,
                 emitt: Optional[str] = 3.5e-6,
                 label = None):
        
        """
        Initialize the AperData class with necessary configurations.

        Parameters:
            ip: Interaction point.
            n: An optional parameter, default is 0.
            emitt: Normalised emittance value, default is 3.5e-6.
            line1: Path to the line JSON file for beam 1, default is None, can be selected interactively.
        """
        
        # Define necessary variables
        self.emitt = emitt
        self.n = n
    
        # Load line data
        self.line_b1, self.line_b2 = self._load_lines_data(path_b1, path_b2)

        # Define gamma and length of the accelerator using loaded line
        self.gamma = self.line_b1.particle_ref.to_pandas()['gamma0'][0]
        self.beta = self.line_b1.particle_ref.to_pandas()['beta0'][0]
        self.length = self.line_b1.get_length()
        self.label = label

        # Find knobs
        self._define_knobs()
        self._define_acb_knobs()
        
        # Turn off all multipoles with order > 2 and relax the aperture to enable higher crossing angles
        self.turn_off_multipoles()
        self.relax_aperture()

        # Twiss
        self.twiss()
        self.define_mcbs()

        # Keep the nominal crossing seperately for calculations
        self._define_nominal_crossing()
        self._distance_to_nominal('horizontal')
        self._distance_to_nominal('vertical')

    def print_to_label(self, string):
        if self.label is not None:
            self.label.value = string
        else: print_and_clear(string)

    def _load_lines_data(self, path_b1: str, path_b2: str) -> None:
        """Load lines data from a JSON file.
        
        Parameters:
            path_b1: Path to the line JSON file for beam 1.
            path_b2: Path to the line JSON file for beam 2, if not given,
                    the path will be created by replacing b1 with b2
        """
        # If path for beam 2 was not given, construct it by replacing b1 with b2
        if not path_b2: path_b2 = str(path_b1).replace('b1', 'b2')

        return xt.Line.from_json(path_b1), xt.Line.from_json(path_b2)

    def _define_knobs(self) -> None:
        """
        Identifies and stores the knobs (parameters with 'on_' in their name) from the line_b1 variable vault.
        Stores the initial and current values of these knobs in a DataFrame.
        """

        # Find knobs
        knobs = self.line_b1.vv.vars.keys()
        knobs = [value for value in knobs if 'on_' in value]

        # Identify knobs that contain 'on_' in their names
        knobs = [k for k in self.line_b1.vv.vars.keys() if 'on_' in k]

        # Extract the initial values of the knobs
        knob_values = [self.line_b1.vv.get(knob) for knob in knobs]

        # Create a DataFrame with knobs and their values
        self.knobs = pd.DataFrame({
            'knob': knobs,
            'initial value': knob_values,
            'current value': knob_values
        })

        self.knobs = self.knobs.sort_values(by='knob').reset_index(drop=True)

    def _define_nominal_crossing(self) -> None:
        """
        This method extracts the 'name', 'x', 'y', and 's' columns from the twiss DataFrames
        for both beams and stores them in new attributes 'nom_b1' and 'nom_b2'.
        """

        # Define the nominal crossing for given configuration
        self.nom_b1 = self.tw_b1[['name', 'x', 'y', 's']].copy()
        self.nom_b2 = self.tw_b2[['name', 'x', 'y', 's']].copy()

    def twiss(self) -> None:
        """
        Compute and process the twiss parameters for both beams.
        """
        # Generate twiss
        self.print_to_label('Computing twiss for beam 1...')
        tw_b1 = self.line_b1.twiss(skip_global_quantities=True).to_pandas()
        self.print_to_label('Computing twiss for beam 2...')
        tw_b2 = self.line_b2.twiss(skip_global_quantities=True, reverse=True).to_pandas()
        self.print_to_label('Done computing twiss.')

        # Process the twiss DataFrames
        self.tw_b1 = self._process_twiss(tw_b1)
        self.tw_b2 = self._process_twiss(tw_b2)

        # Check if the data had been cycled
        if hasattr(self, 'first_element'):
            # Find how much to shift the data
            shift = self._get_shift(self.first_element)
            self.tw_b1 = shift_by(self.tw_b1, shift, 's')
            self.tw_b2 = shift_by(self.tw_b2, shift, 's')

        # Define attributes
        self._define_sigma()
        self.envelope(self.n)

        # If retwissing, also calculate distance to nominal orbit
        if hasattr(self, 'nom_b1'):
            self._distance_to_nominal('horizontal')
            self._distance_to_nominal('vertical')

    def _process_twiss(self, twiss_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process the twiss DataFrame to remove unnecessary elements and columns.

        Parameters:
            twiss_df: DataFrame containing the twiss parameters.

        Returns:
            Processed DataFrame with selected columns and without 'aper' and 'drift' elements.
        """
        # Remove 'aper' and 'drift' elements
        twiss_df = twiss_df[~twiss_df['name'].str.contains('aper|drift')]

        # Select necessary columns
        return twiss_df[['s', 'name', 'x', 'y', 'betx', 'bety', 'px', 'py', 'dx', 'dy']]

    def _distance_to_nominal(self, plane: str) -> None:
        """
        Calculates the distance to nominal positions for the specified plane (horizontal or vertical).

        Parameters:
            plane: The plane for which to calculate the distances.
        """

        if plane == 'horizontal': 
            up, down, nom, from_nom_to_top, from_nom_to_bottom = 'x_up', 'x_down', 'x', 'x_from_nom_to_top', 'x_from_nom_to_bottom'
        elif plane == 'vertical': 
            up, down, nom, from_nom_to_top, from_nom_to_bottom = 'y_up', 'y_down', 'y', 'y_from_nom_to_top', 'y_from_nom_to_bottom'

        # Ensure tw_b1 is not a slice
        self.tw_b1 = self.tw_b1.copy()
        self.tw_b2 = self.tw_b2.copy()

        self.tw_b1.loc[:, from_nom_to_top] = abs(self.tw_b1[up] - self.nom_b1[nom])*1000
        self.tw_b1.loc[:, from_nom_to_bottom] = abs(self.tw_b1[down] - self.nom_b1[nom])*1000

        self.tw_b2.loc[:, from_nom_to_top] = abs(self.tw_b2[up] - self.nom_b2[nom])*1000
        self.tw_b2.loc[:, from_nom_to_bottom] = abs(self.tw_b2[down] - self.nom_b2[nom])*1000

    def _define_sigma(self) -> None:
        """
        Calculate and add sigma_x and sigma_y columns to twiss DataFrames for both beams.
        """
        # Ensure tw_b1 is not a slice
        self.tw_b1 = self.tw_b1.copy()
        self.tw_b2 = self.tw_b2.copy()

        self.epsilon = self.emitt / (self.gamma*self.beta)

        # Add columns for horizontal and vertical sigma
        for df in [self.tw_b1, self.tw_b2]:
            df.loc[:, 'sigma_x'] = np.sqrt(df['betx'] * self.epsilon) # Divide by the relativistic factor and the relative particle velocity to get emittance
            df.loc[:, 'sigma_y'] = np.sqrt(df['bety'] * self.epsilon)

    def _get_shift(self, first_element: str) -> float:
        """
        Calculates the shift required to set the specified element as the new zero point.

        Returns:
            float: The amount to shift the data.
        """
        # Find the element to be set as the new zero
        element_positions = self.tw_b1.loc[self.tw_b1['name'] == first_element]['s'].values

        # If element not found
        if len(element_positions) == 0:
            # Don't cycle
            shift = 0
            self.print_to_label(f"Element '{first_element}' not found in the DataFrame.")
        else:
            # Save the first element for the case of retwissing
            self.first_element = first_element
            # To set to zero, shift to the left
            shift = -element_positions[0]
        
        return shift

    def turn_off_multipoles(self):
        """
        Disable high-order multipoles in the elements of line_b1 and line_b2.

        This method sets the `knl` and `ksl` arrays to zero for all 
        `xt.Multipole` elements with an order greater than 2 in both `line_b1` 
        and `line_b2`.
        """

        for i, n in enumerate(self.line_b1.elements):
            if isinstance(n, xt.Multipole) and n.order>2:
                n.knl.fill(0)
                n.ksl.fill(0)

        for i, n in enumerate(self.line_b2.elements):
            if isinstance(n, xt.Multipole) and n.order>2:
                n.knl.fill(0)
                n.ksl.fill(0)

    def relax_aperture(self):
        """
        Relax the aperture constraints for elements in line_b1 and line_b2.

        This method sets the aperture parameters `a_squ`, `b_squ`, `a_b_squ`, 
        `max_x`, and `max_y` to 1 for all `xt.LimitEllipse` and 
        `xt.LimitRectEllipse` elements in both `line_b1` and `line_b2`.
        """
        for i, n in enumerate(self.line_b1.elements):
            if isinstance(n, xt.LimitEllipse):
                n.a_squ = 1
                n.b_squ = 1
                n.a_b_squ = 1
            if isinstance(n, xt.LimitRectEllipse):
                n.a_squ = 1
                n.b_squ = 1
                n.a_b_squ = 1
                n.max_x = 1
                n.max_y = 1

        for i, n in enumerate(self.line_b2.elements):
            if isinstance(n, xt.LimitEllipse):
                n.a_squ = 1
                n.b_squ = 1
                n.a_b_squ = 1
            if isinstance(n, xt.LimitRectEllipse):
                n.a_squ = 1
                n.b_squ = 1
                n.a_b_squ = 1
                n.max_x = 1
                n.max_y = 1

    def cycle(self, element: str) -> None:
        """
        Cycles all the data to set a new zero point.

        Parameters:
            element: The new first element to be cycled in, must be a lowercase string.
        """
        # Covert to lowercase if not already
        element = element.lower()
        
        # Find how much to shift the data
        shift = self._get_shift(element) # Here I set a new first element

        # List of attributes to shift, categorized by their shift type
        attributes_to_shift = {
            's': ['tw_b1', 'tw_b2', 'nom_b1', 'nom_b2', 'colx_b1', 'colx_b2', 'coly_b1', 'coly_b2'],
            'S': ['aper_b1', 'aper_b2', 'elements']
        }

        if shift != 0:
            # Shift the attributes
            for shift_type, attrs in attributes_to_shift.items():
                for attr in attrs:
                    if hasattr(self, attr):
                        try:
                            setattr(self, attr, shift_by(getattr(self, attr), shift, shift_type))
                        except Exception as e:
                            self.print_to_label(f"Error shifting {attr}: {e}")

    def envelope(self, n: float) -> None:
        """
        Calculate the envelope edges for the twiss DataFrames based on the envelope size.

        Parameters:
            n : The envelope size in sigma units.
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

        if hasattr(self, 'nom_b1'):
            self._distance_to_nominal('horizontal')
            self._distance_to_nominal('vertical')

    def change_knob(self, knob: str, value: float) -> None:
        """
        Update the specified knob to the given value for both beam lines (b1 and b2).
        Also update the corresponding entry in the knobs DataFrame.

        Parameters:
            knob: The name of the knob to be changed.
            value: The new value to set for the knob.
        """
        # Set the new value for both lines
        self.line_b1.vars[knob] = value
        self.line_b2.vars[knob] = value

        # Update the current value with the new value
        self.knobs.loc[self.knobs['knob'] == knob, 'current value'] = value

    def change_acb_knob(self, knob, value, beam) -> None:
        """
        Update the specified knob to the given value for one beam lines.
        Also update the corresponding entry in the knobs DataFrame.

        Parameters:
            knob: The name of the knob to be changed.
            value: The new value to set for the knob.
            plane: The plane to specify the dataframe with current and inital values 
            beam: The beam to specify the dataframe with current and inital values 
        """

        # Specify which df to update
        if beam == 'beam 1':
            line = self.line_b1
            if 'h' in knob: knobs_df = self.acbh_knobs_b1
            elif 'v' in knob: knobs_df = self.acbv_knobs_b1
        elif beam == 'beam 2':
            line = self.line_b2
            if 'h' in knob: knobs_df = self.acbh_knobs_b2
            elif 'v' in knob: knobs_df = self.acbv_knobs_b2

        # Set the new value
        line.vars[knob] = value

        # Update the current value with the new value
        knobs_df.loc[knobs_df['knob'] == knob, 'current value'] = value
    
    def _define_acb_knobs(self) -> None:
        """
        Create dataframes with knobs controling current of orbit correctors
        """
        # Vertical plane
        self.acbv_knobs_b1 = self._create_acb_knob_df(r'acb.*v.*b1$', self.line_b1)
        self.acbv_knobs_b2 = self._create_acb_knob_df(r'acb.*v.*b2$', self.line_b2)

        # Horizontal plane
        self.acbh_knobs_b1 = self._create_acb_knob_df(r'acb.*h.*b1$', self.line_b1)
        self.acbh_knobs_b2 = self._create_acb_knob_df(r'acb.*h.*b2$', self.line_b2)

    def _create_acb_knob_df(self, search_string, line):
        """
        Creates data frames with acb knobs and their values for given plane and beam 
        """

        knobs = [i for i in line.vv.vars.keys() if re.search(search_string, i)] 
        values = [line.vv.get(knob) for knob in knobs]

        df = pd.DataFrame({
            'knob': knobs, # Knob names
            'initial value': values, # Initial values for resetting
            'current value': values # Current values
        })

        # Add a column to facilitate sorting by region
        df['sort_key'] = df['knob'].apply(self._extract_sort_key)

        return df

    def sort_acb_knobs_by_region(self, beam, plane, region):
        """
        Create sorted lists of knobs corresponding to a selected region
        """
        # Select the dataframe to sort
        if plane == 'horizontal': 
            if beam == 'beam 1': 
                df = self.acbh_knobs_b1
            elif beam == 'beam 2': 
                df = self.acbh_knobs_b2
        if plane == 'vertical':
            if beam == 'beam 1': 
                df = self.acbv_knobs_b1
            elif beam == 'beam 2': 
                df = self.acbv_knobs_b2

        # Create a slice of the df corresponding to the selected region
        df_l1 = df[df['sort_key'].str.contains(region)].copy()
        # Sort the knobs
        df_l1.loc[:, 'sort_number'] = df_l1['sort_key'].str.extract(r'(\d+)').astype(int)
        sorted_df = df_l1.sort_values(by='sort_number').drop('sort_number', axis=1)

        # Return as a list 
        return sorted_df['knob'].to_list()

    def _extract_sort_key(self, knob_name):
        """
        Extracts the number and region from the knob name        
        """
        knob_name = knob_name.replace('.', '')
        # Match patterns like '4l1', '8l1', '4r1', '4r8', etc.
        match = re.search(r'(\d+[lr]\d+)', knob_name)
        if match:
            return match.group(1)
        else:
            return ''

    def reset_knobs(self) -> None:
        """
        Resets the knobs to their initial values if they have been changed.
        Then recalculates the twiss parameters.
        """     

        # Iterate over the knobs DataFrame and reset values where necessary
        changed_knobs = self.knobs[self.knobs['current value'] != self.knobs['initial value']]

        for _, row in changed_knobs.iterrows():
            self.change_knob(row['knob'], row['initial value'])
            # Update the 'current value' to reflect the reset
            self.knobs.at[row.name, 'current value'] = row['initial value']

        # Recalculate the twiss parameters    
        self.twiss()
    
    def reset_all_acb_knobs(self):
        """
        Resets the acb knobs to their initial values if they have been changed.
        Then recalculates the twiss parameters.
        """  
        self._reset_acb_knobs(self.acbh_knobs_b1)
        self._reset_acb_knobs(self.acbh_knobs_b2)
        self._reset_acb_knobs(self.acbv_knobs_b1)
        self._reset_acb_knobs(self.acbv_knobs_b2)

        # Recalculate the twiss parameters    
        self.twiss()

    def _reset_acb_knobs(self, acb_knobs_df) -> None:
        """
        Helper method to reset the knobs to their initial values if they have been changed.
        """     

        # Iterate over the knobs DataFrame and reset values where necessary
        changed_knobs = acb_knobs_df[acb_knobs_df['current value'] != acb_knobs_df['initial value']]

        for _, row in changed_knobs.iterrows():
            self.change_knob(row['knob'], row['initial value'])
            # Update the 'current value' to reflect the reset
            acb_knobs_df.at[row.name, 'current value'] = row['initial value']

    def load_aperture(self, path_b1: str, path_b2: Optional[str]=None) -> None:
        # Load and process aperture data
        self.aper_b1, self.aper_b2 = self._load_aperture_data(path_b1, path_b2)
        self._load_aperture_tolerance()
    
    def _load_aperture_data(self, path_b1, path_b2) -> pd.DataFrame:
        """Load and process aperture data from a file.
        
        Parameters:
            path_b1: Path to aperture all_optics_B1.tfs file.
            path_b2: Path to aperture all_optics_B4.tfs file, if not given,
                    the path will be created by replacing B1 with B4.

        Returns:
            Processeed aperture DataFrames for beams 1 and 2, respectively.
        """

        # If path for beam 2 was not given, construct it by replacing b1 with b2
        if not path_b2: path_b2 = str(path_b1).replace('B1', 'B4')

        # Drop uneeded columns
        df1 = tfs.read(path_b1)[['NAME', 'APER_1', 'APER_2', 'APER_3', 'APER_4', 'MECH_SEP']]
        df2 = tfs.read(path_b2)[['NAME', 'APER_1', 'APER_2', 'APER_3', 'APER_4', 'MECH_SEP']]
        # Get rid of undefined values
        df1 = df1[(df1['APER_1'] < 0.2) & (df1['APER_1'] != 0) & (df1['APER_2'] < 0.2) & (df1['APER_2'] != 0)]
        df2 = df2[(df2['APER_1'] < 0.2) & (df2['APER_1'] != 0) & (df2['APER_2'] < 0.2) & (df2['APER_2'] != 0)]
        # Make sure the aperture aligns with twiss data (if cycling was performed)
        df1 = match_with_twiss(self.tw_b1, df1)
        df2 = match_with_twiss(self.tw_b2, df2)

        return df1.drop_duplicates(subset=['S']), df2.drop_duplicates(subset=['S'])
    
    def _load_aperture_tolerance(self):
        """
        Loads madx file with aperture tolerances and adds them to the aper_b1 and aper_b2 dataframe
        """

        home_path = str(Path.cwd().parent)
        tol_b1 = self._create_df_from_madx(home_path+'/test_data/aper_tol_profiles-as-built.b1.madx')
        tol_b2 = self._create_df_from_madx(home_path+'/test_data/aper_tol_profiles-as-built.b2.madx')

        # Merge with the existing aperture dataframe attribute
        self.aper_b1 = pd.merge(tol_b1, self.aper_b1, on='NAME', how='right')
        self.aper_b2 = pd.merge(tol_b2, self.aper_b2, on='NAME', how='right')

    def _create_df_from_madx(self, file_path):
        """
        Creates a dataframe with elements and corresponding aperture tolerances from specified madx file
        """
        # Create lists to store parsed data
        element_names = []
        aper_tol_values = []

        # Open and read the file
        with open(file_path, 'r') as file:
            for line in file:
                # Skip comment lines
                if line.startswith('!') or line.strip() == '':
                    continue

                # Use regex to find element name and APER_TOL values
                match = re.match(r'(\w[\w.]+),\s*APER_TOL=\{([\d\.,\s\-]+)\};', line)
                if match:
                    element_name = match.group(1)
                    # Extract the tolerance values and convert them to a list of floats
                    aper_tol = [float(x) for x in match.group(2).split(',')]
                    
                    # Store the parsed data
                    element_names.append(element_name)
                    aper_tol_values.append(aper_tol)

        # Create a pandas DataFrame from the parsed data
        df = pd.DataFrame(aper_tol_values, columns=['APER_TOL_1', 'APER_TOL_2', 'APER_TOL_3'])
        df['NAME'] = element_names

        # Reorder the columns to have 'Element' first
        df = df[['NAME', 'APER_TOL_1', 'APER_TOL_2', 'APER_TOL_3']]

        return df
    
    def calculate_n1(self, delta_beta, delta, beam, element, rtol=None, xtol=None, ytol=None, delta_co=0.002):
        """
        Method to calculate n1
        Parameters:
            delta_beta: Beta beating given in %
            delta: Momentum spread
            beam: 'beam 1' or 'beam 2'
            element: Element for which n1 will be calculated
            rtol, xtol, ytol: Aperture tolerances, if not given, the tolerances from self.aper_b[12] are be takem
            delta_co: Closed orbit error, default 2 mm

        Returns:
            aperx_error: Total error on aperture 
            sigmax_error: Sigma including beta-beating and dispersion
            n1_x: Calculated n1 in the horizontal plane
            same for vertical plane
        """
        element_position = find_s_value(element, self)
        if element_position == None:
            self.print_to_label('Incorrect element')
            return
        
        if beam == 'beam 1':
            merged = merge_twiss_and_aper(self.tw_b1, self.aper_b1)
        elif beam == 'beam 2':
            merged = merge_twiss_and_aper(self.tw_b2, self.aper_b2)  

        row = merged.iloc[(merged['s'] - element_position).abs().idxmin()] 

        aperx_error, apery_error = self.calculate_aper_error(row, rtol, xtol, ytol, delta_co)
        sigmax_after_errors, sigmay_after_errors = self.calculate_sigma_with_error(row, delta_beta, delta) 
        
        n1_x = (row.APER_1-aperx_error)/sigmax_after_errors
        n1_y = (row.APER_2-apery_error)/sigmay_after_errors

        return aperx_error, sigmax_after_errors, n1_x, apery_error, sigmay_after_errors, n1_y
        
    def calculate_aper_error(self, row, rtol, xtol, ytol, delta_co):

        # Check if tolerances defined
        if rtol is None or xtol is None or ytol is None:
            # If not check is available in the data frame
            if row[['APER_TOL_1', 'APER_TOL_2', 'APER_TOL_3']].isnull().any(): 
                # If not return
                self.print_to_label('Aperture tolerance not defined')
                return
            # Else take errors from the dataframe
            else: rtol, xtol, ytol = row.APER_TOL_1, row.APER_TOL_2, row.APER_TOL_3
        
        tol_x = rtol+xtol
        tol_y = rtol+ytol

        aperx_error = tol_x+delta_co
        apery_error = tol_y+delta_co

        return aperx_error, apery_error
    
    def calculate_sigma_with_error(self, row, delta_beta, delta):

        delta_beta = delta_beta/100 + 1 # Convert % 

        sigmax_after_errors = np.sqrt(delta_beta*row.betx*self.epsilon+(row.dx**2)*(delta**2))
        sigmay_after_errors = np.sqrt(delta_beta*row.bety*self.epsilon+(row.dy**2)*(delta**2))

        return sigmax_after_errors, sigmay_after_errors
    
    def load_collimators_from_yaml(self, path: str) -> None:
        """
        Loads collimator data from a YAML file and creates DataFrames for collimator positions.

        Parameters:
            path : The path to the collimators YAML file. If None, a default path is used.
        """

        # Load the file
        with open(path, 'r') as file:
            f = yaml.safe_load(file)

        # Create the DataFrames
        self.colx_b1 = self._get_col_df_from_yaml(f, 0, 'b1', 'horizontal')
        self.colx_b2 = self._get_col_df_from_yaml(f, 0, 'b2', 'horizontal')

        self.coly_b1 = self._get_col_df_from_yaml(f, 90, 'b1', 'vertical')
        self.coly_b2 = self._get_col_df_from_yaml(f, 90, 'b2', 'vertical')

    def _get_col_df_from_yaml(self, f: Dict[str, Any], angle: float, beam: str, plane: str) -> pd.DataFrame:
        """
        Creates a DataFrame containing collimator data for the specified beam and plane.

        Parameters:
            f : A dictionary containing collimator data.
            angle : The angle to filter collimators by.
            beam : The beam identifier ('b1' or 'b2').
            plane : The plane identifier ('h' for horizontal, 'v' for vertical).

        Returns:
            pd.DataFrame: A DataFrame with the collimator data, including calculated gaps.
        """

        if beam == 'b1': twiss_data=self.tw_b1
        elif beam == 'b2': twiss_data=self.tw_b2

        if plane == 'horizontal': sigma_key, x_key='sigma_x', 'x'
        if plane == 'vertical': sigma_key, x_key='sigma_y', 'y'

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
    
    def load_elements(self, path: str) -> None:
        """
        Loads machine component data from a TFS file and matches it with the twiss data.

        Parameters:
            path : The path to the machine components TFS file. If None, a default path is used.

        """
        # Load the file
        df = tfs.read(path)[['NAME', 'KEYWORD', 'L', 'K1L']]

        # Make sure the elements align with twiss data (if cycling was performed)
        self.elements = match_with_twiss(self.tw_b1, df)

    def define_mcbs(self):

        self.mcbh_b1 = self._define_mcbs('beam 1', 'mcb.*h.*b1$')
        self.mcbh_b2 = self._define_mcbs('beam 2', 'mcb.*h.*b2$')
        self.mcbv_b1 = self._define_mcbs('beam 1', 'mcb.*v.*b1$')
        self.mcbv_b2 = self._define_mcbs('beam 2', 'mcb.*v.*b2$')

    def _define_mcbs(self, beam, key):
        """
        Creates lists of mcb orbit correctors for each beam for given plane
        """
        if beam == 'beam 1': line, tw = self.line_b1, self.tw_b1
        elif beam == 'beam 2': line, tw = self.line_b2, self.tw_b2
        
        mcb_list = [element for element in list(line.element_names) 
                if re.search(key, element)]
        
        df = tw[tw['name'].isin(mcb_list)][['name', 's']]

        df['sort_key'] = df['name'].str.extract(r'\.([ab]?\d+[lr]\d)\.')  # Extract pattern like '4l1', 'a4l1', '9r1', etc.
        df['sort_key'] = df['sort_key'].str.replace(r'[ab]', '', regex=True)  # Remove 'a' or 'b' if present

        return df
    
    def sort_mcbs_by_region(self, beam, plane, region):
        """
        Create sorted lists of knobs corresponding to a selected region
        """
        # Select the dataframe to sort
        if plane == 'horizontal': 
            if beam == 'beam 1': 
                df = self.mcbh_b1
            elif beam == 'beam 2': 
                df = self.mcbh_b2
        if plane == 'vertical':
            if beam == 'beam 1': 
                df = self.mcbv_b1
            elif beam == 'beam 2': 
                df = self.mcbv_b2

        # Create a slice of the df corresponding to the selected region
        df_slice = df[df['sort_key'].str.contains(region)].copy()
        # Sort the knobs
        df_slice.loc[:, 'sort_number'] = df_slice['sort_key'].str.extract(r'(\d+)').astype(int)
        sorted_df = df_slice.sort_values(by='sort_number').drop('sort_number', axis=1)

        # Return as a list 
        return sorted_df['name'].to_list()

    def match_local_bump(self, 
                       element: str, 
                       relevant_mcbs: list,
                       size: float, 
                       beam: str,
                       plane: str,
                       tw0 = None):

        """
        Adds a 3C or 4C local bump to line using optimisation line.match
        """
        # If bump size was given as a numpy array, get the first value - for fitting
        if isinstance(size, np.ndarray): size = size[0]

        element = element.lower()

        if beam == 'beam 1': 
            line, tw = self.line_b1, self.tw_b1.copy().reset_index()
            if plane == 'horizontal': df = self.acbh_knobs_b1
            elif plane == 'vertical': df = self.acbv_knobs_b1
        elif beam == 'beam 2': 
            line, tw = self.line_b2, self.tw_b2.copy().reset_index()
            if plane == 'horizontal': df = self.acbh_knobs_b2
            elif plane == 'vertical': df = self.acbv_knobs_b2
        
        try:
            mcb_count = len(relevant_mcbs)
            filtered_df = tw[tw['name'].isin(relevant_mcbs)]

            # Get the rows of first and last corrector
            min_s_row = filtered_df.loc[filtered_df['s'].idxmin()]  # Row with smallest 's' value
            max_s_row = filtered_df.loc[filtered_df['s'].idxmax()]  # Row with largest 's' value

            # Get the indices of these rows
            min_s_index = min_s_row.name
            max_s_index = max_s_row.name

            # Get the indices of elements downstream and upstream of the bump
            previous_index = min_s_index - 1
            next_index = max_s_index + 1

            # Retrieve the names at these indices
            if beam == 'beam 1':
                start_element = tw.at[previous_index, 'name']
                end_element = tw.at[next_index, 'name']
            elif beam == 'beam 2':
                start_element = tw.at[next_index, 'name']
                end_element = tw.at[previous_index, 'name']

        except: 
            self.print_to_label('Something is wrong with the correctors')
            return False
                
        self.print_to_label(f'Applying a {mcb_count}C-bump...')
        if tw0 is None:
            tw0 = line.twiss()

        if plane == 'vertical':
            target1 = xt.TargetSet(['y','py'], value=tw0, at=xt.END)
            target2 = xt.Target('y', size/1000, at=element)
            # Get knobs that control relevant mcb elements
            vars_list = [str(line.element_refs[i].ksl[0]._expr) for i in relevant_mcbs]
            varylist = [re.search(r"vars\['(.*?)'\]", expr).group(1) for expr in vars_list]
        elif plane == 'horizontal':
            target1 = xt.TargetSet(['x','px'], value=tw0, at=xt.END)
            target2 = xt.Target('x', size/1000, at=element)
            # Get knobs that control relevant mcb elements
            vars_list = [str(line.element_refs[i].knl[0]._expr) for i in relevant_mcbs]
            varylist = [re.search(r"vars\['(.*?)'\]", expr).group(1) for expr in vars_list]

        try:
            self.opt = line.match(
                default_tol={None: 5e-8},
                solver_options=dict(max_rel_penalty_increase=2.),
                init=tw0,
                start=(start_element),
                end=(end_element),
                vary=xt.VaryList(varylist),
                targets=[target1, target2])
                
            self.twiss()
            knob_values = self.opt.get_knob_values()

            for knob, new_value in knob_values.items():
                df.loc[df['knob'] == knob, 'current value'] = new_value
            
            return True

        except Exception as e: 
            self.print_to_label(e)
            return False
        
    def get_ir_boundries(self, ir):
        """
        Mathod to get the boundries of IRs, returns a position range in metres
        """
        try:
            number = ir[-1] #last element in the string is the number of the ir

            # Construct element names corresponding to start and end of an ir
            start = 's.ds.l'+number+'.b1'
            end = 'e.ds.r'+number+'.b1'

            # Define the range by searching the elements in twiss data
            s_range = (self.tw_b1[self.tw_b1['name']==start]['s'].values[0], self.tw_b1[self.tw_b1['name']==end]['s'].values[0])

            return s_range
        
        # If something is wrong return the full line length
        except:
            return (0, self.length)
            