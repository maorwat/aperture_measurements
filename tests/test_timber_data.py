import unittest
from datetime import datetime
import pandas as pd

from pathlib import Path
import sys
sys.path.append(str(Path.cwd().parent))

from aper_package.timber_data import BPMData, CollimatorsData

class TestTimberData(unittest.TestCase):
    
    def setUp(self):
        time = datetime(2023, 4, 21, 10, 53, 15)

    def test_BPM(self):
        pass
    
    def test_collimators(self):
        pass

if __name__ == '__main__':
    unittest.main()