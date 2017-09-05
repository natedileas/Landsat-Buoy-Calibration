import unittest
from buoycalib import landsat


class TestLandsat(unittest.TestCase):

    def test_parse_scene_landsat_archive(self):
        scene = landsat.parse_scene('LC80130332013145LCN00')
        self.assertEqual(scene['sat'], 'L8')
        self.assertEqual(scene['path'], '013')
        self.assertEqual(scene['row'], '033')

    def test_parse_scene_landsat_collection1(self):
        scene = landsat.parse_scene('LC08_L1GT_013033_20130525_20170310_01_T2')
        self.assertEqual(scene['sat'], 'c1/L8')
        self.assertEqual(scene['path'], '013')
        self.assertEqual(scene['row'], '033')
