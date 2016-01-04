import logging
import os
import subprocess
import sys
import datetime
import math
import re
import shutil
import NarrData
import ModeledRadProcessing


class CalCon:
    def __init__(self, ):
        self.filepath_base = os.path.realpath(__file__)
        match = re.search('/bin/BuoyCalib.pyc?', self.filepath_base)
        if match:
            self.filepath_base = self.filepath_base.replace(match.group(), '')

        self._buoy_id = None  # buoy_info call it is the actual dataset used
        self.buoy_location = None  # lat, lon
        self.buoy_temperature = None   # calculated from buoy dataset

        self.metadata = None   # landsat metadata
        
        self.modeled_temperature = None
        self.modeled_radiance = None
        self.narr_coor = None
        
        self.image_temperature = None
        self.image_radiance = None

        self.satelite = None
        self.WRS2 = None
        self.date = None
        self.version = None

        self.cloud_cover = None
        self.poi = None
        
        self.image_file_extension = 'data/landsat'
        self.output_txt = True   # option for output
        self.verbose = True   # option for command line output

    @property
    def scene_id(self):
        lid = '%s%s%sLGN%2f' % (self.satelite, self.WRS2, self.date.strftime('%Y%j'), self.version)
        print 5
        return lid

    @scene_id.setter
    def scene_id(self, new_id):
        match = re.match('L[CE][78]\d*\w\w\w0[0-5]', new_id)

        if match:
            new_id = match.group()
            self.satelite = new_id[0:3]
            self.WRS2 = new_id[3:9]
            self.date = datetime.datetime.strptime(new_id[9:16], '%Y%j')
            self.version = new_id[-2:]
            return 0

        else:
            print 'WARNING scene_id.setter: %s is the wrong format' % new_id
            return -1
        
    @property
    def buoy_id(self):
        return self._buoy_id

    @buoy_id.setter
    def buoy_id(self, new_id):
        """ check for correct format in buoy_id. """
        if new_id is not None:
            chars = ['\n', ' ', '"', '\\', '/']   # unwanted characters
            new_id = new_id.translate(None, ''.join(chars))   #rm chars
            match = re.match('\d\d\d\d\d', new_id)

            if match:   # if it matches the pattern
                self._buoy_id = match.group()
                return 0
            else:
                self._buoy_id = new_id
                print 'WARNING .buoy_id: @buoy_id.setter: the given buoy id is the wrong format'
                return -1
        else:
            self._buoy_id = None
            return 0
            
    def output(self):
        """ Output calculated values to command line or txt file. """
        if self.output_txt:
            outfile = os.path.join(self.filepath_base, 'logs/output.txt')
            header = '%21s' % (self.scene_id)
            buoy_info = ' %7s%8s%7s %4.4f' %(self.buoy_latitude, self.buoy_longitude, self.buoy_id, self.buoy_temperature)
            radiances = ' %2.6f %2.6f %2.6f %2.6f' % (self.image_radiance[0], self.modeled_radiance[0], self.image_radiance[1], self.modeled_radiance[1])
            narr_coor = ' %14s, %14s, %14s, %14s' % (self.narr_coor[0], self.narr_coor[1], self.narr_coor[2], self.narr_coor[3])
            timestamp = '   '+datetime.datetime.now().strftime('%m/%d/%y-%H:%M:%S')

            with open(outfile, 'a') as f:
                f.write(header + buoy_info + radiances + narr_coor + '\n')
        else:
            print 'Scene ID: ', self.scene_id
            if self.buoy_latitude: print 'Buoy Latitude:', self.buoy_latitude
            if self.buoy_longitude: print 'Buoy Longitde:', self.buoy_longitude
            if self.poi: print 'POI: ', self.poi
            if self.image_radiance: print 'Band 10:\n\tImage Radiance: ', self.image_radiance[0]
            if self.modeled_radiance: print '\tModeled Radiance: ', self.modeled_radiance[0]
            if self.image_radiance: print 'Band 11:\n\tImage Radiance: ', self.image_radiance[1]
            if self.modeled_radiance: print '\tModeled Radiance: ', self.modeled_radiance[1]
            print 'Absolute Temperature: ', self.buoy_temperature
        return 0

    def cleanup(self, execute=False, *args):
        """ Remove temporary files. """

        if execute is True:
            for rm_file in self.cleanup_list:
                try:
                    if os.path.exists(rm_file):
                        if os.path.isfile(rm_file):
                            os.remove(rm_file)
                        elif os.path.isdir(rm_file):
                            shutil.rmtree(rm_file)
                except OSError as e:
                    self.logger.warning('cleanup: OSError: %s: %s: %s' % (e.errno, e.strerror, rm_file))
        else:
            for add_file in args:
                self.cleanup_list.append(os.path.join(self.filepath_base, add_file))

        return 0

def download_mod_data(cc):

    print 'download_mod_data: Downloading NARR Data'

    ret_val = nd.start_download(cc)   # make call
    
    if ret_val == -1:
        print 'download_mod_data: missing wgrib issue'
        return -1

    return 0

def calc_mod_radiance(cc):
    """ calculate modeled radiance. """

    print 'calc_mod_radiance: Calculating Modeled Radiance'
    return_vals = mrp.do_processing(cc)   # make call
    
    if return_vals == -1:
        print 'calc_mod_radiance: return_vals were -1'
        return -1
    else:
        cc.modeled_radiance, cc.narr_coor = return_vals

    return 0

def download_img_data(cc):
    """ download landsat image and parse metadata. """
    import LandsatData

    print '.download_img_data: Dealing with Landsat Data'

    return_vals = ld.download(cc)   # make call

    if return_vals:   # make sure return_vals exist and are good returns
        if return_vals == -1:
            print 'WARNING .download_img_data: something went wrong'
            return -1
        else:          # otherwise, assign values
            cc.satelite = int(return_vals[0][2:3])
            cc.scene_id = return_vals[0]
            cc.metadata = return_vals[1]
            return 0
    else:
        return -1

def calc_img_radiance(cc):
    """ calculate image radiance. """
    import ImageRadProcessing

    print '.calc_img_radiance: Calculating Image Radiance'
    return_vals = irp.do_processing(cc)

    cc.image_radiance = return_vals[0]
    cc.poi = return_vals[1]
    return 0
    
def calculate_buoy_information(cc):
    """pick buoy dataset, download, and calculate skin_temp. """
    import BuoyData

    print 'calculate_buoy_information: Downloading Buoy Data'
    if not cc.metadata:
      return -1
      
    return_vals = BuoyData.start_download(cc)

    if return_vals:
        if return_vals == -1:
            return -1
        else:
            cc.buoy_id = return_vals[0]
            cc.buoy_latitude = return_vals[1][0]
            cc.buoy_longitude = return_vals[1][1]
            cc.buoy_temperature = return_vals[2]
            cc.buoy_press = return_vals[3]
            cc.buoy_airtemp = return_vals[4]
            cc.buoy_dewpnt = return_vals[5]
            return 0
    else:
        return -1

    return 0

    
