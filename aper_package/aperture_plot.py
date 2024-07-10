import sys
sys.path.append('/eos/home-i03/m/morwat/.local/lib/python3.9/site-packages/')

import numpy as np
import pandas as pd
import tfs
import yaml

import xtrack as xt

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from aper_package.utils import match_indices

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
        df_b2 = tfs.read(path2)[['S', 'NAME', 'APER_1', 'APER_2']]

        # Filtering the DataFrame to only have the IP locations
        self.ip_df_b1 = df_b1[df_b1['NAME'].isin(['IP1', 'IP2', 'IP4', 'IP5', 'IP6', 'IP8'])]
        self.ip_df_b1['NAME'] = self.ip_df_b1['NAME'].str.lower()  
        self.ip_df_b2 = df_b2[df_b2['NAME'].isin(['IP1', 'IP2', 'IP4', 'IP5', 'IP6', 'IP8'])]
        self.ip_df_b2['NAME'] = self.ip_df_b2['NAME'].str.lower()    
        
        #get rid of undefined and unnecessary values
        self.aper_b1 = df_b1[(df_b1['APER_1'] < 1) & (df_b1['APER_1'] != 0) & (df_b1['APER_2'] < 1) & (df_b1['APER_2'] != 0)]
        self.aper_b2 = df_b2[(df_b2['APER_1'] < 1) & (df_b2['APER_1'] != 0) & (df_b2['APER_2'] < 1) & (df_b2['APER_2'] != 0)]

        # Load a line and build tracker
        self.line_b1 = xt.Line.from_json(line1)
        self.line_b2 = xt.Line.from_json(line2)

        self.change_ip(ip)

    def change_ip(self, ip):

        if ip == 'ip1': ip0 = 'ip5'
        elif ip == 'ip2': ip0 = 'ip6'
        elif ip == 'ip5': ip0 = 'ip1'
        elif ip == 'ip8': ip0 = 'ip4'
        else: print('Incorrect IP') #TODO change that to error pop-up

        # Set the chosen IP as the middle
        self.line_b1.cycle(ip0)
        self.line_b2.cycle(ip0)

        # Generate twiss
        print('Computing twiss for beam 1...')
        tw_b1 = self.line_b1.twiss().to_pandas()
        print('Computing twiss for beam 2...')
        tw_b2 = self.line_b2.twiss(reverse=True).to_pandas()
        print('Done computing twiss.')

        # Remove the aperture
        tw_b1 = tw_b1[~tw_b1.name.str.contains('aper')]
        tw_b2 = tw_b2[~tw_b2.name.str.contains('aper')]

        # Drop the unnecessary columns
        tw_b1 = tw_b1[['s', 'name', 'x', 'y', 'betx', 'bety']]
        tw_b2 = tw_b2[['s', 'name', 'x', 'y', 'betx', 'bety']]

        # Define attributes
        print('Almost there...')
        self._define_nominal_crossing(tw_b1, tw_b2)
        self._define_attributes(tw_b1, tw_b2)

        # Shift the aperture accordingly

        columns_to_shift = self.aper_b1.columns[self.aper_b1.columns != 'S'] #Exclude column 'S'

        s_b1 = self.ip_df_b1.loc[self.ip_df_b1['NAME'] == ip0, 'S'].values[0]
        s_b2 = self.ip_df_b2.loc[self.ip_df_b2['NAME'] == ip0, 'S'].values[0]
        
        shift_b1 = -(self.aper_b1['S'] - s_b1).abs().idxmin()
        shift_b2 = -(self.aper_b2['S'] - s_b2).abs().idxmin()

        #TODO fix that bit
        for col in columns_to_shift:
            self.aper_b1[col] = self.aper_b1[col].shift(shift_b1, fill_value=self.aper_b1[col].iloc[:shift_b1].values)
            self.aper_b2[col] = self.aper_b2[col].shift(shift_b2, fill_value=self.aper_b2[col].iloc[:shift_b2].values)


    def _define_nominal_crossing(self, tw_b1, tw_b2):

        # Define the nominal crossing for given configuration
        self.nominalx_b1 = tw_b1.x
        self.nominalx_b2 = -tw_b2.x
        
        self.nominaly_b1 = tw_b1.y
        self.nominaly_b2 = tw_b2.y

    def _define_attributes(self, tw_b1, tw_b2):
        
        # Position and element names for beam 1
        self.s_b1 = tw_b1.s.to_numpy()
        self.name_b1 = tw_b1.name.to_numpy()
            
        # Horizontal data for beam 1
        self.x_b1 = tw_b1.x.to_numpy()
        self.betx_b1 = tw_b1.betx.to_numpy()
        self.sigmax_b1 = np.sqrt(self.betx_b1*self.emitt/self.gamma)

        # Vertical data for beam 1
        self.y_b1 = tw_b1.y.to_numpy()
        self.bety_b1 = tw_b1.bety.to_numpy()
        self.sigmay_b1 = np.sqrt(self.bety_b1*self.emitt/self.gamma)   
        
        # Position and element names for beam 2
        self.s_b2 = tw_b2.s.to_numpy()[-1] - tw_b2.s.to_numpy()
        self.name_b2 = tw_b2.name.to_numpy()
            
        # Horizontal data for beam 1
        self.x_b2 = -tw_b2.x.to_numpy()
        self.betx_b2 = tw_b2.betx.to_numpy()
        self.sigmax_b2 = np.sqrt(self.betx_b2*self.emitt/self.gamma)

        # Vertical data for beam 1
        self.y_b2 = -tw_b2.y.to_numpy()
        self.bety_b2 = tw_b2.bety.to_numpy()
        self.sigmay_b2 = np.sqrt(self.bety_b2*self.emitt/self.gamma)   

        # Envelope
        self.envelope(self.n)  

    def envelope(self, n):

        self.n = n
        
        #recalculate the envelope edges for the new envelope size
        self.xup_b1 = self.x_b1+n*self.sigmax_b1
        self.xdown_b1 = self.x_b1-n*self.sigmax_b1
        self.xup_b2 = self.x_b2+n*self.sigmax_b2
        self.xdown_b2 = self.x_b2-n*self.sigmax_b2
        
        self.yup_b1 = self.y_b1+n*self.sigmay_b1
        self.ydown_b1 = self.y_b1-n*self.sigmay_b1
        self.yup_b2 = self.y_b2+n*self.sigmay_b2
        self.ydown_b2 = self.y_b2-n*self.sigmay_b2

    def _add_collimators(self, fig, row, column):

        #TODO
        pass

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

            b1 = go.Scatter(x=self.s_b1, y=self.x_b1, mode='lines', line=dict(color='blue'), name='Beam 1')
            b2 = go.Scatter(x=self.s_b2, y=self.x_b2, mode='lines', line=dict(color='red'), name='Beam 2')
            nom_b1 = go.Scatter(x=self.s_b1, y=self.nominalx_b1, mode='lines', line=dict(color='blue', dash='dash'), name='Beam 1')
            nom_b2 = go.Scatter(x=self.s_b2, y=self.nominalx_b2, mode='lines', line=dict(color='red', dash='dash'), name='Beam 2')
            
            up_b1 = self.xup_b1
            down_b1 = self.xdown_b1
            up_b2 = self.xup_b2
            down_b2 = self.xdown_b2
            
            fig.update_yaxes(range=[-0.05, 0.05], title_text="x [m]", row=2, col=1)
            
        elif plane == 'v':
            
            top_aper_b1 = go.Scatter(x=self.aper_b1.S, y=self.aper_b1.APER_2, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b1 = go.Scatter(x=self.aper_b1.S, y=-self.aper_b1.APER_2, mode='lines', line=dict(color='gray'), name='Aperture')
            top_aper_b2 = go.Scatter(x=self.aper_b2.S, y=self.aper_b2.APER_2, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b2 = go.Scatter(x=self.aper_b2.S, y=-self.aper_b12.APER_2, mode='lines', line=dict(color='gray'), name='Aperture') 
            
            b1 = go.Scatter(x=self.s_b1, y=self.y_b1, mode='lines', line=dict(color='blue'), name='Beam 1')
            b2 = go.Scatter(x=self.s_b2, y=self.y_b2, mode='lines', line=dict(color='red'),name='Beam 2')
            nom_b1 = go.Scatter(x=self.s_b1, y=self.nominaly_b1, mode='lines', line=dict(color='blue', dash='dash'), name='Beam 1')
            nom_b2 = go.Scatter(x=self.s_b2, y=self.nominaly_b2, mode='lines', line=dict(color='red', dash='dash'), name='Beam 2')
            
            up_b1 = self.yup_b1
            down_b1 = self.ydown_b1
            up_b2 = self.yup_b2
            down_b2 = self.ydown_b2

            fig.update_yaxes(range=[-0.05, 0.05], title_text="y [m]", row=2, col=1)

        else: print('Incorrect plane')

        upper_b1 = go.Scatter(x=self.s_b1, y=up_b1, mode='lines', name='Upper envelope beam 1', fill=None, line=dict(color='rgba(0,0,255,0)'))
        lower_b1 = go.Scatter(x=self.s_b1, y=down_b1, mode='lines', name='Lower envelope beam 1', line=dict(color='rgba(0,0,255,0)'), 
                          fill='tonexty', fillcolor='rgba(0,0,255,0.1)')

        upper_b2 = go.Scatter(x=self.s_b2, y=up_b2, mode='lines', name='Upper envelope beam 2', fill=None, line=dict(color='rgba(255,0,0,0)'))
        lower_b2 = go.Scatter(x=self.s_b2, y=down_b2, mode='lines', name='Lower envelope beam 2', line=dict(color='rgba(255,0,0,0)'), 
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
        

                

