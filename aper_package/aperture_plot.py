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
                 ip,
                 n = 0,
                 emitt = 3.5e-6,
                 gamma = 7247.364689,
                 path1 = "/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX/levelling.20/all_optics_B1.tfs", 
                 path2 = "/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX/levelling.20/all_optics_B4.tfs",
                 line1 = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/xsuite/levelling.20_b1.json',
                 line2 = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/xsuite/levelling.20_b2.json',
                 machine_components_path = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B1.tfs',
                 collimators_path = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/colldbs/levelling.20.yaml'):
        
        self.emitt = emitt
        self.gamma = gamma
        self.n = n

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

        self._twiss(ip)

    def _twiss(self, ip):

        # Shift the aperture
        #if ip == 'ip1':
            #self.aper_b1 = shift_and_redefine(self.aper_b1, self.ip_df_b1.loc[self.ip_df_b1['NAME'] == 'ip5', 'S'].iloc[0])
            #self.aper_b2 = shift_and_redefine(self.aper_b2, self.ip_df_b2.loc[self.ip_df_b2['NAME'] == 'ip5', 'S'].iloc[0])

            # Set IP1 as the middle
            #self.line_b1.cycle('ip5')
            #self.line_b2.cycle('ip5')

        # Generate twiss
        print('Computing twiss for beam 1...')
        tw_b1 = self.line_b1.twiss(skip_global_quantities=True).to_pandas()
        print('Computing twiss for beam 2...')
        tw_b2 = self.line_b2.twiss(skip_global_quantities=True).to_pandas()
        print('Done computing twiss.')

        # Remove the aperture
        tw_b1 = tw_b1[~tw_b1.name.str.contains('aper')]
        tw_b2 = tw_b2[~tw_b2.name.str.contains('aper')]

        tw_b2['y'] = -tw_b2['y']

        # Drop the unnecessary columns
        self.tw_b1 = tw_b1[['s', 'name', 'x', 'y', 'betx', 'bety']]
        self.tw_b2 = tw_b2[['s', 'name', 'x', 'y', 'betx', 'bety']]

        # Define attributes
        print('Almost there...')
        self._define_nominal_crossing()
        self._define_sigma()


    def _define_nominal_crossing(self):

        # Define the nominal crossing for given configuration
        self.tw_b1.loc[:, 'nom_x'] = self.tw_b1['x']
        self.tw_b1.loc[:, 'nom_y'] = self.tw_b1['y']
        
        self.tw_b2.loc[:, 'nom_x'] = self.tw_b2['x']
        self.tw_b2.loc[:, 'nom_y'] = self.tw_b2['y']

    def _define_sigma(self):

        self.tw_b1.loc[:, 'sigma_x'] = np.sqrt(self.tw_b1['betx'] * self.emitt / self.gamma)
        self.tw_b1.loc[:, 'sigma_y'] = np.sqrt(self.tw_b1['bety'] * self.emitt / self.gamma)

        self.tw_b2.loc[:, 'sigma_x'] = np.sqrt(self.tw_b2['betx'] * self.emitt / self.gamma)
        self.tw_b2.loc[:, 'sigma_y'] = np.sqrt(self.tw_b2['bety'] * self.emitt / self.gamma)

        # Envelope
        self.envelope(self.n)  

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

        with open(self.collimators_path, 'r') as file:
            f = yaml.safe_load(file)
    
        cols_b1 = f['collimators']['b1']
        col_b1 = pd.DataFrame(cols_b1)
        col_b1 = col_b1[['gap', 'angle']]

        cols_b2 = f['collimators']['b2']
        col_b2 = pd.DataFrame(cols_b2)
        col_b2 = col_b2[['gap', 'angle']]

        xname_b1 = col_b1.columns[col_b1.loc['angle'] == 0].to_numpy()
        yname_b1 = col_b1.columns[col_b1.loc['angle'] == 90].to_numpy()

        xname_b2 = col_b2.columns[col_b2.loc['angle'] == 0].to_numpy()
        yname_b2 = col_b2.columns[col_b2.loc['angle'] == 90].to_numpy()

        #find collimators in horizontal and vertical plane
        colx_b1 = col_b1[xname_b1]
        coly_b1 = col_b1[yname_b1]

        colx_b2 = col_b2[xname_b2]
        coly_b2 = col_b2[yname_b2]

        # Beam 1

        xgap_b1 = colx_b1.loc['gap'].to_numpy()
        ygap_b1 = coly_b1.loc['gap'].to_numpy()

        s_col_b1 = self.tw_b1["s"].to_numpy()
        name_col_b1 = self.tw_b1["name"].to_numpy()

        #find the collimators by name in the other file
        indx = np.where(np.isin(name_col_b1, xname_b1))[0]
        indy = np.where(np.isin(name_col_b1, yname_b1))[0]

        #get the positions of the collimators relative to IP5
        s_colx_b1 = s_col_b1[indx]
        s_coly_b1 = s_col_b1[indy]

        #get sigma at the collimator positions and hence calculate the gap in [m]
        col_sigmax_b1 = self.tw_b1.sigma_x[np.isin(self.tw_b1.s, s_colx_b1)]
        col_gapx_b1 = (col_sigmax_b1*xgap_b1)

        col_sigmay_b1 = self.tw_b1.sigma_y[np.isin(self.tw_b1.s, s_coly_b1)]
        col_gapy_b1 = (col_sigmay_b1*ygap_b1)

        # Beam 2

        xgap_b2 = colx_b2.loc['gap'].to_numpy()
        ygap_b2 = coly_b2.loc['gap'].to_numpy()

        s_col_b2 = self.tw_b2["s"].to_numpy()
        name_col_b2 = self.tw_b2["name"].to_numpy()

        #find the collimators by name in the other file
        indx = np.where(np.isin(name_col_b2, xname_b2))[0]
        indy = np.where(np.isin(name_col_b2, yname_b2))[0]

        #get the positions of the collimators relative to IP5
        s_colx_b2 = s_col_b2[indx]
        s_coly_b2 = s_col_b2[indy]

        #get sigma at the collimator positions and hence calculate the gap in [m]
        col_sigmax_b2 = self.tw_b1.sigma_x[np.isin(self.tw_b2.s, s_colx_b2)]
        col_gapx_b2 = (col_sigmax_b2*xgap_b1)

        col_sigmay_b2 = self.tw_b2.sigma_y[np.isin(self.tw_b2.s, s_coly_b2)]
        col_gapy_b2 = (col_sigmay_b2*ygap_b2)

        if plane == 'v':
            # Add x collimators
            for i in range(len(s_colx_b1)):
                #change the thickness
                x0=s_colx_b1[i]-0.5
                y0=col_gapx_b1[i]
                x1=s_colx_b1[i]+0.5
                y1=0.05
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=xname_b1[i]), row=2, col=1)
                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[-y0, -y1, -y1, -y0], fill="toself", mode='lines',
                             fillcolor='black', line=dict(color='black'), name=xname_b1[i]), row=2, col=1)

    def _add_machine_components(self, fig, row, column):
        
        df = tfs.read(self.machine_components_path)

        objects = ["SBEND", "COLLIMATOR", "SEXTUPOLE", "RBEND", "QUADRUPOLE"]
        colors = ['lightblue', 'black', 'hotpink', 'green', 'red']

        for n, obj in enumerate(objects):
            
            obj_df = df[df['KEYWORD'] == obj]
            
            for i in range(obj_df.shape[0]):

                x0=obj_df.iloc[i]['S']-obj_df.iloc[i]['L']/2
                x1=obj_df.iloc[i]['S']+obj_df.iloc[i]['L']/2
                
                if obj=='QUADRUPOLE':
                    y0=0
                    y1=np.sign(obj_df.iloc[i]['K1L']).astype(int)
                    
                else:
                    y0=-0.5
                    y1=0.5

                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor=colors[n], line=dict(color=colors[n]), name=obj_df.iloc[i]['NAME']), row=row, col=column) 

    def distance_from_nominal(self):

        #TODO
        pass

    def distance_to_aperture(self):

        #TODO
        pass


    def show(self, 
             plane,
             beam = 1,
             show_both_beams = True):
        
        # Create figure
        fig = make_subplots(rows=2, cols=1, row_heights=[0.2, 0.8], shared_xaxes=True)
        
        if plane == 'h':
            
            top_aper_b1 = go.Scatter(x=self.aper_b1.S, y=self.aper_b1.APER_1, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b1 = go.Scatter(x=self.aper_b1.S, y=-self.aper_b1.APER_1, mode='lines', line=dict(color='gray'), name='Aperture')     
            top_aper_b2 = go.Scatter(x=self.aper_b2.S, y=self.aper_b2.APER_1, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b2 = go.Scatter(x=self.aper_b2.S, y=-self.aper_b2.APER_1, mode='lines', line=dict(color='gray'), name='Aperture') 

            b1 = go.Scatter(x=self.tw_b1.s, y=self.tw_b1.x, mode='lines', line=dict(color='blue'), name='Beam 1')
            b2 = go.Scatter(x=self.tw_b2.s, y=self.tw_b2.x, mode='lines', line=dict(color='red'), name='Beam 2')
            nom_b1 = go.Scatter(x=self.tw_b1['s'], y=self.tw_b1['nom_x'], mode='lines', line=dict(color='blue', dash='dash'), name='Beam 1')
            nom_b2 = go.Scatter(x=self.tw_b2['s'], y=self.tw_b2['nom_x'], mode='lines', line=dict(color='red', dash='dash'), name='Beam 2')
            
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
            nom_b1 = go.Scatter(x=self.tw_b1['s'], y=self.tw_b1['nom_y'], mode='lines', line=dict(color='blue', dash='dash'), name='Beam 1')
            nom_b2 = go.Scatter(x=self.tw_b2['s'], y=self.tw_b2['nom_y'], mode='lines', line=dict(color='red', dash='dash'), name='Beam 2')
            
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
        self._add_collimators(fig=fig, row=2, column=1)

        # Set layout
        fig.update_layout(height=800, width=800, plot_bgcolor='white', showlegend=False)

        # Change the axes limits and labels
        fig.update_yaxes(range=[-1, 1], row=1, col=1, showticklabels=False, showline=False)

        fig.update_xaxes(title_text="s [m]", row=2, col=1)
        fig.update_xaxes(row=1, col=1, showticklabels=False, showline=False)

        fig.show()
        

                

