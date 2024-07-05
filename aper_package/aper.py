import numpy as np
import tfs

from aper_package.utils import match_indices

class Aper:
    
    def __init__(self, path1 = "/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX/levelling.20/all_optics_B1.tfs", 
                 path2 = "/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX/levelling.20/all_optics_B4.tfs"):
        
        df_b1 = tfs.read(path1)
        df_b2 = tfs.read(path2)
        
        #get rid of undefined values
        indices_b1 = df_b1.index[(df_b1['APER_1'] < 1) & (df_b1['APER_1'] != 0) & (df_b1['APER_2'] < 1) & (df_b1['APER_2'] != 0)].tolist()
        s_b1 = df_b1["S"][indices_b1].to_numpy()
        name_b1 = df_b1["NAME"][indices_b1].to_numpy()
        
        aperx_b1 = df_b1["APER_1"][indices_b1].to_numpy()
        apery_b1 = df_b1["APER_2"][indices_b1].to_numpy()
        
        indices_b2 = df_b2.index[(df_b2['APER_1'] < 1) & (df_b2['APER_1'] != 0) & (df_b2['APER_2'] < 1) & (df_b2['APER_2'] != 0)].tolist()
        s_b2 = df_b2["S"][indices_b2].to_numpy()
        name_b2 = df_b2["NAME"][indices_b2].to_numpy()
            
        aperx_b2 = df_b2["APER_1"][indices_b2].to_numpy()
        apery_b2 = df_b2["APER_2"][indices_b2].to_numpy()
        
        # Match the lengths of data for both arrays, it makes stuff easier!!
        if len(s_b1) > len(s_b2): 
            indices = match_indices(s_b2, s_b1)
            self.s = s_b2
            self.name = name_b2
            
            self.x_b2 = aperx_b2
            self.y_b2 = apery_b2
            
            self.x_b1 = aperx_b1[indices]
            self.y_b1 = apery_b1[indices]
             
        else:
            indices = match_indices(s_b1, s_b2)
            self.s = s_b1
            self.name = name_b1
            
            self.x_b1 = aperx_b1
            self.y_b1 = apery_b1
            
            self.x_b2 = aperx_b2[indices]
            self.y_b2 = apery_b2[indices]
            
    def plot(self, plane, fig, row = 2, column = 1, beam1 = True, beam2 = True):
        
        if plane == 'h':
            
            top_aper_b1 = go.Scatter(x=self.s, y=self.x_b1, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b1 = go.Scatter(x=self.s, y=-self.x_b1, mode='lines', line=dict(color='gray'), name='Aperture')      
            
        if plane == 'v':
            
            top_aper_b1 = go.Scatter(x=self.s, y=self.y_b1, mode='lines', line=dict(color='gray'), name='Aperture')
            bottom_aper_b1 = go.Scatter(x=self.s, y=-self.y_b1, mode='lines', line=dict(color='gray'), name='Aperture')

        
        if beam1:
            fig.add_trace(top_aper_b1, row=row, col=column) 
            fig.add_trace(bottom_aper_b1, row=row, col=column)
        
        if beam2:
            fig.add_trace(top_aper_b2, row=row, col=column) 
            fig.add_trace(bottom_aper_b2, row=row, col=column)
                

