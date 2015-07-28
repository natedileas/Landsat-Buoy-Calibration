import logging
import os
import subprocess
import sys
import datetime
import math
import re


class ModeledRadiance(object):
    """ Attributes and methods to calculate the modeled radiance.
    
    Attributes:
        modeled_temperature: empty array for modeled temperatures, list
        modeled_radiance: empty array for modeled radiances, list
    
    Methods:
        __init__(self): initializes the object.
        download_mod_data(self): launcher for NarrData.start_download(),
            downloads NARR data.
            Returns: 0 if good, -1 if bad
        calc_mod_radiance(self): Calculate  modeled band 10 and 11 radiance.
            Launcher for ModeledRadProcessing.do_processing().
            Returns: 0 if good, -1 if bad
            
    Intended to be subclassed, but can be used alone.
    """
    def __init__(self):
        """ initialize the object. """
        self.modeled_temperature = []
        self.modeled_radiance = []

    def download_mod_data(self):
        """ doenload NARR data. """
        import NarrData

        self.logger.info('download_mod_data: Downloading NARR Data')

        nd = NarrData.NarrData(self)   # initialize
        ret_val = nd.start_download()   # make call
        if ret_val == -1:
            return -1
        self.cleanup(False, 'data/narr/HGT_1', 'data/narr/HGT_2', 
                            'data/narr/SHUM_1', 'data/narr/SHUM_2', 
                            'data/narr/TMP_1', 'data/narr/TMP_2')
        return 0

    def calc_mod_radiance(self):
        """ calculate modeled radiance. """
        import ModeledRadProcessing

        self.logger.info('calc_mod_radiance: Calculating Modeled Radiance')

        mrp = ModeledRadProcessing.ModeledRadProcessing(self)   # initialize
        return_vals = mrp.do_processing()   # make call
        
        if return_vals == -1:
            self.logger.info('calc_mod_radiance: return_vals were -1')
            return -1
        else:
            self.modeled_radiance, caselist = return_vals

            self.cleanup(False, 'data/modtran/newHead.txt', 
                         'data/modtran/newHead2.txt', 'data/modtran/newHead3.txt',
                         'data/modtran/newHead4.txt', 'data/modtran/tempLayers.txt',
                         'data/modtran/newTail.txt', 'data/modtran/newTail2.txt',
                         'data/modtran/newTail3.txt', 'data/modtran/newTail5.txt',
                         'data/modtran/newTail4.txt', 'data/modtran/newTail6.txt',)
        return 0


class SensorRadiance(object):
    """ Attributes and methods to calculate the sensor radiance.
    
    Attributes:
        image_temperature: empty array for image temperature, list
        image_radiance: empty array for image radaiances, list
        _scene_id: landsat id, has setter and getter, string
        satelite: landsat version, options(8, 7), int
        WRS2_path: path for landsat id construction, string
        WRS2_row: row for landsat id construction, string
        year: year for landsat id construction, string
        julian_date: day of year, for landsat id construction, string
        cloud_cover: cloud cover, optional argument, range(0-100), string
        poi: pixel of interest, assigned from calc_rad call, list
    
    Methods:
        __init__(self): initializes the object.
        scene_id(self): getter, returns: self._scene_id.
        scene_id(self, new_id): setter, checks for proper format.
        download_img_data(self): download image data for the appropriate 
            scene_id or parts whereof.
        calc_img_radiance(self): calculate image radiance, launcher for 
            LandsatData.start_download().
        download_img_data(self): Launcher for ImageRadProcessing.do_processing
            , depends on a BuoyData call and a LandsatData call.
            Returns: self.image_radiance.
            
    Intended to be subclassed, but can be used alone.
    """
    def __init__(self):
        """ initialize the object. """
        self.image_temperature = []
        self.image_radiance = []

        self._scene_id = None

        self.satelite = None
        self.WRS2_path = None
        self.WRS2_row = None
        self.year = None
        self.julian_date = None

        self.cloud_cover = None
        self.poi = None

    @property
    def scene_id(self):
        return self._scene_id

    @scene_id.setter
    def scene_id(self, new_id):
        """ check for correct format in landsat id. """
        if new_id is not None:
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
        """ download landsat image and parse metadata. """
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
        """ calculate image radiance. """
        import ImageRadProcessing

        self.logger.info('.calc_img_radiance: Calculating Image Radiance')
        irp = ImageRadProcessing.ImageRadProcessing(self)
        return_vals = irp.do_processing()

        self.image_radiance = return_vals[0]
        self.poi = return_vals[1]
        return 0


class CalibrationController(ModeledRadiance, SensorRadiance):
    """ Provides wrappers for BuoyData, cleanup, and output functionality.
    
    Attributes:
        filepath_base: smart path object.
        self.logger: logging object used by super and sub classes.
        _buoy_id: assigned by user initially, after buoy_info call it is the
            actual dataset used, int
        buoy_latitude: calculated from stationtable.txt, float
        buoy_longitude: calculated from stationtable.txt, float
        buoy_temperature: calculated from buoy dataset, float
        metadata: landsat metadata, dict
        output_txt: option to for output, string
        verbose: option for command line output, int
        cleanup_list: files to remove, list
        
    Methods:
        __init__(self): initialize the object
        buoy_id(self): getter
        buoy_id(self, new_id): setter, check for correct format
        calculate_buoy_information(self): Launcher for BuoyData.start_download,
             does all buoy calculations.
        calc_brightness_temperature(self): Depends on image_radiance
             and modeled_radiance being calculated already, will return -1 if
             not.
        output(self): Output calculated values to command line or txt file.
        cleanup(self, execute=False, *args): remove temporary files, if
            execute is false then append input args to the list. 
        
    Subclasses ModeledRadiance and SensorRadiance.
    """
    def __init__(self):
        """ initialize the object. """
        # standardize file paths in modules
        self.filepath_base = os.path.realpath(__file__)
        match = re.search('/bin/BuoyCalib.pyc?', self.filepath_base)
        if match:
            self.filepath_base = self.filepath_base.replace(match.group(), '')

        log_file = os.path.join(self.filepath_base, 'logs/CalibrationController.log')
        logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # buoy id- assigned by user initially, after
        self._buoy_id = None  # buoy_info call it is the actual dataset used
        self.buoy_latitude = None  # calculated from stationtable.txt
        self.buoy_longitude = None   # calculated from stationtable.txt
        self.buoy_temperature = None   # calculated from buoy dataset

        self.metadata = None   # landsat metadata

        self.output_txt = True   # option to for output
        self.verbose = False   # option for command line output
        
        self.cleanup_list = ['data/modtran/points']   # list of files to remove

        ModeledRadiance.__init__(self)   # initializers to utilize attributes
        SensorRadiance.__init__(self)    # from parent classes
        
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
                self.logger.warning('.buoy_id: @buoy_id.setter: \
                                    the given buoy id is the wrong format')
                return -1
        else:
            self._buoy_id = None
            return 0

    def calculate_buoy_information(self):
        """pick buoy dataset, download, and calculate skin_temp. """
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
        """ translate radiance to temperature. """

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
        """ Output calculated values to command line or txt file. """
        if self.output_txt:
            outfile = os.path.join(self.filepath_base, 'logs/output.txt')
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
        """ Remove temporary files. """
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
                self.cleanup_list.append(os.path.join(self.filepath_base, add_file))

        return 0
