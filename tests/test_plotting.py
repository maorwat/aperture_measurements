import unittest
import pandas as pd
import numpy as np

from pathlib import Path
import sys

home_path = str(Path.cwd().parent)
sys.path.append(home_path)

from aper_package.aperture_data import Data
from aper_package.plotting import create_figure

class TestPlotting(unittest.TestCase):
    
    def setUp(self):

        line = home_path+'/test_data/Martas_injection_b1.json'
        self.data = Data(line)
        path = home_path+'/test_data/all_optics_B1.tfs'
        self.data.load_aperture(path)

    def test_create_figure(self):
        
        fig, visibility_b1, visibility_b2, row, col = create_figure(self.data, 'h', None, None)
        
        expected_visibility_b1 = np.array([ True,  True, False, False,  True,  True,  True,  True,  True, True,  True,  True])
        expected_visibility_b2 = np.array([False, False,  True,  True,  True,  True,  True,  True,  True, True,  True,  True])
        np.testing.assert_array_equal(visibility_b1, expected_visibility_b1)
        np.testing.assert_array_equal(visibility_b2, expected_visibility_b2)
        self.assertEqual(row, 1)
        self.assertEqual(col, 1)
        self.assertEqual(len(fig.data), 12)

        self.assertEqual(len(fig.data[1]['y']), 29057)
        self.assertEqual(len(fig.data[2]['x']), 29085)
        self.assertEqual(len(fig.data[3]['y']), 29085)
        self.assertEqual(len(fig.data[4]['x']), 34939)
        self.assertEqual(fig.data[5]['text'][0], 'lhcb2ip1.l1_p_')
        self.assertEqual(fig.data[6]['text'][0], 'ip1')


if __name__ == '__main__':
    unittest.main()