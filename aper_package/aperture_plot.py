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
                 emitt = 3.5e-6,
                 gamma = 7247.364689,
                 show_both_beams = True,
                 path1 = "/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX/levelling.20/all_optics_B1.tfs", 
                 path2 = "/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX/levelling.20/all_optics_B4.tfs",
                 line1 = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/xsuite/levelling.20_b1.json',
                 line2 = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/xsuite/levelling.20_b2.json',
                 machine_components_path = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B1.tfs',
                 collimators_path = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/colldbs/levelling.20.yaml'):
        
        self.emitt = emitt
        self.gamma = gamma
        
        df_b1 = tfs.read(path1)
        df_b2 = tfs.read(path2)

        self.machine_components_path = machine_components_path
        self.collimators_path = collimators_path
        
        #get rid of undefined values
        indices_b1 = df_b1.index[(df_b1['APER_1'] < 1) & (df_b1['APER_1'] != 0) & (df_b1['APER_2'] < 1) & (df_b1['APER_2'] != 0)].tolist()
        s_b1 = df_b1["S"][indices_b1].to_numpy()
        
        aperx_b1 = df_b1["APER_1"][indices_b1].to_numpy()
        apery_b1 = df_b1["APER_2"][indices_b1].to_numpy()
        
        indices_b2 = df_b2.index[(df_b2['APER_1'] < 1) & (df_b2['APER_1'] != 0) & (df_b2['APER_2'] < 1) & (df_b2['APER_2'] != 0)].tolist()
        s_b2 = df_b2["S"][indices_b2].to_numpy()
            
        aperx_b2 = df_b2["APER_1"][indices_b2].to_numpy()
        apery_b2 = df_b2["APER_2"][indices_b2].to_numpy()

        # Load a line and build tracker
        line_b1 = xt.Line.from_json(line1)
        line_b2 = xt.Line.from_json(line2)

        print('Computing twiss for beam 1...')
        tw_b1 = line_b1.twiss()
        print('Computing twiss for beam 2...')
        tw_b2 = line_b2.twiss(reverse=True)
        print('Done computing twiss.')

        # Remove all the aperture
        tw_b1 = tw_b1.to_pandas()[~tw_b1.to_pandas().name.str.contains('aper')]
        tw_b2 = tw_b2.to_pandas()[~tw_b2.to_pandas().name.str.contains('aper')]
        
        # Define all the arrays, convert to numpy, and calulate sigma
        tws_b1 = tw_b1.s.to_numpy()
        # elements at the same position for both beam 1 and beam 2
        tws_b2 = tw_b2.s.to_numpy()[-1]-tw_b2.s.to_numpy()
        
        # TODO maybe later shorten this:

        print('Defining variables...')

        # Match the lengths of data for both s_b1 and tws_b1 to facilitate calculations 
        # of the distance of the beam from the aperture later
        if len(s_b1) > len(tws_b1): 

            indices = match_indices(tws_b1, s_b1)

            self.s_b1 = tws_b1
            self.name = tw_b1.name.to_numpy()
            
            # Horizontal data for beam 1
            self.x_b1 = tw_b1.x.to_numpy()
            self.betx_b1 = tw_b1.betx.to_numpy()
            self.sigmax_b1 = np.sqrt(self.betx_b1*self.emitt/self.gamma)

            # Vertical data for beam 1
            self.y_b1 = tw_b1.y.to_numpy()
            self.bety_b1 = tw_b1.bety.to_numpy()
            self.sigmay_b1 = np.sqrt(self.bety_b1*self.emitt/self.gamma)   
            
            # Aperture data shortened to match the length of twiss
            self.aperx_b1 = aperx_b1[indices]
            self.apery_b1 = apery_b1[indices]
             
        else:

            indices = match_indices(s_b1, tws_b1)

            self.s_b1 = s_b1
            self.name = tw_b1.name.to_numpy()[indices]
            
            # Horizontal data for beam 1
            self.x_b1 = tw_b1.x.to_numpy()[indices]
            self.betx_b1 = tw_b1.betx.to_numpy()[indices]
            self.sigmax_b1 = np.sqrt(self.betx_b1*self.emitt/self.gamma)

            # Vertical data for beam 1
            self.y_b1 = tw_b1.y.to_numpy()[indices]
            self.bety_b1 = tw_b1.bety.to_numpy()[indices]
            self.sigmay_b1 = np.sqrt(self.bety_b1*self.emitt/self.gamma)   
            
            # Aperture data shortened to match the length of twiss
            self.aperx_b1 = aperx_b1
            self.apery_b1 = apery_b1
       
        # Match the length of s_b2 and tws_b2
        if len(s_b2) > len(tws_b2): 

            indices = match_indices(tws_b2, s_b2)

            self.s_b2 = tws_b2
            self.name = tw_b2.name.to_numpy()
            
            # Horizontal data for beam 1
            self.x_b2 = -tw_b2.x.to_numpy()
            self.betx_b2 = tw_b2.betx.to_numpy()
            self.sigmax_b2 = np.sqrt(self.betx_b2*self.emitt/self.gamma)

            # Vertical data for beam 1
            self.y_b2 = -tw_b2.y.to_numpy()
            self.bety_b2 = tw_b2.bety.to_numpy()
            self.sigmay_b2 = np.sqrt(self.bety_b2*self.emitt/self.gamma)   
            
            # Aperture data shortened to match the length of twiss
            self.aperx_b2 = aperx_b2[indices]
            self.apery_b2 = apery_b2[indices]
             
        else:

            indices = match_indices(s_b2, tws_b2)

            self.s_b2 = s_b2
            self.name = tw_b2.name.to_numpy()[indices]
            
            # Horizontal data for beam 1
            self.x_b2 = -tw_b2.x.to_numpy()[indices]## Find locations of IPs
            self.betx_b2 = tw_b2.betx.to_numpy()[indices]
            self.sigmax_b2 = np.sqrt(self.betx_b2*self.emitt/self.gamma)

            # Vertical data for beam 1
            self.y_b2 = -tw_b2.y.to_numpy()[indices]
            self.bety_b2 = tw_b2.bety.to_numpy()[indices]
            self.sigmay_b2 = np.sqrt(self.bety_b2*self.emitt/self.gamma)   
            
            # Aperture data shortened to match the length of twiss
            self.aperx_b2 = aperx_b2
            self.apery_b2 = apery_b2

        self.nominalx_b1 = self.x_b1
        self.nominalx_b2 = self.x_b2
        
        self.nominaly_b1 = self.y_b1
        self.nominaly_b2 = self.y_b2

        self.envelope(0)

        ## Find locations of IPs
        self.ip_names = np.array(['ip1', 'ip2', 'ip5', 'ip8'])
        self.ip_b1 = tw_b1.loc[tw_b1['name'].isin(self.ip_names)].s.to_numpy()
        self.ip_b2 = tw_b2.loc[tw_b2['name'].isin(self.ip_names)].s.to_numpy()
        
        del tw_b1, tw_b2        
        
    def envelope(self, n):

        self.n = n
        
        #recalculate the envelope edges for the new angle
        self.xup_b1 = self.x_b1+n*self.sigmax_b1
        self.xdown_b1 = self.x_b1-n*self.sigmax_b1
        self.xup_b2 = self.x_b2+n*self.sigmax_b2
        self.xdown_b2 = self.x_b2-n*self.sigmax_b2
        
        self.yup_b1 = self.y_b1+n*self.sigmay_b1
        self.ydown_b1 = self.y_b1-n*self.sigmay_b1
        self.yup_b2 = self.y_b2+n*self.sigmay_b2
        self.ydown_b2 = self.y_b2-n*self.sigmay_b2

    def _rescale_factor(self, angle, ip, plane, lim):
        
        #TODO add code for IP1

        # Find iposition of ip
        ip_s = self.ip_b1[np.where(self.ip_names == ip)[0][0]]

        #use only the data up to 20 m away from the ip
        ind = np.where(((self.s_b1 - ip_s) >= 0) & ((self.s_b1 - ip_s) < lim))
        s = self.s_b1[ind]
        if plane == 'h':
            x = self.x_b1[ind]
        elif plane == 'v':
            x = self.y_b1[ind]

        adjacent = s[-1]-s[0]
        opposite = adjacent * np.tan(angle*1e-6)

        factor = opposite/(x[-1]-x[0])

        return factor 
    
    def rescale_data(self, angle, ip, plane, lim=20):
        
        #get the rescaling factor
        f = self._rescale_factor(angle, ip, plane, lim) 
        
        if plane == 'h':
            self.x_b1 = f*self.x_b1
            self.x_b2 = f*self.x_b2
            
        elif plane == 'v':
            self.y_b1 = f*self.y_b1
            self.y_b2 = f*self.y_b2    

        self.envelope(self.n)        

    def _add_collimators(self, fig, row, column):

        #TODO
        pass


    def _load_machine_components(self):

        df = tfs.read(self.machine_components_path)
        
        s = df['S'].to_numpy()
        keyword = df['KEYWORD'].to_numpy()
        l = df['L'].to_numpy()
        k1l = df['K1L'].to_numpy()
        name = df['NAME'].to_numpy()

        return s, keyword, l, k1l, name
        

    def _add_machine_components(self, fig, row, column):
        
        s, keyword, l, k1l, name = self._load_machine_components()

        objects = ["SBEND", "COLLIMATOR", "SEXTUPOLE", "RBEND", "QUADRUPOLE"]
        colors = ['lightblue', 'black', 'hotpink', 'green', 'red']

        for n, j in enumerate(objects):
            
            ob_s = s[np.where(keyword==j)[0]]
            ob_l = l[np.where(keyword==j)[0]]
            ob_name = name[np.where(keyword==j)[0]]
            ob_k1l = np.sign(k1l[np.where(keyword=="QUADRUPOLE")[0]]).astype(int)
            
            for i in range(len(ob_s)):

                x0=ob_s[i]-ob_l[i]/2
                x1=ob_s[i]+ob_l[i]/2
                
                if j=='QUADRUPOLE':
                    y0=0
                    y1=ob_k1l[i]
                    
                else:
                    y0=-0.5
                    y1=0.5

                fig.add_trace(go.Scatter(x=[x0, x0, x1, x1], y=[y0, y1, y1, y0], fill="toself", mode='lines',
                             fillcolor=colors[n], line=dict(color=colors[n]), name=ob_name[i]), row=row, col=column)  


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
            
            top_aper_b1 = go.Scatter(x=self.s_b1, y=self.aperx_b1, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b1 = go.Scatter(x=self.s_b1, y=-self.aperx_b1, mode='lines', line=dict(color='gray'), name='Aperture')     
            top_aper_b2 = go.Scatter(x=self.s_b2, y=self.aperx_b2, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b2 = go.Scatter(x=self.s_b2, y=-self.aperx_b2, mode='lines', line=dict(color='gray'), name='Aperture') 

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
            
            top_aper_b1 = go.Scatter(x=self.s_b1, y=self.apery_b1, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b1 = go.Scatter(x=self.s_b1, y=-self.apery_b1, mode='lines', line=dict(color='gray'), name='Aperture')
            top_aper_b2 = go.Scatter(x=self.s_b2, y=self.apery_b2, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b2 = go.Scatter(x=self.s_b2, y=-self.apery_b2, mode='lines', line=dict(color='gray'), name='Aperture') 
            
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

        # Set layout
        fig.update_layout(height=800, width=800, plot_bgcolor='white', showlegend=False)

        # Change the axes limits and labels
        fig.update_yaxes(range=[-1, 1], row=1, col=1, showticklabels=False, showline=False)

        fig.update_xaxes(title_text="s [m]", row=2, col=1)
        fig.update_xaxes(row=1, col=1, showticklabels=False, showline=False)

        fig.show()
        

                

