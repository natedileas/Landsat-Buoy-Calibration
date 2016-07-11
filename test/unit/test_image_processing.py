import unittest
from test_landsatbuoycalib import TestLandsatBuoyCalib_NARR as TestLandsatBuoyCalib
from landsatbuoycalib import image_processing as img_proc


class TestCalcDCAVG(unittest.TestCase):

    def test_calc_dc_avg_in_range(self):
        img_file = '/cis/ugrad/nid4986/Landsat-Buoy-Calibration/test/unit/assets/LC80410372013149LGN00_B10.TIF'

        dc_avg = img_proc.calc_dc_avg(img_file, (3400, 4000))
        self.assertEqual(dc_avg, 23530.0)

    def test_calc_dc_avg_out_of_range(self):
        img_file = '/cis/ugrad/nid4986/Landsat-Buoy-Calibration/test/unit/assets/LC80410372013149LGN00_B10.TIF'

        self.assertRaises(img_proc.OutOfRangeError, img_proc.calc_dc_avg, img_file, (0,1231231))

class TestConvertUTMZones(unittest.TestCase):

    def test_convert_utm_zones_up_one(self):
        import utm
        lt = 33.1; ln= -119.3
        utm_proj = utm.from_latlon(lt, ln)
        new_proj = img_proc.convert_utm_zones(utm_proj[0], utm_proj[1], 11, 12)

        self.assertEqual(new_proj, (-275574.0852502306, 3693181.559160657))

    def test_convert_utm_zones_down_one(self):
        import utm
        lt = 33.1; ln= -119.3
        utm_proj = utm.from_latlon(lt, ln)
        new_proj = img_proc.convert_utm_zones(utm_proj[0], utm_proj[1], 11, 10)

        self.assertEqual(new_proj, (845345.7168345955, 3668467.6168501354))

    def test_convert_utm_zones_negative_zone(self):
        import utm
        lt = 33.1; ln= -119.3
        utm_proj = utm.from_latlon(lt, ln)

        self.assertRaises(img_proc.OutOfRangeError, img_proc.convert_utm_zones, utm_proj[0], utm_proj[1], 11, -4)

    def test_convert_utm_zones_zone_too_big(self):
        import utm
        lt = 33.1; ln= -119.3
        utm_proj = utm.from_latlon(lt, ln)

        self.assertRaises(img_proc.OutOfRangeError, img_proc.convert_utm_zones, utm_proj[0], utm_proj[1], 112312, 12)


class TestFindROI(unittest.TestCase):
    """
    Test the find_roi function in image_processing.

    Tests include numerical checking and out-of-range lat/lon pairs.
    """

    def test_find_roi_in_range(self):
        """
        Check if lat/lon pairs inside the image give expected results.

        "Ground truth" values generated from envi.
        """
        img_file = '/cis/ugrad/nid4986/Landsat-Buoy-Calibration/test/unit/assets/LC80410372013149LGN00_B10.TIF'
        lat = 33.3123; lon = -119.1221; zone = 11
        actual_x = 2652; actual_y = 3199
        
        x, y = img_proc.find_roi(img_file, lat, lon, zone)

        self.assertEqual(x, actual_x)
        self.assertEqual(y, actual_y)
        
    def test_find_roi_out_of_range(self):
        """
        Check to see if function fails graciously when given lat/lon pair outside of image.
        """
        img_file = '/cis/ugrad/nid4986/Landsat-Buoy-Calibration/test/unit/assets/LC80410372013149LGN00_B10.TIF'
        lat = 33.3123; lon = -60.0; zone = 11

        self.assertRaises(img_proc.OutOfRangeError, img_proc.find_roi, img_file, lat, lon, zone)


class TestDCToRad(unittest.TestCase):
    """
    Test the method dc_to_rad in image_processing.

    Tests include numerical testing for all satelites and bands, plus out of range 
    digital count checking.
    """

    def test_dc_to_rad_L8_B10(self):
        metadata = {'RADIANCE_ADD_BAND_10':0.1, 'RADIANCE_MULT_BAND_10':3.342e-04, 'QUANTIZE_CAL_MAX_BAND_10':65535}

        self.assertEqual(img_proc.dc_to_rad('LC8', 10, metadata, 20000), 6.784)

    def test_dc_to_rad_L8_B11(self):
        metadata = {'RADIANCE_ADD_BAND_11':0.1, 'RADIANCE_MULT_BAND_11':3.342e-04, 'QUANTIZE_CAL_MAX_BAND_10':65535}
        
        self.assertEqual(img_proc.dc_to_rad('LC8', 11, metadata, 32000), 10.7944)

    def test_dc_to_rad_L7(self):
        metadata = {'RADIANCE_ADD_BAND_6_VCID_2':3.16280, 'RADIANCE_MULT_BAND_6_VCID_2':0.037, 'QUANTIZE_CAL_MAX_BAND_6_VCID_2':255}
        dc = 100
        self.assertEqual(img_proc.dc_to_rad('LE7', 6, metadata, dc), 6.8628)

    def test_dc_to_rad_L5(self):
        metadata = {'RADIANCE_ADD_BAND_6':1.18243, 'RADIANCE_MULT_BAND_6':0.055, 'QUANTIZE_CAL_MAX_BAND_6':255}
        dc = 100

        self.assertEqual(img_proc.dc_to_rad('LT5', 6, metadata, dc), 6.68243)

    def test_out_of_range(self):
        metadata = {'RADIANCE_ADD_BAND_10':0.1, 'RADIANCE_MULT_BAND_10':3.342e-04, 'QUANTIZE_CAL_MAX_BAND_10':65535}
        dc = 9102380

        self.assertRaises(img_proc.OutOfRangeError, img_proc.dc_to_rad, 'LC8', 10, metadata, dc)

