import numpy as np
import pandas as pd
import tfs
import yaml
import re

from typing import Any, Dict, Optional
 
import xtrack as xt

from aper_package.utils import *

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class ApertureData:
    
    def __init__(self,
                 path_b1: str,
                 path_b2: Optional[str] = None,
                 n: Optional[float] = 0,
                 emitt: Optional[str] = 3.5e-6):
        
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
        self.length = self.line_b1.get_length()

        # Find knobs
        self._define_knobs()
        self._define_acb_knobs()
        self._define_mcbs()

        # Turn off all multipoles with order > 2 and relax the aperture to enable higher crossing angles
        self.turn_off_multipoles()
        self.relax_aperture()

        # Twiss
        self.twiss()

        # Keep the nominal crossing seperately for calculations
        self._define_nominal_crossing()
        self._distance_to_nominal('horizontal')
        self._distance_to_nominal('vertical')

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
        print_and_clear('Computing twiss for beam 1...')
        tw_b1 = self.line_b1.twiss(skip_global_quantities=True).to_pandas()
        print_and_clear('Computing twiss for beam 2...')
        tw_b2 = self.line_b2.twiss(skip_global_quantities=True, reverse=True).to_pandas()
        print_and_clear('Done computing twiss.')

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
        return twiss_df[['s', 'name', 'x', 'y', 'betx', 'bety', 'px', 'py']]

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

        self.tw_b1.loc[:, from_nom_to_top] = (self.tw_b1[up] - self.nom_b1[nom])*1000
        self.tw_b1.loc[:, from_nom_to_bottom] = abs(self.tw_b1[down] - self.nom_b1[nom])*1000

        self.tw_b2.loc[:, from_nom_to_top] = (self.tw_b2[up] - self.nom_b2[nom])*1000
        self.tw_b2.loc[:, from_nom_to_bottom] = abs(self.tw_b2[down] - self.nom_b2[nom])*1000

    def _define_sigma(self) -> None:
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
            print_and_clear(f"Element '{first_element}' not found in the DataFrame.")
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
        shift = self._get_shift(element)

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
                            print_and_clear(f"Error shifting {attr}: {e}")

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

    def change_acb_knob(self, knob, value, plane, beam) -> None:
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
            if plane == 'horizontal': knobs_df = self.acbh_knobs_b1
            elif plane == 'vertical': knobs_df = self.acbv_knobs_b1
        elif beam == 'beam 2':
            line = self.line_b2
            if plane == 'horizontal': knobs_df = self.acbh_knobs_b2
            elif plane == 'vertical': knobs_df = self.acbv_knobs_b2

        # Set the new value
        line.vars[knob] = value

        # Update the current value with the new value
        knobs_df.loc[knobs_df['knob'] == knob, 'current value'] = value

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
        df1 = tfs.read(path_b1)[['S', 'NAME', 'APER_1', 'APER_2']]
        df2 = tfs.read(path_b2)[['S', 'NAME', 'APER_1', 'APER_2']]
        # Get rid of undefined values
        df1 = df1[(df1['APER_1'] < 0.2) & (df1['APER_1'] != 0) & (df1['APER_2'] < 0.2) & (df1['APER_2'] != 0)]
        df2 = df2[(df2['APER_1'] < 0.2) & (df2['APER_1'] != 0) & (df2['APER_2'] < 0.2) & (df2['APER_2'] != 0)]
        # Make sure the aperture aligns with twiss data (if cycling was performed)
        df1 = match_with_twiss(self.tw_b1, df1)
        df2 = match_with_twiss(self.tw_b2, df2)

        return df1.drop_duplicates(subset=['S']), df2.drop_duplicates(subset=['S'])
    
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

        return df
    
    def load_elements(self, path: str) -> None:
        """
        Loads machine component data from a TFS file and matches it with the twiss data.

        Parameters:
            path : The path to the machine components TFS file. If None, a default path is used.

        """
        # Load the file
        df = tfs.read(path)

        # Make sure the elements align with twiss data (if cycling was performed)
        self.elements = match_with_twiss(self.tw_b1, df)

    def _define_mcbs(self):
        """
        Creates lists of mcb orbit correctors for each beam for given plane
        """

        self.mcbh_b1 = [element for element in list(self.line_b1.element_names) 
                if re.search('mcb.*h.*b1$',element)]
        self.mcbh_b2 = [element for element in list(self.line_b2.element_names)
                if re.search('mcb.*h.*b2$',element)]
        
        self.mcbv_b1 = [element for element in list(self.line_b1.element_names) 
                if re.search('mcb.*v.*b1$',element)]
        self.mcbv_b2 = [element for element in list(self.line_b2.element_names)
                if re.search('mcb.*v.*b2$',element)]

    def add_local_bump(self, 
                       element: str, 
                       start_mcb: str, 
                       end_mcb: str,
                       size: float, 
                       beam: str,
                       plane: str):

        """
        Adds a 3C or 4C local bump to line using optimisation line.match
        """
        #TODO: DOESNT WORK
        if beam == 'beam 1': line = self.line_b1
        elif beam == 'beam 2': line = self.line_b2

        # Find the indices of the start and end elements
        start_index = line.element_names.index(start_mcb)
        end_index = line.element_names.index(end_mcb)

        if plane == 'horizontal': key = 'mcb.*h.*b[12]$'#'mcbh'
        elif plane == 'vertical': key = 'mcb.*v.*b[12]$'#'mcbv'
        
        # In case the elements were selected in the wrong order
        elements_between = list(line.element_names[start_index:end_index + 1])
        if len(elements_between) == 0: elements_between = list(line.element_names[end_index:start_index + 1])
        
        relevant_mcbs = [element for element in list(elements_between) if re.search(key,element)]
        print(relevant_mcbs)
        mcb_count = len(relevant_mcbs)
        print(mcb_count)
        
        if mcb_count == 3 or mcb_count == 4:

            print_and_clear(f'Applying a {mcb_count}C-bump...')
            tw0 = line.twiss()

            if plane == 'vertical':
                target1 = xt.TargetSet(['y','py'], value=tw0, at=relevant_mcbs[0])
                target2 = xt.Target(y=size/1000, at=element)
                target3 = xt.TargetSet(['y','py'], value=tw0, at=relevant_mcbs[-1])
                # Get knobs that control relevant mcb elements
                vars_list = [str(line.element_refs[element].ksl[0]._expr) for element in relevant_mcbs]
                varylist = [re.search(r"vars\['(.*?)'\]", expr).group(1) for expr in vars_list]
            elif plane == 'horizontal':
                target1 = xt.TargetSet(['x','px'], value=tw0, at=relevant_mcbs[0])
                target2 = xt.Target(x=size/1000, at=element)
                target3 = xt.TargetSet(['x','px'], value=tw0, at=relevant_mcbs[-1])
                vars_list = [str(line.element_refs[element].knl[0]._expr) for element in relevant_mcbs]
                varylist = [re.search(r"vars\['(.*?)'\]", expr).group(1) for expr in vars_list]
                
            targets = [target1, target2, target3]
            try:
                self.opt = line.match(
                    vary=xt.VaryList(varylist, step=1e-8),
                    targets = targets)
                
                self.twiss()
                print(self.opt.get_knob_values())
            except Exception as e: print(e)
            
        else: print_and_clear('Wrong mcbs, retry')

    def get_ir_boundries(self, ir):
        """
        Mathod to get the boundries of IRs, returns a position range in metres
        """
        number = ir[-1] #last element in the string is the number of the ir

        # Construct element names corresponding to start and end of an ir
        start = 's.ds.l'+number+'.b1'
        end = 'e.ds.r'+number+'.b1'

        # Define the range by searching the elements in twiss data
        s_range = (self.tw_b1[self.tw_b1['name']==start]['s'].values[0], self.tw_b1[self.tw_b1['name']==end]['s'].values[0])

        return s_range