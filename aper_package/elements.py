import tfs
import numpy as np
import plotly.graph_objects as go

class Elements():
    
    def __init__(self, path='/eos/project-c/collimation-team/machine_configurations/LHC_run3/2023/MADX_thick/injection/all_optics_B1.tfs',
                objects = ["SBEND", "COLLIMATOR", "SEXTUPOLE", "RBEND", "QUADRUPOLE"], 
                 colors = ['lightblue', 'black', 'hotpink', 'green', 'red']):
        
        df = tfs.read(path)
        
        self.s = df['S'].to_numpy()
        self.keyword = df['KEYWORD'].to_numpy()
        self.l = df['L'].to_numpy()
        self.k1l = df['K1L'].to_numpy()
        self.name = df['NAME'].to_numpy()
        
        self.objects = objects
        self.colors = colors
        
    def plot(self, fig, row=1, column=1):

        for n, j in enumerate(self.objects):
            
            ob_s = self.s[np.where(self.keyword==j)[0]]
            ob_l = self.l[np.where(self.keyword==j)[0]]
            ob_name = self.name[np.where(self.keyword==j)[0]]
            ob_k1l = np.sign(self.k1l[np.where(self.keyword=="QUADRUPOLE")[0]]).astype(int)
            
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
                             fillcolor=self.colors[n], line=dict(color=self.colors[n]), name=ob_name[i]), row=row, col=column)      
        