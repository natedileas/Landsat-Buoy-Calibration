import unittest

import sys
import os.path as path
sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

import landsatbuoycalib.BuoyCalib as bc

LID = 'LC80130332013145LGN00'

class TestLandsatBuoyCalib_NARR(unittest.TestCase):
    def setUp(self):
        self.cc = bc.CalibrationController(LID, None, verbose=False, atmo_src='narr')

class TestLandsatBuoyCalib_MERRA(unittest.TestCase):
    def setUp(self):
        self.cc = bc.CalibrationController(LID, None, verbose=False, atmo_src='merra')

