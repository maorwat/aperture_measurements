import unittest
import pandas as pd

from pathlib import Path
import sys
sys.path.append(str(Path.cwd().parent))

from aper_package.utils import *

class TestUtils(unittest.TestCase):

    def test_shift_by(self):
        # Set up a sample dataframe for testing
        df = pd.DataFrame({
            'S': [0, 10000, 20000, 26000, 26600]
        })

        # Test positive shift 
        shifted_df = shift_by(df.copy(), 1000, 'S')
        expected_df = pd.DataFrame({'S': [341.1168199999993, 941.1168199999993, 1000.0, 11000.0, 21000.0]}, dtype=float)
        pd.testing.assert_frame_equal(shifted_df, expected_df)

        # Test negative shift without exceeding last_value
        shifted_df = shift_by(df.copy(), -1000, 'S')
        expected_df = pd.DataFrame({'S': [9000.0, 19000.0, 25000.0, 25600.0, 25658.88318]}, dtype=float)
        pd.testing.assert_frame_equal(shifted_df, expected_df)

    def test_match_with_twiss(self):
        # Setup the sample data for twiss and aper_to_match
        twiss = pd.DataFrame({
            'name': ['bpm1', 'bpm2', 'bpm3'],
            's': [10.5, 20.3, 30.1]
        })

        aper_to_match = pd.DataFrame({
            'NAME': ['BPM1', 'BPM2', 'BPM4'],
            'APER': [0.001, 0.002, 0.003],
            'S': [40.0, 50.9, 60.7]
        })

        # Expected output after matching
        expected_df = pd.DataFrame({
            'NAME': ['BPM1', 'BPM2'],
            'APER': [0.001, 0.002],
            'S': [10.5, 20.3]
        })

        # Run the function
        result_df = match_with_twiss(twiss, aper_to_match)

        # Assert that the resulting dataframe matches the expected output
        pd.testing.assert_frame_equal(result_df, expected_df)


if __name__ == '__main__':
    unittest.main()