import pandas as pd
import numpy as np
import yaml
import tfs

from typing import Any, Dict, Optional

import pytimber
from datetime import timedelta

from aper_package.utils import shift_by

class BPMData:

    def __init__(self, 
                 spark):

        # initialise the logging
        self.ldb = pytimber.LoggingDB(spark_session=spark)

    def load_data(self, t):
        
        # If time was selected using utils.select_time()
        if isinstance(t, list): t = t[0]

        print("Loading BPM data...")

        # Fetch BPM positions and names
        end_time = t + timedelta(seconds=1)
        BPM_data = {
            'BPM_pos_H': self.ldb.get('BFC.LHC:OrbitAcq:positionsH', t, end_time),
            'BPM_pos_V': self.ldb.get('BFC.LHC:OrbitAcq:positionsV', t, end_time),
            'BPM_names': self.ldb.get('BFC.LHC:Mappings:fBPMNames_h', t, t + timedelta(minutes=1))
        }

        # Extract BPM names and readings
        BPM_readings_H = BPM_data['BPM_pos_H']['BFC.LHC:OrbitAcq:positionsH'][1]
        BPM_readings_V = BPM_data['BPM_pos_V']['BFC.LHC:OrbitAcq:positionsV'][1]
        # Make sure the names are lowercase to merge later with twiss data
        BPM_names = np.char.lower(BPM_data['BPM_names']['BFC.LHC:Mappings:fBPMNames_h'][1][0].astype(str))

        # Create DataFrame with readings
        self.data = pd.DataFrame({
            'x': BPM_readings_H[0],  # Access first (and only) reading by index 0
            'y': BPM_readings_V[0],  # Access first reading by index 0
            'name': BPM_names
        })

        print("Done loading BPM data.")

    def process(self, twiss):

        # Find BPM positions using twiss data
        self.b1 = pd.merge(self.data, twiss.tw_b1[['name', 's']], on='name')
        self.b2 = pd.merge(self.data, twiss.tw_b2[['name', 's']], on='name')

class CollimatorsData:

    def __init__(self, 
                 spark,
                 yaml_path='/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/colldbs/injection.yaml'):

        # initialise the logging
        self.ldb = pytimber.LoggingDB(spark_session=spark)
        self.yaml_path = yaml_path

    def load_data(self, t):
        
        # If time was selected using utils.select_time()
        if isinstance(t, list): t = t[0]
        # or file selected using select_file_in_SWAN()
        if isinstance(self.yaml_path, list): self.yaml_path = self.yaml_path[0]

        # Load the file  
        with open(self.yaml_path, 'r') as file:
            f = yaml.safe_load(file)

        # Create a data frame for beam 1
        col_b1 = pd.DataFrame(f['collimators']['b1']).loc[['angle']].T
        col_b1 = col_b1.reset_index().rename(columns={'index': 'name'})

        # Create a data frame for beam 2
        col_b2 = pd.DataFrame(f['collimators']['b2']).loc[['angle']].T
        col_b2 = col_b2.reset_index().rename(columns={'index': 'name'})

        # Get a list of collimator names to load from timber
        names_b1 = col_b1['name'].str.upper().to_list()
        names_b2 = col_b2['name'].str.upper().to_list()

        for i, name in enumerate(names_b1): names_b1[i]=name+':MEAS_LVDT_GD'
        for i, name in enumerate(names_b2): names_b2[i]=name+':MEAS_LVDT_GD'

        print("Loading collimators data...")

        col_b1_from_timber = self.ldb.get(names_b1, t, t+timedelta(seconds=1))
        col_b2_from_timber = self.ldb.get(names_b2, t, t+timedelta(seconds=1))

        # Iterate over all rows and add the gap column's values
        for index, row in col_b1.iterrows():
            try:
                name_to_search = row['name'].upper()+':MEAS_LVDT_GD'
                # Make sure the gaps are in units of metres to match everythong else
                col_b1.at[index, 'gap'] = col_b1_from_timber[name_to_search][1][0]/1e3
            except: continue

        # Iterate over all rows and add the gap column's values
        for index, row in col_b2.iterrows():
            try:
                name_to_search = row['name'].upper()+':MEAS_LVDT_GD'
                # Make sure the gaps are in units of metres to match everythong else
                col_b2.at[index, 'gap'] = col_b2_from_timber[name_to_search][1][0]/1e3
            except: continue

        self.colx_b1 = col_b1[col_b1['angle']==0].dropna()
        self.colx_b2 = col_b2[col_b2['angle']==0].dropna()
        self.coly_b1 = col_b1[col_b1['angle']==90].dropna()
        self.coly_b2 = col_b2[col_b2['angle']==90].dropna()

        print("Done loading collimators data.")
        
    def process(self, twiss):
        
        self.colx_b1 = self._add_collimator_positions(twiss.tw_b1, self.colx_b1, 'x')
        self.colx_b2 = self._add_collimator_positions(twiss.tw_b2, self.colx_b2, 'x')
        self.coly_b1 = self._add_collimator_positions(twiss.tw_b1, self.coly_b1, 'y')
        self.coly_b2 = self._add_collimator_positions(twiss.tw_b2, self.coly_b2, 'y')
               
    def _add_collimator_positions(self, twiss, col, x_key):

        # Ensure 'col' is a copy to avoid SettingWithCopyWarning
        col = col.copy()

        # Change names to lowercase to match twiss
        col.loc[:, 'name'] = col['name'].str.lower()

        # Merge with twiss data to find collimator positions
        col = pd.merge(col[['name', 'gap', 'angle']], twiss[['name', 's', 'x', 'y']], on='name', how='left')

        # Calculate gap in meters and add to the dataFrame
        col.loc[:, 'top_gap_col'] = col['gap'] + col[x_key]
        col.loc[:, 'bottom_gap_col'] = -col['gap'] + col[x_key]
        
        return col