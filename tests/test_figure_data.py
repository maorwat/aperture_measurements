import unittest
import pandas as pd
import numpy as np

from pathlib import Path
import sys

home_path = str(Path.cwd().parent)
sys.path.append(home_path)

from aper_package.aperture_data import ApertureData
from aper_package.figure_data import *

class TestPlotting(unittest.TestCase):
    
    def setUp(self):

        line = home_path+'/test_data/Martas_injection_b1.json'
        self.data = ApertureData(line)
        path = home_path+'/test_data/all_optics_B1.tfs'
        self.data.load_aperture(path)


    def test_plot_envelopes(self):

        vis, traces = plot_envelopes(self.data, 'horizontal')

        np.testing.assert_array_equal(vis, np.array([True, True, False, False]))
        self.assertEqual(len(traces), 4)

        self.assertAlmostEqual(traces[0]['x'][0], 0, 10)
        self.assertAlmostEqual(traces[0]['x'][-1], 26658.88317687314, 10)
        self.assertAlmostEqual(traces[0]['y'][0], -0.002000142862473192, 10)
        self.assertAlmostEqual(traces[0]['y'][-1], -0.0020001428624731817, 10)

        self.assertEqual(len(traces[0]['x']), self.data.tw_b1.shape[0])
        self.assertEqual(len(traces[1]['x']), self.data.tw_b1.shape[0])
        self.assertEqual(len(traces[2]['y']), self.data.tw_b2.shape[0])
        self.assertEqual(len(traces[3]['y']), self.data.tw_b2.shape[0])

        vis, traces = plot_envelopes(self.data, 'vertical')

        np.testing.assert_array_equal(vis, np.array([True, True, False, False]))
        self.assertEqual(len(traces), 4)

        self.assertAlmostEqual(traces[0]['y'][0], -2.1961356293530347e-09, 10)
        self.assertAlmostEqual(traces[0]['y'][-1], -2.1961356297416947e-09, 10)

        self.assertEqual(len(traces[0]['x']), self.data.tw_b1.shape[0])
        self.assertEqual(len(traces[1]['x']), self.data.tw_b1.shape[0])
        self.assertEqual(len(traces[2]['y']), self.data.tw_b2.shape[0])
        self.assertEqual(len(traces[3]['y']), self.data.tw_b2.shape[0])

    def test_plot_beam_positions(self):

        vis, traces = plot_beam_positions(self.data, 'horizontal')

        np.testing.assert_array_equal(vis, np.array([True, False]))
        self.assertEqual(len(traces), 2)

        self.assertAlmostEqual(traces[0]['x'][1000], 261.1706666666666, 10)
        self.assertAlmostEqual(traces[1]['x'][1000], 264.08433171133584, 10)
        self.assertAlmostEqual(traces[0]['y'][1000], 9.474557711656808e-07, 10)
        self.assertAlmostEqual(traces[1]['y'][1000], -1.2460130805535723e-07, 10)

        nom_vis, nom_traces = plot_beam_positions(self.data, 'horizontal')

        self.assertTrue((nom_traces[0]['x']==traces[0]['x']).all())
        self.assertTrue((nom_traces[1]['x']==traces[1]['x']).all())
        self.assertTrue((nom_traces[0]['y']==traces[0]['y']).all())
        self.assertTrue((nom_traces[1]['y']==traces[1]['y']).all())

        vis, traces = plot_beam_positions(self.data, 'vertical')

        np.testing.assert_array_equal(vis, np.array([True, False]))
        self.assertEqual(len(traces), 2)

        self.assertAlmostEqual(traces[0]['y'][2000], -2.5213925117160937e-07, 10)
        self.assertAlmostEqual(traces[1]['y'][2000], 1.3734680420729657e-07, 10)

        nom_vis, nom_traces = plot_beam_positions(self.data, 'vertical')

        self.assertTrue((nom_traces[0]['x']==traces[0]['x']).all())
        self.assertTrue((nom_traces[1]['x']==traces[1]['x']).all())
        self.assertTrue((nom_traces[0]['y']==traces[0]['y']).all())
        self.assertTrue((nom_traces[1]['y']==traces[1]['y']).all())

    def test_plot_aperture(self):

        vis, traces = plot_aperture(self.data, 'vertical')

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

        vis, traces = plot_aperture(self.data, 'horizontal')

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