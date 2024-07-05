import pandas as pd
import numpy as np
import xtrack as xt
import plotly.graph_objects as go

from aper_package.utils import match_indices

class Twiss():
      
    def __init__(self, path1 = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/xsuite/levelling.20_b1.json', 
                 path2 = '/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/xsuite/levelling.20_b2.json'):
        
        #define normalised emittance
        emitt=3.5e-6
        #define gamma
        gamma = 7247.364689 #TO AUTOMATE
        
        # Load a line and build tracker
        line_b1 = xt.Line.from_json(path1)
        line_b2 = xt.Line.from_json(path2)
        
        # Twiss
        tw_b1 = line_b1.twiss()
        tw_b2 = line_b2.twiss(reverse=True)

        # Remove all the aperture
        tw_b1 = tw_b1.to_pandas()[~tw_b1.to_pandas().name.str.contains('aper')]
        tw_b2 = tw_b2.to_pandas()[~tw_b2.to_pandas().name.str.contains('aper')]
        
        # Define all the arrays, convert to numpy, and calulate sigma
        s_b1 = tw_b1.s.to_numpy()
        # elements at the same position for both beam 1 and beam 2
        s_b2 = tw_b2.s.to_numpy()[-1]-tw_b2.s.to_numpy()
        
        
        # Match the lengths of data for both arrays, it makes stuff easier!!
        if len(s_b1) > len(s_b2): 
            indices = match_indices(s_b2, s_b1)
            self.s = s_b2
            
            # Name of components
            self.name = tw_b2.name.to_numpy()   
            
            # Horizontal data for beam 1
            self.x_b1 = tw_b1.x.to_numpy()[indices]
            self.betx_b1 = tw_b1.betx.to_numpy()[indices]
            self.sigmax_b1 = np.sqrt(self.betx_b1*emitt/gamma)
        
            # Vertical data for beam 1
            self.y_b1 = tw_b1.y.to_numpy()[indices]
            self.bety_b1 = tw_b1.bety.to_numpy()[indices]
            self.sigmay_b1 = np.sqrt(self.bety_b1*emitt/gamma)
            
            # Horizontal data for beam 2
            self.x_b2 = -tw_b2.x.to_numpy()
            self.betx_b2 = tw_b2.betx.to_numpy()
            self.sigmax_b2 = np.sqrt(self.betx_b2*emitt/gamma)
        
            # Vertical data for beam 1
            self.y_b2 = -tw_b2.y.to_numpy() #I'm not sure if I really should reverse that
            self.bety_b2 = tw_b2.bety.to_numpy()
            self.sigmay_b2 = np.sqrt(self.bety_b2*emitt/gamma)
        
        
        else: 
            indices = match_indices(s_b1, s_b2)
            self.s = s_b1
            
            # Name of components
            self.name = tw_b1.name.to_numpy()
            
            # Horizontal data for beam 1
            self.x_b1 = tw_b1.x.to_numpy()
            self.betx_b1 = tw_b1.betx.to_numpy()
            self.sigmax_b1 = np.sqrt(self.betx_b1*emitt/gamma)
        
            # Vertical data for beam 1
            self.y_b1 = tw_b1.y.to_numpy()
            self.bety_b1 = tw_b1.bety.to_numpy()
            self.sigmay_b1 = np.sqrt(self.bety_b1*emitt/gamma)   
        
            # Horizontal data for beam 2
            self.x_b2 = -tw_b2.x.to_numpy()[indices]
            self.betx_b2 = tw_b2.betx.to_numpy()[indices]
            self.sigmax_b2 = np.sqrt(self.betx_b2*emitt/gamma)
        
            # Vertical data for beam 1
            self.y_b2 = -tw_b2.y.to_numpy()[indices]
            self.bety_b2 = tw_b2.bety.to_numpy()[indices]
            self.sigmay_b2 = np.sqrt(self.bety_b2*emitt/gamma)
            
        self.nominalx_b1 = self.x_b1
        self.nominalx_b2 = self.x_b2
        self.nominaly_b1 = self.y_b1
        self.nominaly_b2 = self.y_b2
        
        del tw_b1, tw_b2        
               
    def envelope(self, n):
        
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
        
        # Find iposition of ip
        ip_s = self.s[np.where(self.name == ip)[0][0]]

        #use only the data up to 20 m away from the ip
        ind = np.where(((s - ip) >= 0) & ((s - ip) < lim))
        s = self.s[ind]
        if plane == 'h':
            x = self.x_b1[ind]
        elif plane == 'v':
            x = self.y_b1[ind]

        adjacent = s[-1]-s[0]
        opposite = adjacent * np.tan(crossing_angle*1e-6)

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
        
    def plot(self, plane, fig, row = 2, column = 1, beam1 = True, beam2 = True):
        
        if plane == 'h':
            
            b1 = go.Scatter(x=self.s, y=self.x_b1, mode='lines', line=dict(color='blue'), name='Beam 1')
            b2 = go.Scatter(x=self.s, y=self.x_b2, mode='lines', line=dict(color='red'), name='Beam 2')
            nom_b1 = go.Scatter(x=self.s, y=self.nominalx_b1, mode='lines', line=dict(color='blue', dash='dash'), name='Beam 1')
            nom_b2 = go.Scatter(x=self.s, y=self.nominalx_b2, mode='lines', line=dict(color='red', dash='dash'), name='Beam 2')
            
            up_b1 = self.xup_b1
            down_b1 = self.xdown_b1
            up_b2 = self.xup_b2
            down_b2 = self.xdown_b2
            
        if plane == 'v':
            
            b1 = go.Scatter(x=self.s, y=self.y_b1, mode='lines', line=dict(color='blue'), name='Beam 1')
            b2 = go.Scatter(x=self.s, y=self.y_b2, mode='lines', line=dict(color='red'),name='Beam 2')
            nom_b1 = go.Scatter(x=self.s, y=self.nominaly_b1, mode='lines', line=dict(color='blue', dash='dash'), name='Beam 1')
            nom_b2 = go.Scatter(x=self.s, y=self.nominaly_b2, mode='lines', line=dict(color='red', dash='dash'), name='Beam 2')
            
            up_b1 = self.yup_b1
            down_b1 = self.ydown_b1
            up_b2 = self.yup_b2
            down_b2 = self.ydown_b2

        upper_b1 = go.Scatter(x=self.s, y=up_b1, mode='lines', name='Upper envelope beam 1', fill=None, line=dict(color='rgba(0,0,255,0)'))
        lower_b1 = go.Scatter(x=self.s, y=down_b1, mode='lines', name='Lower envelope beam 1', line=dict(color='rgba(0,0,255,0)'), 
                          fill='tonexty', fillcolor='rgba(0,0,255,0.1)')

        upper_b2 = go.Scatter(x=self.s, y=up_b2, mode='lines', name='Upper envelope beam 2', fill=None, line=dict(color='rgba(255,0,0,0)'))
        lower_b2 = go.Scatter(x=self.s, y=down_b2, mode='lines', name='Lower envelope beam 2', line=dict(color='rgba(255,0,0,0)'), 
                           fill='tonexty', fillcolor='rgba(255,0,0,0.1)')

        traces_b1 = [b1, nom_b1, upper_b1, lower_b1]
        traces_b2 = [b2, nom_b2, upper_b2, lower_b2]
        
        if beam1:
            for i in traces_b1:
                fig.add_trace(i, row=row, col=column) 
        
        if beam2:
            for i in traces_b2:
                fig.add_trace(i, row=row, col=column) 
        

        
        
        