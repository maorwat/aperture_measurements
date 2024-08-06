import sys
sys.path.append('/eos/home-i03/m/morwat/.local/lib/python3.9/site-packages/')

import pandas as pd
import yaml
import tfs

from typing import Any, Dict, Optional

import pytimber
from datetime import timedelta


class BPMData:

    def __init__(self, spark, time):

        # initialise the logging
        self.ldb = pytimber.LoggingDB(spark_session=spark)
        self.load_data(time)

    def load_data(self, time):
        
        if isinstance(time, list):
            # If time was selected using utils.select_time()
            t = time[0]
        else:
            t = time

        # Fetch BPM positions and names in one go
        end_time = t + timedelta(seconds=1)
        BPM_data = {
            'BPM_pos_H': self.ldb.get('BFC.LHC:OrbitAcq:positionsH', t, end_time),
            'BPM_pos_V': self.ldb.get('BFC.LHC:OrbitAcq:positionsV', t, end_time),
            'BPM_names': self.ldb.get('BFC.LHC:Mappings:fBPMNames_h', t, t + timedelta(minutes=1))
        }

        # Extract BPM names and readings
        BPM_names_np = BPM_data['BPM_names']['BFC.LHC:Mappings:fBPMNames_h'][1][0]
        BPM_readings_H = BPM_data['BPM_pos_H']['BFC.LHC:OrbitAcq:positionsH'][1]
        BPM_readings_V = BPM_data['BPM_pos_V']['BFC.LHC:OrbitAcq:positionsV'][1]

        # Create DataFrame with readings
        df = pd.DataFrame({
            'X': BPM_readings_H[0],  # Access first (and only) reading by index 0
            'Y': BPM_readings_V[0],  # Access first reading by index 0
            'NAME': BPM_names_np
        })

        # Process data for both beams
        df1 = tfs.read('/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B1.tfs')
        df1 = df1[df1.KEYWORD.str.contains('MONITOR')]
        self.b1_positions = pd.merge(df, df1[['NAME', 'S']], on='NAME')

        df2 = tfs.read('/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B4.tfs')
        df2 = df2[df2.KEYWORD.str.contains('MONITOR')]
        self.b2_positions = pd.merge(df, df2[['NAME', 'S']], on='NAME')


class CollimatorsData:

    def __init__(self, spark, time):

        # initialise the logging
        self.ldb = pytimber.LoggingDB(spark_session=spark)
        self.load_data(time)

    def load_data(self, time):
        
        if isinstance(time, list):
            # If time was selected using utils.select_time()
            t = time[0]
        else:
            t = time

        # Load the file
        collimators_path = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/colldbs/injection.yaml'
                
        with open(collimators_path, 'r') as file:
            f = yaml.safe_load(file)

        col_b1 = pd.DataFrame(f['collimators']['b1']).loc[['angle']].T
        col_b1 = col_b1.reset_index().rename(columns={'index': 'name'})
        col_b1['name'] = col_b1['name'].str.upper()

        col_b2 = pd.DataFrame(f['collimators']['b2']).loc[['angle']].T
        col_b2 = col_b2.reset_index().rename(columns={'index': 'name'})
        col_b2['name'] = col_b2['name'].str.upper()

        col_df1 = tfs.read('/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B1.tfs')
        col_df1 = pd.merge(col_b1, col_df1, left_on='name', right_on='NAME')[['NAME', 'angle', 'S', 'L']]
        col_df1.columns = col_df1.columns.str.lower()

        col_df2 = tfs.read('/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B4.tfs')
        col_df2 = pd.merge(col_b2, col_df2, left_on='name', right_on='NAME')[['NAME', 'angle', 'S', 'L']]
        col_df2.columns = col_df2.columns.str.lower()

        # Step 1: Add an empty column to the DataFrame
        col_df1['gap'] = None 

        # Step 2: Iterate over all rows and modify the new column's values
        for index, row in col_df1.iterrows():
            
            name = str(row['name']+':MEAS_LVDT_GD')
            
            col_gap = self.ldb.get(name, t, t+timedelta(seconds=1))
            
            try: col_df1.at[index, 'gap'] = col_gap[name][1][0]
            except: continue

        col_df2['gap'] = None 

        # Step 2: Iterate over all rows and modify the new column's values
        for index, row in col_df2.iterrows():
            
            name = str(row['name']+':MEAS_LVDT_GD')
            
            col_gap = self.ldb.get(name, t, t+timedelta(seconds=1))
            
            try: col_df2.at[index, 'gap'] = col_gap[name][1][0]
            except: continue

        self.b1_data = col_df1.copy()
        self.b2_data = col_df2.copy()
        
    def process(self, twiss):
        
        colx_b1 = self.b1_data[self.b1_data['angle']==0]
        colx_b2 = self.b2_data[self.b2_data['angle']==0]
        coly_b1 = self.b1_data[self.b1_data['angle']==90]
        coly_b2 = self.b2_data[self.b2_data['angle']==90]
        
        self.colx_b1 = self.add_collimator_positions(twiss, colx_b1, 'x')
        self.colx_b2 = self.add_collimator_positions(twiss, colx_b2, 'x')
        self.coly_b1 = self.add_collimator_positions(twiss, coly_b1, 'x')
        self.coly_b2 = self.add_collimator_positions(twiss, coly_b2, 'x')
               
    def add_collimator_positions(self, twiss, col, x_key):
        
        # Merge with twiss data to find collimator positions
        col = pd.merge(col, twiss, on='name', how='left')

        # Calculate gap in meters and add to the dataFrame
        col.loc[:, 'top_gap_col'] = col['gap'] + col[x_key]
        col.loc[:, 'bottom_gap_col'] = -col['gap'] + col[x_key]
        
        return col