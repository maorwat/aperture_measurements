import pandas as pd
import yaml
import tfs

from typing import Any, Dict, Optional

import pytimber
from datetime import timedelta


class BPMData:

    def __init__(self, 
                 spark,
                 time,
                 path='/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B1.tfs'):

        # initialise the logging
        self.ldb = pytimber.LoggingDB(spark_session=spark)
        self.load_data(time, path)

    def load_data(self, t, path):
        
        # If time was selected using utils.select_time()
        # or file selected using select_file_in_SWAN()
        if isinstance(t, list): t = t[0]
        if isinstance(path, list): path = path[0]

        # Fetch BPM positions and names in one go
        end_time = t + timedelta(seconds=1)
        BPM_data = {
            'BPM_pos_H': self.ldb.get('BFC.LHC:OrbitAcq:positionsH', t, end_time),
            'BPM_pos_V': self.ldb.get('BFC.LHC:OrbitAcq:positionsV', t, end_time),
            'BPM_names': self.ldb.get('BFC.LHC:Mappings:fBPMNames_h', t, t + timedelta(minutes=1))
        }

        # Extract BPM names and readings
        BPM_names = BPM_data['BPM_names']['BFC.LHC:Mappings:fBPMNames_h'][1][0]
        BPM_readings_H = BPM_data['BPM_pos_H']['BFC.LHC:OrbitAcq:positionsH'][1]
        BPM_readings_V = BPM_data['BPM_pos_V']['BFC.LHC:OrbitAcq:positionsV'][1]

        # Create DataFrame with readings
        df = pd.DataFrame({
            'X': BPM_readings_H[0],  # Access first (and only) reading by index 0
            'Y': BPM_readings_V[0],  # Access first reading by index 0
            'NAME': BPM_names
        })

        # Process data for both beams
        df1 = tfs.read(path)
        df1 = df1[df1.KEYWORD.str.contains('MONITOR')]
        self.b1_positions = pd.merge(df, df1[['NAME', 'S']], on='NAME')

        df2 = tfs.read(str(path).replace('B1', 'B4'))
        df2 = df2[df2.KEYWORD.str.contains('MONITOR')]
        self.b2_positions = pd.merge(df, df2[['NAME', 'S']], on='NAME')


class CollimatorsData:

    def __init__(self, 
                 spark, 
                 time, 
                 all_optics_path='/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B1.tfs',
                 yaml_path='/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/colldbs/injection.yaml'):

        # initialise the logging
        self.ldb = pytimber.LoggingDB(spark_session=spark)
        self.load_data(time, all_optics_path, yaml_path)

    def load_data(self, t, all_optics_path, yaml_path):
        
        # If time was selected using utils.select_time()
        # or files selected using select_file_in_SWAN()
        if isinstance(t, list): t = t[0]
        if isinstance(all_optics_path, list): all_optics_path = all_optics_path[0]
        if isinstance(yaml_path, list): yaml_path = yaml_path[0]

        # Load the file  
        with open(yaml_path, 'r') as file:
            f = yaml.safe_load(file)

        # Create a data frame for beam 1
        col_b1 = pd.DataFrame(f['collimators']['b1']).loc[['angle']].T
        col_b1 = col_b1.reset_index().rename(columns={'index': 'name'})
        # Change the names to uppercase to facilitate searching
        col_b1['name'] = col_b1['name'].str.upper()

        # Create a data frame for beam 2
        col_b2 = pd.DataFrame(f['collimators']['b2']).loc[['angle']].T
        col_b2 = col_b2.reset_index().rename(columns={'index': 'name'})
        # Change the names to uppercase to facilitate searching
        col_b2['name'] = col_b2['name'].str.upper()

        # Load all optics data to find collimator positions
        col_df1 = tfs.read(all_optics_path)

        col_df1 = pd.merge(col_b1, col_df1, left_on='name', right_on='NAME')[['NAME', 'angle', 'S', 'L']]
        # Make sure all the headers are lowercase (necessary for plotting)
        col_df1.columns = col_df1.columns.str.lower()

        # Create a path for beam 2 by replacing B1 with B4
        col_df2 = tfs.read(str(all_optics_path).replace('B1', 'B4'))
        col_df2 = pd.merge(col_b2, col_df2, left_on='name', right_on='NAME')[['NAME', 'angle', 'S', 'L']]
        # Make sure all the headers are lowercase (necessary for plotting)
        col_df2.columns = col_df2.columns.str.lower()

        names_b1 = col_df1['name'].to_list()
        for i, name in enumerate(names_b1): names_b1[i]=name+':MEAS_LVDT_GD'

        names_b2 = col_df2['name'].to_list()
        for i, name in enumerate(names_b2): names_b2[i]=name+':MEAS_LVDT_GD'

        col_df1_from_timber = self.ldb.get(names_b1, t, t+timedelta(seconds=1))
        col_df2_from_timber = self.ldb.get(names_b2, t, t+timedelta(seconds=1))

        # Iterate over all rows and modify the new column's values
        for index, row in col_df1.iterrows():
            try:
                name_to_search = str(row['name']+':MEAS_LVDT_GD')
                col_df1.at[index, 'gap'] = col_df1_from_timber[name_to_search][1][0]/1e3
            except: continue

        # Iterate over all rows and modify the new column's values
        for index, row in col_df2.iterrows():
            try:
                name_to_search = str(row['name']+':MEAS_LVDT_GD')
                col_df2.at[index, 'gap'] = col_df2_from_timber[name_to_search][1][0]/1e3
            except: continue

        self.b1_data = col_df1.dropna().copy()
        self.b2_data = col_df2.dropna().copy()
        
    def process(self, twiss):
        
        colx_b1 = self.b1_data[self.b1_data['angle']==0]
        colx_b2 = self.b2_data[self.b2_data['angle']==0]
        coly_b1 = self.b1_data[self.b1_data['angle']==90]
        coly_b2 = self.b2_data[self.b2_data['angle']==90]
        
        self.colx_b1 = self.add_collimator_positions(twiss.tw_b1, colx_b1, 'x')
        self.colx_b2 = self.add_collimator_positions(twiss.tw_b2, colx_b2, 'x')
        self.coly_b1 = self.add_collimator_positions(twiss.tw_b1, coly_b1, 'x')
        self.coly_b2 = self.add_collimator_positions(twiss.tw_b2, coly_b2, 'x')
               
    def add_collimator_positions(self, twiss, col, x_key):

        # Ensure 'col' is a copy to avoid SettingWithCopyWarning
        col = col.copy()

        # Change names to lowercase to match twiss
        col.loc[:, 'name'] = col['name'].str.lower()

        # Merge with twiss data to find collimator positions
        col = pd.merge(col, twiss[['name', 'x', 'y']], on='name', how='left')

        # Calculate gap in meters and add to the dataFrame
        col.loc[:, 'top_gap_col'] = col['gap'] + col[x_key]
        col.loc[:, 'bottom_gap_col'] = -col['gap'] + col[x_key]
        
        return col