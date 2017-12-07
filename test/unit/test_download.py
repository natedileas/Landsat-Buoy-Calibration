from buoycalib import download
import unittest
import os
import netCDF4
import skimage.io

class TestDownload(unittest.TestCase):

    def test_good_ftp(self):
        """ Test good ftp / test narr download """
        url = 'ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/air.199611.nc'
        save_loc = '.'
        save_loc__ = download.url_download(url, save_loc)
        ds = netCDF4.Dataset(save_loc__)
        os.remove(save_loc__)
        self.assertTrue(True)

    def test_good_http_with_auth(self):
        """ Test good http with auth / test merra download """
        url = 'https://goldsmr5.sci.gsfc.nasa.gov/data/s4pa/MERRA2/M2I3NPASM.5.12.4/2014/04/MERRA2_400.inst3_3d_asm_Np.20140401.nc4'
        username = "nid4986"
        password = "Anamorph1c"
        save_loc = '.'
        save_loc__ = download.url_download(url, save_loc, auth=(username, password))
        ds = netCDF4.Dataset(save_loc__)
        os.remove(save_loc__)
        self.assertTrue(True)

    def test_good_http(self):
        """ Test good http / test landsat download from aws """
        url = 'https://landsat-pds.s3.amazonaws.com/c1/L8/139/045/LC08_L1TP_139045_20170304_20170316_01_T1/LC08_L1TP_139045_20170304_20170316_01_T1_B8.TIF'
        save_loc = '.'
        save_loc__ = download.url_download(url, save_loc)
        image = skimage.io.imread(save_loc__)
        os.remove(save_loc__)
        self.assertTrue(True)

    def test_bad_ftp(self):
        self.fail("Not implemented yet")

    def test_bad_http(self):
        self.fail("Not implemented yet")
        
    def test_bad_auth(self):
        self.fail("Not implemented yet")
        
    def test_bad_url(self):
        self.fail("Not implemented yet")
    
