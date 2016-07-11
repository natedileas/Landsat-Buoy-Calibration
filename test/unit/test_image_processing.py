import unittest
from test_landsatbuoycalib import TestLandsatBuoyCalib_NARR as TestLandsatBuoyCalib
from landsatbuoycalib import image_processing as img_proc

class TestImageProcessingFuncs(TestLandsatBuoyCalib):
    def test_calc_radiance(self):
        self.fail('Yet to be implemented')

    def test_find_roi(self):
        self.fail('Yet to be implemented')

    def test_convert_utm_zones(self):
        self.fail('Yet to be implemented')

    def test_calc_dc_avg(self):
        self.fail('Yet to be implemented')

    def test_dc_to_rad(self):
        metadata = {'RADIANCE_ADD_BAND_10':0.1, 'RADIANCE_MULT_BAND_10':3.342e-04, 'RADIANCE_ADD_BAND_11':0.1, 'RADIANCE_MULT_BAND_11':3.342e-04,\
                    'RADIANCE_ADD_BAND_6_VCID_2':3.16280, 'RADIANCE_MULT_BAND_6_VCID_2':0.037, \
                    'RADIANCE_ADD_BAND_6':1.18243, 'RADIANCE_MULT_BAND_6':0.055}
        dc = 100

        self.assertEqual(img_proc.dc_to_rad('LC8', 10, metadata, 20000), 6.784)
        self.assertEqual(img_proc.dc_to_rad('LC8', 11, metadata, 32000), 10.7944)

        self.assertEqual(img_proc.dc_to_rad('LE7', 6, metadata, dc), 6.8628)

        self.assertEqual(img_proc.dc_to_rad('LT5', 6, metadata, dc), 6.68243)


