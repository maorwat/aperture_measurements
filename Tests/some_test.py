import unittest
import pandas as pd

from pathlib import Path
import sys
sys.path.append(str(Path.cwd().parent))

from aper_package.aperture_data import Data

class TestAperData(unittest.TestCase):

    def setUp(self):

        #TODO change the paths
        line1 = '/eos/user/m/morwat/aperture_measurements/madx/2023/xsuite/Martas_injection_b1.json'
        self.data = Data(line1 = line1)

    def test_init(self):

        self.assertEqual(self.data.gamma, 479.6050161552533)
        self.assertEqual(self.data.tw_b1.shape, (34939, 16))
        self.assertEqual(self.data.tw_b2.shape, (34963, 16))
        self.assertEqual(self.data.nom_b1.shape, (34939, 4))
        self.assertEqual(self.data.nom_b2.shape, (34963, 4))
        self.assertEqual(self.data.tw_b1['name'].iloc[0], 'ip1')
        self.assertEqual(self.data.tw_b2['name'].iloc[0], 'lhcb2ip1.l1_p_')
        self.assertEqual(self.data.nom_b1['name'].iloc[0], 'ip1')
        self.assertEqual(self.data.nom_b2['name'].iloc[0], 'lhcb2ip1.l1_p_')

        self.assertTrue((self.data.tw_b1['x_from_nom_to_top'] == 0).all())
        self.assertTrue((self.data.tw_b1['x_from_nom_to_bottom'] == 0).all())
        self.assertTrue((self.data.tw_b2['x_from_nom_to_top'] == 0).all())
        self.assertTrue((self.data.tw_b2['x_from_nom_to_bottom'] == 0).all())

        self.assertTrue((self.data.tw_b1['y_from_nom_to_top'] == 0).all())
        self.assertTrue((self.data.tw_b1['y_from_nom_to_bottom'] == 0).all())
        self.assertTrue((self.data.tw_b2['y_from_nom_to_top'] == 0).all())
        self.assertTrue((self.data.tw_b2['y_from_nom_to_bottom'] == 0).all())

    def test_aperture(self):

        path1 = '/eos/user/m/morwat/aperture_measurements/madx/2023/all_optics_B1.tfs'
        self.data.load_aperture()

        # Convert names to lower case for case-insensitive comparison
        self.data.aper_b2['NAME'] = self.data.aper_b2['NAME'].str.lower()

        # Merge the dataframes on the name columns
        merged_df = pd.merge(self.data.aper_b2, self.data.tw_b2, left_on='NAME', right_on='name')

        # Check for equality of the 'S' and 's' columns
        pd.testing.assert_series_equal(merged_df['S'], merged_df['s'], check_names=False)


    @unittest.skipIf(True, 'no reason')
    def test_aperture(self):
        pass

    @unittest.skipUnless(False, 'because')
    def test_cycle(self):
        pass

if __name__ == '__main__':
    unittest.main()