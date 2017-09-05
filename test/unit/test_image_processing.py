import unittest

from buoycalib import image_processing as img

TEST_IMAGE = 'test/unit/assets/LC80410372013149LGN00_B10.TIF'


class TestCalcDCAVG(unittest.TestCase):

    def test_calc_dc_avg_in_range(self):
        dc_avg = img.calc_dc_avg(TEST_IMAGE, (3400, 4000))
        self.assertEqual(dc_avg, 23530.0)

    def test_calc_dc_avg_out_of_range(self):
        self.assertRaises(img.OutOfRangeError, img.calc_dc_avg, TEST_IMAGE, (0, 1231231))


class TestConvertUTMZones(unittest.TestCase):

    def test_convert_utm_zones_up_one(self):
        import utm
        lt = 33.1; ln = -119.3
        utm_proj = utm.from_latlon(lt, ln)
        new_proj = img.convert_utm_zones(utm_proj[0], utm_proj[1], 11, 12)

        self.assertEqual(new_proj, (-275574.0852502306, 3693181.559160657))

    def test_convert_utm_zones_down_one(self):
        import utm
        lt = 33.1; ln = -119.3
        utm_proj = utm.from_latlon(lt, ln)
        new_proj = img.convert_utm_zones(utm_proj[0], utm_proj[1], 11, 10)

        self.assertEqual(new_proj, (845345.7168345955, 3668467.6168501354))

    def test_convert_utm_zones_negative_zone(self):
        import utm
        lt = 33.1; ln= -119.3
        utm_proj = utm.from_latlon(lt, ln)

        self.assertRaises(img.OutOfRangeError, img.convert_utm_zones, utm_proj[0], utm_proj[1], 11, -4)

    def test_convert_utm_zones_zone_too_big(self):
        import utm
        lt = 33.1; ln= -119.3
        utm_proj = utm.from_latlon(lt, ln)

        self.assertRaises(img.OutOfRangeError, img.convert_utm_zones, utm_proj[0], utm_proj[1], 112312, 12)


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
        lat = 33.3123; lon = -119.1221; zone = 11
        actual_x = 2652; actual_y = 3199

        x, y = img.find_roi(TEST_IMAGE, lat, lon, zone)

        self.assertEqual(x, actual_x)
        self.assertEqual(y, actual_y)

    def test_find_roi_out_of_range(self):
        """
        Check to see if function fails graciously when given lat/lon pair outside of image.
        """
        lat = 33.3123; lon = -60.0; zone = 11

        self.assertRaises(img.OutOfRangeError, img.find_roi, TEST_IMAGE, lat, lon, zone)
