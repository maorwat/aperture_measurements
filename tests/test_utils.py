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

if __name__ == '__main__':
    unittest.main()