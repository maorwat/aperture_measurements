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

from aper_package.utils import match_indices
from aper_package.utils import shift_and_redefine

class AperPlot:
    
    #TODO define all the arguments as optional or not
    def __init__(self,
                 ip = 'ip5',
                 n = 0,
                 emitt = 3.5e-6,
                 gamma = 7247.364689,
                 path1 = "/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX/levelling.20/all_optics_B1.tfs", 
                 path2 = "/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX/levelling.20/all_optics_B4.tfs",
                 line1 = '/home/morwat/cernbox/aperture_measurements/madx/2023/xsuite/Martas_levelling.20_b1.json',
                 line2 = '/home/morwat/cernbox/aperture_measurements/madx/2023/xsuite/Martas_levelling.20_b2.json',
                 machine_components_path = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B1.tfs',
                 collimators_path = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/colldbs/levelling.20.yaml'):
        
        self.emitt = emitt
        self.gamma = gamma
        self.n = n
        self.ip = ip

        self.machine_components_path = machine_components_path
        self.collimators_path = collimators_path   

        df_b1 = tfs.read(path1)[['S', 'NAME', 'APER_1', 'APER_2']]
        df_b1.drop_duplicates(subset=['S'])
        df_b2 = tfs.read(path2)[['S', 'NAME', 'APER_1', 'APER_2']]
        df_b2.drop_duplicates(subset=['S'])

        # Filtering the DataFrame to only have the IP locations
        self.ip_df_b1 = df_b1[df_b1['NAME'].isin(['IP1', 'IP2', 'IP4', 'IP5', 'IP6', 'IP8'])]
        self.ip_df_b1.loc[:, 'NAME'] = self.ip_df_b1['NAME'].str.lower()
        self.ip_df_b2 = df_b2[df_b2['NAME'].isin(['IP1', 'IP2', 'IP4', 'IP5', 'IP6', 'IP8'])]
        self.ip_df_b2.loc[:, 'NAME'] = self.ip_df_b2['NAME'].str.lower()   
        
        #get rid of undefined and unnecessary values
        self.aper_b1 = df_b1[(df_b1['APER_1'] < 1) & (df_b1['APER_1'] != 0) & (df_b1['APER_2'] < 1) & (df_b1['APER_2'] != 0)]
        self.aper_b2 = df_b2[(df_b2['APER_1'] < 1) & (df_b2['APER_1'] != 0) & (df_b2['APER_2'] < 1) & (df_b2['APER_2'] != 0)]

        # Load a line and build tracker
        self.line_b1 = xt.Line.from_json(line1)
        self.line_b2 = xt.Line.from_json(line2)

        self.twiss()
        self._define_nominal_crossing()

    def twiss(self):

        # Shift the aperture
        if self.ip == 'ip1':
            self.aper_b1 = shift_and_redefine(self.aper_b1, self.ip_df_b1.loc[self.ip_df_b1['NAME'] == 'ip5', 'S'].iloc[0])
            self.aper_b2 = shift_and_redefine(self.aper_b2, self.ip_df_b2.loc[self.ip_df_b2['NAME'] == 'ip5', 'S'].iloc[0])

            # Set IP1 as the middle
            self.line_b1.cycle('ip5')
            self.line_b2.cycle('ip5')

        # Generate twiss
        print('Computing twiss for beam 1...')
        tw_b1 = self.line_b1.twiss(skip_global_quantities=True).to_pandas()
        print('Computing twiss for beam 2...')
        tw_b2 = self.line_b2.twiss(skip_global_quantities=True).to_pandas()
        print('Done computing twiss.')

        # Remove the aperture
        tw_b1 = tw_b1[~tw_b1.name.str.contains('aper')]
        tw_b2 = tw_b2[~tw_b2.name.str.contains('aper')]

        print('Almost there...')
        tw_b2['y'] = -tw_b2['y']

        # Drop the unnecessary columns
        self.tw_b1 = tw_b1[['s', 'name', 'x', 'y', 'betx', 'bety']]
        self.tw_b2 = tw_b2[['s', 'name', 'x', 'y', 'betx', 'bety']]

        # Define attributes
        self._define_sigma()
        self.envelope(self.n)


    def _define_nominal_crossing(self):

        # Define the nominal crossing for given configuration
        self.nom_x_b1 = self.tw_b1['x']
        self.nom_y_b1 = self.tw_b1['y']
        
        self.nom_x_b2 = self.tw_b2['x']
        self.nom_y_b2 = self.tw_b2['y']

        self.nom_s_b1 = self.tw_b1['s']
        self.nom_s_b2 = self.tw_b2['s']

    def _define_sigma(self):

        self.tw_b1.loc[:, 'sigma_x'] = np.sqrt(self.tw_b1['betx'] * self.emitt / self.gamma)
        self.tw_b1.loc[:, 'sigma_y'] = np.sqrt(self.tw_b1['bety'] * self.emitt / self.gamma)

        self.tw_b2.loc[:, 'sigma_x'] = np.sqrt(self.tw_b2['betx'] * self.emitt / self.gamma)
        self.tw_b2.loc[:, 'sigma_y'] = np.sqrt(self.tw_b2['bety'] * self.emitt / self.gamma) 

    def envelope(self, n):

        self.n = n
        
        #recalculate the envelope edges for the new envelope size
        self.tw_b1.loc[:, 'x_up'] = self.tw_b1['x'] + n * self.tw_b1['sigma_x']
        self.tw_b1.loc[:, 'x_down'] = self.tw_b1['x'] - n * self.tw_b1['sigma_x']
        self.tw_b1.loc[:, 'y_up'] = self.tw_b1['y'] + n * self.tw_b1['sigma_y']
        self.tw_b1.loc[:, 'y_down'] = self.tw_b1['y'] - n * self.tw_b1['sigma_y']

        self.tw_b2.loc[:, 'x_up'] = self.tw_b2['x'] + n * self.tw_b2['sigma_x']
        self.tw_b2.loc[:, 'x_down'] = self.tw_b2['x'] - n * self.tw_b2['sigma_x']
        self.tw_b2.loc[:, 'y_up'] = self.tw_b2['y'] + n * self.tw_b2['sigma_y']
        self.tw_b2.loc[:, 'y_down'] = self.tw_b2['y'] - n * self.tw_b2['sigma_y']

    def _add_collimators(self, fig, plane, row, column):

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

        def get_df(name, yaml_df, twiss_data, sigma_key):

            col = yaml_df[name]
            gap = np.array([np.nan if x is None else x for x in col.loc['gap']])
            indx = np.where(np.isin(twiss_data["name"], name))[0]
            s_col = twiss_data["s"].to_numpy()[indx]
            sigma = twiss_data[sigma_key].to_numpy()[indx]
            gap_col = sigma * gap

            data = {'NAME': name,
                    'GAP': gap_col,
                    'S': s_col}
            
            df = pd.DataFrame(data)

            if self.ip == 'ip1':
                df = shift_and_redefine(df, self.ip_df_b1.loc[self.ip_df_b1['NAME'] == 'ip5', 'S'].iloc[0])

            return df
        
        # Create the DataFrames
        dfx_b1 = get_df(xname_b1, col_b1, self.tw_b1, 'sigma_x')
        dfy_b1 = get_df(yname_b1, col_b1, self.tw_b1, 'sigma_y')
        dfx_b2 = get_df(xname_b2, col_b2, self.tw_b2, 'sigma_x')
        dfy_b2 = get_df(yname_b2, col_b2, self.tw_b2, 'sigma_y')
  
        if plane == 'h':
            # Add x collimators
            for i in range(dfx_b1.shape[0]):
                x0, y0, x1, y1 = dfx_b1.S.iloc[i] - 0.5, dfx_b1.GAP.iloc[i], dfx_b1.S.iloc[i] + 0.5, 0.05
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=dfx_b1.NAME.iloc[i]), row=2, col=1)
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[-y0, -y1, -y1, -y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=dfx_b1.NAME.iloc[i]), row=2, col=1)
                
            for i in range(dfx_b2.shape[0]):
                x0, y0, x1, y1 = dfx_b2.S.iloc[i] - 0.5, dfx_b2.GAP.iloc[i], dfx_b2.S.iloc[i] + 0.5, 0.05
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=dfx_b2.NAME.iloc[i]), row=2, col=1)
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[-y0, -y1, -y1, -y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=dfx_b2.NAME.iloc[i]), row=2, col=1)

        if plane == 'v':
            # Add y collimators
            for i in range(dfy_b1.shape[0]):
                x0, y0, x1, y1 = dfy_b1.S.iloc[i] - 0.5, dfy_b1.GAP.iloc[i], dfy_b1.S.iloc[i] + 0.5, 0.05
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=dfy_b1.NAME.iloc[i]), row=2, col=1)
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[-y0, -y1, -y1, -y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=dfy_b1.NAME.iloc[i]), row=2, col=1)
                
            for i in range(dfy_b2.shape[0]):
                x0, y0, x1, y1 = dfy_b2.S.iloc[i] - 0.5, dfy_b2.GAP.iloc[i], dfy_b2.S.iloc[i] + 0.5, 0.05
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=dfy_b2.NAME.iloc[i]), row=2, col=1)
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[-y0, -y1, -y1, -y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=dfy_b2.NAME.iloc[i]), row=2, col=1)

    def _add_machine_components(self, fig, row, column):
        
        df = tfs.read(self.machine_components_path)

        if self.ip == 'ip1': df = shift_and_redefine(df, df.loc[df['NAME'] == 'IP5', 'S'].iloc[0])

        objects = ["SBEND", "COLLIMATOR", "SEXTUPOLE", "RBEND", "QUADRUPOLE"]
        colors = ['lightblue', 'black', 'hotpink', 'green', 'red']

        for n, obj in enumerate(objects):
            
            obj_df = df[df['KEYWORD'] == obj]
            
            for i in range(obj_df.shape[0]):

                x0, x1 = obj_df.iloc[i]['S']-obj_df.iloc[i]['L']/2, obj_df.iloc[i]['S']+obj_df.iloc[i]['L']/2                
                if obj=='QUADRUPOLE': y0, y1 = 0, np.sign(obj_df.iloc[i]['K1L']).astype(int)                    
                else: y0, y1 = -0.5, 0.5

                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor=colors[n], line=dict(color=colors[n]), name=obj_df.iloc[i]['NAME']), row=row, col=column) 

    def min_distance_to_aperture(self):

        # Merge twiss and aperture data
        merged_b1 = pd.merge_asof(self.tw_b1[~self.tw_b1.name.str.contains('drift')], self.aper_b1, left_on='s', right_on='S', direction='nearest', tolerance=0.00001)
        merged_b2 = pd.merge_asof(self.tw_b2[~self.tw_b2.name.str.contains('drift')], self.aper_b2, left_on='s', right_on='S', direction='nearest', tolerance=0.00001)

        # Drop all the rows with NaNs
        merged_b1 = merged_b1.dropna()
        merged_b2 = merged_b2.dropna()

        # Drop repeat columns
        merged_b1 = merged_b1.drop(columns=['S', 'NAME'])
        merged_b2 = merged_b2.drop(columns=['S', 'NAME'])

        # Need to add from nominal to top envelope
        # from nominal to bottom envelope for both beams
        # then distance from the top envelope to the top aperture 
        # and from the bottom envelope to the bottom aperture
        # find the minimum
        # check for any negative values, if so find what elements where touched
        # maybe add a marker on the graph to show where the aperture was touched

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

    def sperctrometer(self, ip, value):

        if ip == 'ip2':
            self.line_b1.vars['on_alice'] = value
            self.line_b2.vars['on_alice'] = value
        elif ip == 'ip8':
            self.line_b1.vars['on_lhcb'] = value
            self.line_b2.vars['on_lhcb'] = value

    def show(self, 
             plane,
             beam = 1,
             show_both_beams = True,
             show_collimators = True):
        
        # Create figure
        fig = make_subplots(rows=2, cols=1, row_heights=[0.2, 0.8], shared_xaxes=True)
        
        if plane == 'h':
            
            top_aper_b1 = go.Scatter(x=self.aper_b1.S, y=self.aper_b1.APER_1, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b1 = go.Scatter(x=self.aper_b1.S, y=-self.aper_b1.APER_1, mode='lines', line=dict(color='gray'), name='Aperture')     
            top_aper_b2 = go.Scatter(x=self.aper_b2.S, y=self.aper_b2.APER_1, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b2 = go.Scatter(x=self.aper_b2.S, y=-self.aper_b2.APER_1, mode='lines', line=dict(color='gray'), name='Aperture') 

            b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.x, mode='lines', line=dict(color='blue'), name='Beam 1')
            b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.x, mode='lines', line=dict(color='red'), name='Beam 2')
            nom_b1 = go.Scatter(x=self.nom_s_b1, y=self.nom_x_b1, mode='lines', line=dict(color='blue', dash='dash'), name='Beam 1')
            nom_b2 = go.Scatter(x=self.nom_s_b2, y=self.nom_x_b2, mode='lines', line=dict(color='red', dash='dash'), name='Beam 2')
            
            up_b1 = self.tw_b1.x_up
            down_b1 = self.tw_b1.x_down
            up_b2 = self.tw_b2.x_up
            down_b2 = self.tw_b2.x_down
            
            fig.update_yaxes(range=[-0.05, 0.05], title_text="x [m]", row=2, col=1)
            
        elif plane == 'v':
            
            top_aper_b1 = go.Scatter(x=self.aper_b1.S, y=self.aper_b1.APER_2, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b1 = go.Scatter(x=self.aper_b1.S, y=-self.aper_b1.APER_2, mode='lines', line=dict(color='gray'), name='Aperture')
            top_aper_b2 = go.Scatter(x=self.aper_b2.S, y=self.aper_b2.APER_2, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b2 = go.Scatter(x=self.aper_b2.S, y=-self.aper_b2.APER_2, mode='lines', line=dict(color='gray'), name='Aperture') 
            
            b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.y, mode='lines', line=dict(color='blue'), name='Beam 1')
            b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.y, mode='lines', line=dict(color='red'),name='Beam 2')
            nom_b1 = go.Scatter(x=self.nom_s_b1, y=self.nom_y_b1, mode='lines', line=dict(color='blue', dash='dash'), name='Beam 1')
            nom_b2 = go.Scatter(x=self.nom_s_b2, y=self.nom_y_b2, mode='lines', line=dict(color='red', dash='dash'), name='Beam 2')
            
            up_b1 = self.tw_b1.y_up
            down_b1 = self.tw_b1.y_down
            up_b2 = self.tw_b2.y_up
            down_b2 = self.tw_b2.y_down

            fig.update_yaxes(range=[-0.05, 0.05], title_text="y [m]", row=2, col=1)

        else: print('Incorrect plane')

        upper_b1 = go.Scatter(x=self.tw_b1.s, y=up_b1, mode='lines', name='Upper envelope beam 1', fill=None, line=dict(color='rgba(0,0,255,0)'))
        lower_b1 = go.Scatter(x=self.tw_b1.s, y=down_b1, mode='lines', name='Lower envelope beam 1', line=dict(color='rgba(0,0,255,0)'), 
                          fill='tonexty', fillcolor='rgba(0,0,255,0.1)')

        upper_b2 = go.Scatter(x=self.tw_b2.s, y=up_b2, mode='lines', name='Upper envelope beam 2', fill=None, line=dict(color='rgba(255,0,0,0)'))
        lower_b2 = go.Scatter(x=self.tw_b2.s, y=down_b2, mode='lines', name='Lower envelope beam 2', line=dict(color='rgba(255,0,0,0)'), 
                           fill='tonexty', fillcolor='rgba(255,0,0,0.1)')

        traces_b1 = [b1, nom_b1, upper_b1, lower_b1]
        traces_b2 = [b2, nom_b2, upper_b2, lower_b2]
        
        if beam == 1:
            for i in traces_b1:
                fig.add_trace(i, row=2, col=1) 

            fig.add_trace(top_aper_b1, row=2, col=1)
            fig.add_trace(bottom_aper_b1, row=2, col=1)

            if show_both_beams:
                for i in traces_b2:
                    fig.add_trace(i, row=2, col=1)     
        
        if beam == 2:
            for i in traces_b2:
                fig.add_trace(i, row=2, col=1) 

            fig.add_trace(top_aper_b2, row=2, col=1)
            fig.add_trace(bottom_aper_b2, row=2, col=1)

            if show_both_beams:
                for i in traces_b1:
                    fig.add_trace(i, row=2, col=1) 

        self._add_machine_components(fig=fig, row=1, column=1)

        if show_collimators:
            self._add_collimators(fig=fig, plane = plane, row=2, column=1)

        # Set layout
        fig.update_layout(height=800, width=800, plot_bgcolor='white', showlegend=False)

        # Change the axes limits and labels
        fig.update_yaxes(range=[-1, 1], row=1, col=1, showticklabels=False, showline=False)

        fig.update_xaxes(title_text="s [m]", row=2, col=1)
        fig.update_xaxes(row=1, col=1, showticklabels=False, showline=False)

        fig.show()
        

                

