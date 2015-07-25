import logging
import os
import subprocess
import sys
import datetime
import math


class ModeledRadiance(object):
    def __init__(self):
        self.modeled_temperature = []   # empty array for modeled temps
        self.modeled_radiance = []   # empty array for modeled radiances

    def download_mod_data(self):
        """launcher for NarrData.start_download().
        """

        import NarrData

        self.logger.info('download_mod_data: Downloading NARR Data')

        nd = NarrData.NarrData(self)   # initialize
        ret_val = nd.start_download()   # make call
        if ret_val == -1:
            return -1
        CalibrationController.cleanup(self, False, 'data/narr/HGT_1',
                                     'data/narr/HGT_2', 'data/narr/SHUM_1',
                                     'data/narr/SHUM_2', 'data/narr/TMP_1',
                                     'data/narr/TMP_2')
        return 0

    def calc_mod_radiance(self):
        """Calculate  modeled band 10 and 11 radiance.

        Launcher for ModeledRadProcessing.do_processing().
        """

        import ModeledRadProcessing

        self.logger.info('calc_mod_radiance: Calculating Modeled Radiance')

        mrp = ModeledRadProcessing.ModeledRadProcessing(self)   # initialize
        return_vals = mrp.do_processing()   # make call
        
        if return_vals == -1:
            self.logger.info('calc_mod_radiance: return_vals were -1')
            return -1
        else:
            self.modeled_radiance, caselist = return_vals

            CalibrationController.cleanup(self, False, 'data/modtran/newHead.txt',
                                          'data/modtran/newHead2.txt', 'data/modtran/newHead3.txt',
                                          'data/modtran/newHead4.txt', 'data/modtran/tempLayers.txt',
                                          'data/modtran/newTail.txt', 'data/modtran/newTail2.txt',
                                          'data/modtran/newTail3.txt', 'data/modtran/newTail5.txt',
                                          'data/modtran/newTail4.txt', 'data/modtran/newTail6.txt',)
        return 0


class SensorRadiance(object):
    def __init__(self):
        self.image_temperature = []   # empty array for image temp (from rad)
        self.image_radiance = []   # empty array for image radaiances

        self._scene_id = None   # landsat id

        self.satelite = None   # landsat version: format: 8 or 7
        self.WRS2_path = None   # path for landsat id construction
        self.WRS2_row = None   # row for landsat id construction
        self.year = None   # year for landsat id construction
        self.julian_date = None   # day of year, for landsat id construction

        # TODO check implementation
        self.cloud_cover = None  # cloud cover, optional argument

        self.poi = None   # pixel of interest, assigned from calc_rad call

    @property
    def scene_id(self):
        return self._scene_id

    @scene_id.setter
    def scene_id(self, new_id):
        if new_id is not None:
            import re
            chars = ['\n', ' ', '"', '\\', '/']   # unwanted characters
            new_id = new_id.translate(None, ''.join(chars))
            match = re.match('L[CE][78]\d*\w\w\w0[0-5]', new_id)

            if match:   # if it matches the pattern
                self._scene_id = match.group()
                return 0
            else:
                self._scene_id = new_id
                self.logger.warning('.scene_id: @scene_id.setter: \
                                    the given landsat id is the wrong format')
                return -1
        else:
            self._scene_id = None
            return 0

    def download_img_data(self):
        """launcher for LandsatData.start_download().
        """

        import LandsatData

        self.logger.info('.download_img_data: Dealing with Landsat Data')

        ld = LandsatData.LandsatData(self)   # initialize
        return_vals = ld.start_download()   # make call

        if return_vals:   # make sure return_vals exist and are good returns
            if return_vals == -1:
                self.logger.warning('.download_img_data: something went wrong')
                return -1
            else:          # otherwise, assign values
                self.satelite = int(return_vals[0][2:3])
                self.scene_id = return_vals[0]
                self.metadata = return_vals[1]
                return 0
        else:
            return -1

    def calc_img_radiance(self):
        """Launcher for ImageRadProcessing.do_processing().

        Depends on a BuoyData call and a LandsatData call.
        Functions: calculate_buoy_information, download_img_data.
        """

        import ImageRadProcessing

        self.logger.info('.calc_img_radiance: Calculating Image Radiance')
        irp = ImageRadProcessing.ImageRadProcessing(self)
        return_vals = irp.do_processing()

        self.image_radiance = return_vals[0]
        self.poi = return_vals[1]
        return 0


class CalibrationController(ModeledRadiance, SensorRadiance):
    def __init__(self):
        logging.basicConfig(filename='./logs/CalibrationController.log',
                            filemode='w', level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # buoy id- assigned by user initially, after
        self.buoy_id = None  # buoy_info call it is the actual dataset used
        self.buoy_latitude = None  # calculated from stationtable.txt
        self.buoy_longitude = None   # calculated from stationtable.txt
        self.buoy_temperature = None   # calculated from buoy dataset

        self.metadata = None   # landsat metadata

        self.output_txt = True   # option to for output
        self.verbose = False   # option for command line output

        self.filepath_base = os.getcwd()   # standardize file paths in modules
        self.cleanup_list = ['data/modtran/points']   # list of files to remove

        ModeledRadiance.__init__(self)   # initializers to utilize attributes
        SensorRadiance.__init__(self)    # from parent classes

    def calculate_buoy_information(self):
        """Launcher for BuoyData.start_download, does all buoy calculations.
        """

        import BuoyData

        self.logger.info('calculate_buoy_information: Downloading Buoy Data')
        bd = BuoyData.BuoyData(self)
        return_vals = bd.start_download()

        if return_vals:
            if return_vals == -1:
                sys.exit()
            else:
                self.buoy_id = return_vals[0]
                self.buoy_latitude = return_vals[1][0]
                self.buoy_longitude = return_vals[1][1]
                self.buoy_temperature = return_vals[2]
                self.cleanup_list.append('data/buoy/station_table.txt')
                return 0
        else:
            return -1

        return 0

    def calc_brightness_temperature(self):
        """translate radiance to temperature.

        Depends on image_radiance, modeled_radiance being calculated already.
        """

        K1 = self.metadata['K1_CONSTANT_BAND_10'], \
             self.metadata['K1_CONSTANT_BAND_11']
        K2 = self.metadata['K2_CONSTANT_BAND_10'], \
             self.metadata['K2_CONSTANT_BAND_11']

        for i in range(2):
            Timg = K2[i] / math.log((K1[i] / self.image_radiance[i]) + 1)
            Tmod = K2[i] / math.log((K1[i] / self.modeled_radiance[i]) + 1)

            self.image_temperature.append(Timg)
            self.modeled_temperature.append(Tmod)

        return 0

    def output(self):
        """Output calculated values to command line or txt file.
        """

        if self.output_txt:
            outfile = './logs/output.txt'
            #other = '%21s%7s%10s%7s' % (self.scene_id, self.buoy_latitude, self.buoy_longitude, self.buoy_id)
            radiances = ' %2.6f %2.6f %2.6f %2.6f' % (self.image_radiance[0], self.modeled_radiance[0], self.image_radiance[1], self.modeled_radiance[1])
            buoy_temp = ' %4.4f' % float(self.buoy_temperature)
            #timestamp = '   '+datetime.datetime.now().strftime('%m/%d/%y-%H:%M:%S')

            with open(outfile, 'a') as f:
                f.write(radiances + buoy_temp + '\n')
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
        """Remove temporary files.
        """

        import shutil

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
                self.cleanup_list.append(add_file)

        return 0
