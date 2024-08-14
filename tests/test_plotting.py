import unittest
import pandas as pd
import numpy as np

from pathlib import Path
import sys

home_path = str(Path.cwd().parent)
sys.path.append(home_path)

from aper_package.aperture_data import ApertureData
from aper_package.plotting import *

class TestPlotting(unittest.TestCase):
    
    def setUp(self):

        line = home_path+'/test_data/Martas_injection_b1.json'
        self.data = ApertureData(line)
        path = home_path+'/test_data/all_optics_B1.tfs'
        self.data.load_aperture(path)

    def test_create_figure(self):
        
        fig, visibility_b1, visibility_b2, row, col = create_figure(self.data, 'h', None, None, None)
        
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

        fig, visibility_b1, visibility_b2, row, col = create_figure(self.data, 'v', None, None, None)

        expected_visibility_b1 = np.array([True, True, False, False, True, True, True, True, True, True, True, True])
        expected_visibility_b2 = np.array([False, False, True, True, True, True, True, True, True, True, True, True])
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

        self.data.load_elements(path=home_path+'/test_data/thick_all_optics_B1.tfs')

        fig, visibility_b1, visibility_b2, row, col = create_figure(self.data, 'v', None, None, None)
        self.assertEqual(row, 2)
        self.assertEqual(col, 1)
        self.assertEqual(len(fig.data), 3837)
        self.assertEqual(len(visibility_b1), 3837)
        self.assertEqual(len(visibility_b2), 3837)

        # Assuming fig.data[1000]['x'] exists and is comparable
        expected_values = (21642.38092286263, 21642.38092286263, 21656.680922862633, 21656.680922862633)
        
        for actual, expected in zip(fig.data[1000]['x'], expected_values):
            self.assertAlmostEqual(actual, expected, places=10)

    def test_plot_envelopes(self):

        vis, traces = plot_envelopes(self.data, 'h')

        np.testing.assert_array_equal(vis, np.array([True, True, True, True]))
        self.assertEqual(len(traces), 4)

        self.assertAlmostEqual(traces[0]['x'][0], 0, 10)
        self.assertAlmostEqual(traces[0]['x'][-1], 26658.88317687314, 10)
        self.assertAlmostEqual(traces[0]['y'][0], -0.002000142862473192, 10)
        self.assertAlmostEqual(traces[0]['y'][-1], -0.0020001428624731817, 10)

        self.assertEqual(len(traces[0]['x']), self.data.tw_b1.shape[0])
        self.assertEqual(len(traces[1]['x']), self.data.tw_b1.shape[0])
        self.assertEqual(len(traces[2]['y']), self.data.tw_b2.shape[0])
        self.assertEqual(len(traces[3]['y']), self.data.tw_b2.shape[0])

        vis, traces = plot_envelopes(self.data, 'v')

        np.testing.assert_array_equal(vis, np.array([True, True, True, True]))
        self.assertEqual(len(traces), 4)

        self.assertAlmostEqual(traces[0]['y'][0], -2.1961356293530347e-09, 10)
        self.assertAlmostEqual(traces[0]['y'][-1], -2.1961356297416947e-09, 10)

        self.assertEqual(len(traces[0]['x']), self.data.tw_b1.shape[0])
        self.assertEqual(len(traces[1]['x']), self.data.tw_b1.shape[0])
        self.assertEqual(len(traces[2]['y']), self.data.tw_b2.shape[0])
        self.assertEqual(len(traces[3]['y']), self.data.tw_b2.shape[0])

    def test_plot_beam_positions(self):

        vis, traces = plot_beam_positions(self.data, 'h')

        np.testing.assert_array_equal(vis, np.array([True, True]))
        self.assertEqual(len(traces), 2)

        self.assertAlmostEqual(traces[0]['x'][1000], 261.1706666666666, 10)
        self.assertAlmostEqual(traces[1]['x'][1000], 264.08433171133584, 10)
        self.assertAlmostEqual(traces[0]['y'][1000], 9.474557711656808e-07, 10)
        self.assertAlmostEqual(traces[1]['y'][1000], -1.2460130805535723e-07, 10)

        nom_vis, nom_traces = plot_beam_positions(self.data, 'h')

        self.assertTrue((nom_traces[0]['x']==traces[0]['x']).all())
        self.assertTrue((nom_traces[1]['x']==traces[1]['x']).all())
        self.assertTrue((nom_traces[0]['y']==traces[0]['y']).all())
        self.assertTrue((nom_traces[1]['y']==traces[1]['y']).all())

        vis, traces = plot_beam_positions(self.data, 'v')

        np.testing.assert_array_equal(vis, np.array([True, True]))
        self.assertEqual(len(traces), 2)

        self.assertAlmostEqual(traces[0]['y'][2000], -2.5213925117160937e-07, 10)
        self.assertAlmostEqual(traces[1]['y'][2000], 1.3734680420729657e-07, 10)

        nom_vis, nom_traces = plot_beam_positions(self.data, 'v')

        self.assertTrue((nom_traces[0]['x']==traces[0]['x']).all())
        self.assertTrue((nom_traces[1]['x']==traces[1]['x']).all())
        self.assertTrue((nom_traces[0]['y']==traces[0]['y']).all())
        self.assertTrue((nom_traces[1]['y']==traces[1]['y']).all())

    def test_plot_aperture(self):

        vis, traces = plot_aperture(self.data, 'v')

        np.testing.assert_array_equal(vis, np.array([True, True, False, False]))
        self.assertEqual(len(traces), 4)

        self.assertEqual(traces[0]['text'][50], 'MQXA.1R1..45')
        self.assertEqual(traces[1]['text'][50], 'MQXA.1R1..45')
        self.assertEqual(traces[2]['text'][50], 'MQXA.1R1..84')
        self.assertEqual(traces[3]['text'][50], 'MQXA.1R1..84')

        self.assertAlmostEqual(traces[0]['y'][100], 0.02385, 10)
        self.assertAlmostEqual(traces[2]['y'][100], 0.02385, 10)

        self.assertTrue((traces[0]['y']==-traces[1]['y']).all())
        self.assertTrue((traces[2]['y']==-traces[3]['y']).all())
        self.assertTrue((traces[0]['x']==traces[1]['x']).all())
        self.assertTrue((traces[2]['x']==traces[3]['x']).all())

        vis, traces = plot_aperture(self.data, 'h')

        np.testing.assert_array_equal(vis, np.array([True, True, False, False]))
        self.assertEqual(len(traces), 4)

        self.assertEqual(traces[0]['text'][50], 'MQXA.1R1..45')
        self.assertEqual(traces[1]['text'][50], 'MQXA.1R1..45')
        self.assertEqual(traces[2]['text'][50], 'MQXA.1R1..84')
        self.assertEqual(traces[3]['text'][50], 'MQXA.1R1..84')

        self.assertAlmostEqual(traces[0]['y'][100], 0.01895, 10)
        self.assertAlmostEqual(traces[2]['y'][100], 0.01895, 10)

        self.assertTrue((traces[0]['y']==-traces[1]['y']).all())
        self.assertTrue((traces[2]['y']==-traces[3]['y']).all())
        self.assertTrue((traces[0]['x']==traces[1]['x']).all())
        self.assertTrue((traces[2]['x']==traces[3]['x']).all())


if __name__ == '__main__':
    unittest.main()