import datetime
import logging
import os
import sys
import re
import subprocess

import numpy

import modeled_processing as mod_proc
import image_processing as img_proc
import buoy_data
import landsat_data
import narr_data
import merra_data

class CalibrationController(object):
    """
    Attributes:

        buoy_id: NOAA Buoy ID, e.g. 44009, 41008, 46025
        buoy_location: location of buoy [lat, lon]
        skin_temp: skin temperature at buoy
        buoy_press: pressure at buoy
        buoy_airtemp: air temperature at buoy
        buoy_dewpnt: dewpoint temperature at buoy
        
        modeled_radiance: radiance(s) calculated from NARR or MERRA data and MODTRAN
        narr_coor: coordinates of atmospheric data points

        image_radiance: radiance(s) calculated from landsat image(s) and metadata
        metadata: landsat product metadata
        scenedatetime:
        poi:
        
        scene_id: Landsat Product ID e.g. LC80130332013145LGN00
            This attribute is assembled from the below elements.
        satelite: Landsat Satelite idenitfier, e.g. LC8, LE7, LT5
        wrs2: WRS2 coordinates PTHROW, e.g. 013033, 037041
        date: date of overpass, year and day of year, e.g. 2013145, 2014003
        station: station to which the image was transmitted, e.g. LGN, EDC
        version: version of image that is stored, e.g. 00, 04, etc.
                
        filepath_base:
        data_base: 
        scene_dir: Directory in which landsat images are stored
        
        atmo_src: Either 'narr' or 'merra', indicates which atmospheric data source to use
    """
    def __init__(self, LID, BID=None, DIR='/dirs/home/ugrad/nid4986/landsat_data/', atmo_src='narr', verbose=False):
        """
        Args:
            LID: Landsat product ID, see scene_id above
            BID: NOAA buoy ID, see buoy_id above
            DIR: base of data storage directory
            atmo_src: see above
            verbose: if true, output to stdout, otherwise log to file
        """
        
        # buoy and related attributes
        self._buoy_id = None
        self.buoy_location = None  # [lat, lon]
        self.skin_temp = None   # calculated from buoy dataset
        self.buoy_press = None
        self.buoy_airtemp = None
        self.buoy_dewpnt = None
        
        # modeled radiance and related attributes
        self.modeled_radiance = []
        self.narr_coor = None
        
        # image radiance and related attributes
        self.image_radiance = []
        self.metadata = None    # landsat metadata
        self.scenedatetime = None 
        self.poi = None
        
        # attributes that make up the lansat id
        self.satelite = None
        self.wrs2 = None
        self.date = None
        self.station = None
        self.version = None

        self.scene_id = LID
                
        self.filepath_base = os.path.realpath(os.path.join(__file__, '../..'))
        self.data_base = os.path.realpath(DIR)
        self.scene_dir = os.path.realpath(os.path.join(DIR, 'landsat_scenes', LID))
        
        self.atmo_src = atmo_src

        if not os.path.exists(self.scene_dir):
            os.makedirs(self.scene_dir)

        if not os.path.exists(os.path.join(self.scene_dir, 'output')):
            os.makedirs(os.path.join(self.scene_dir, 'output'))

        if verbose is False:
            logging.basicConfig(filename=os.path.join(self.scene_dir, 'output','log.txt'), \
            level=logging.INFO, filemode='w')
        else:
            logging.basicConfig(level=logging.INFO)

    @property
    def scene_id(self):
        """ Stored internally as different parts. """
        
        lid = '%s%s%s%s%s' % (self.satelite, self.wrs2, self.date.strftime('%Y%j'), \
        self.station, self.version)
        return lid

    @scene_id.setter
    def scene_id(self, new_id):
        """ Check that the landsat id is valid before assignment. """
        
        match = re.match('^L(C8|E7|T5)\d{13}(LGN|EDC|SGS|AGS|ASN|SG1|GLC|ASA|KIR|MOR|KHC|PAC|KIS|CHM|LGS|MGR|COA|MPS)0[0-5]$', new_id)

        if match:
            self.satelite = new_id[0:3]
            self.wrs2 = new_id[3:9]
            self.date = datetime.datetime.strptime(new_id[9:16], '%Y%j')
            self.station = new_id[16:19]
            self.version = new_id[-2:]

        else:
            logging.error('scene_id.setter: %s is the wrong format' % new_id)
            sys.exit(-1)

    @property
    def buoy_id(self):
        return self._buoy_id

    @buoy_id.setter
    def buoy_id(self, new_id):
        """ Check that the buoy id is valid before assignment. """
        
        match = re.match('^\d{5}$', new_id)

        if match:   # if it matches the pattern
            self._buoy_id = match.group()
        else:
            self._buoy_id = new_id
            logging.warning('.buoy_id: @buoy_id.setter: %s is the wrong format' % new_id)

    def __repr__(self):
        return self.__str__()
        
    def __str__(self):
        """ Control output of class. """
            
        output_items = ['Scene ID: %s'%self.scene_id]
        
        output_items.append('Modeled: %s' % (self.modeled_radiance))
        output_items.append('Image: %s' % (self.image_radiance))
        
        output_items.append('Buoy ID: %7s Lat-Lon: %8s Skin Temp: %s' %(self.buoy_id, self.buoy_location, self.skin_temp))
            
        return '\n'.join(output_items)
    
    def calc_all(self):
        """ Calculate Image and Modeled Radiances, as well as all the other variables. """
        self.download_img_data()
        self.calculate_buoy_information()
        self.download_mod_data()
        
        # modeled radiance processing
        if self.satelite == 'LC8':   # L8
            rsr_files = [[10, os.path.join(self.data_base, 'misc', 'L8_B10.rsp')], \
                        [11, os.path.join(self.data_base, 'misc', 'L8_B11.rsp')]]
            img_files = [[10, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_10'])], \
                        [11, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_11'])]]
        elif self.satelite == 'LE7':   # L7
            rsr_files = [[6, os.path.join(self.data_base, 'misc', 'L7_B6_2.rsp')]]
            img_files = [[6, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_6_VCID_2'])]]
        elif self.satelite == 'LT5':   # L5
            rsr_files = [[6, os.path.join(self.data_base, 'misc', 'L5_B6.rsp')]]
            img_files = [[6, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_6'])]]

        modtran_data = self.run_modtran()

        for band, rsr_file in rsr_files:
            logging.info('Modeled Radiance Processing: Band %s' % (band))
            self.modeled_radiance.append(mod_proc.calc_radiance(self, rsr_file, modtran_data))
                    
        for band, img_file in img_files:
            logging.info('Image Radiance Processing: Band %s' % (band))
            self.image_radiance.append(img_proc.calc_radiance(self, img_file, band))
  
    def download_mod_data(self):
        """
        Download atmospheric data.

        Args: None

        Returns: None
        """

        logging.info('Downloading atmospheric data.')

        if self.atmo_src == 'narr':
            narr_data.download(self)
        elif self.atmo_src == 'merra':
            merra_data.download(self)
            
    def run_modtran(self):
        """
        Make tape5, run modtran and parse tape7.scn for this instance.

        Args: None

        Returns: 
            Relevant Modtran Outputs: spectral, units=[] TODO
                upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect
        """
        logging.info('Generating tape5 files.')
        # read in narr data and generate tape5 files and caseList
        point_dir, self.narr_coor = mod_proc.make_tape5s(self)
        
        logging.info('Running modtran.')
        mod_proc.run_modtran(point_dir)
        
        logging.info('Parsing modtran output.')
        upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect = mod_proc.parse_tape7scn(point_dir)
        return upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect

    
    def download_img_data(self):
        """
        Download landsat product and parse metadata.

        Args: None

        Returns: None
        """
        
        logging.info('.download_img_data: Dealing with Landsat Data')
    
        # download landsat image data and assign returns
        downloaded_LID = landsat_data.download(self)

        self.satelite = downloaded_LID[2:3]
        self.scene_id = downloaded_LID

        # read in landsat metadata
        self.metadata = landsat_data.read_metadata(self)
        
        date = self.metadata['DATE_ACQUIRED']
        time = self.metadata['SCENE_CENTER_TIME'].replace('"', '')[0:7]
        self.scenedatetime = datetime.datetime.strptime(date+' '+time, '%Y-%m-%d %H:%M:%S')

    def calculate_buoy_information(self):
        """
        Pick buoy dataset, download, and calculate skin_temp.

        Args: None

        Returns: None
        """
        
        corners = numpy.asarray([[0, 0]]*2, dtype=numpy.float32)
        corners[0] = self.metadata['CORNER_UR_LAT_PRODUCT'], \
            self.metadata['CORNER_UR_LON_PRODUCT']

        corners[1] = self.metadata['CORNER_LL_LAT_PRODUCT'], \
            self.metadata['CORNER_LL_LON_PRODUCT']

        save_dir = os.path.join(self.data_base, 'noaa')
        dataset = None
        
        buoy_data.get_stationtable(save_dir)   # download staion_table.txt
        datasets, buoy_coors, depths = buoy_data.find_datasets(save_dir, corners)
        
        url_base = ['http://www.ndbc.noaa.gov/data/historical/stdmet/',
                    'http://www.ndbc.noaa.gov/data/stdmet/']
        mon_str = ['Jan/', 'Feb/', 'Apr/', 'May/', 'Jun/', 'Jul/', 'Aug/',
                   'Sep/', 'Oct/', 'Nov/', 'Dec/']
                   
        year = self.date.strftime('%Y')
        month = self.date.strftime('%m')
        urls = []
        
        if self.buoy_id:
            urls.append('%s%sh%s.txt.gz'%(url_base[0], self.buoy_id, year))
            urls.append('%s%s%s%s2015.txt.gz' % (url_base[1], mon_str[int(month)-1], self.buoy_id, str(int(month))))

            ret_vals = buoy_data.search_stationtable(save_dir, self.buoy_id)
            if ret_vals != -1:
                datasets, buoy_coors, depths = ret_vals
            else: 
                logging.warning('.start_download: _save_buoy_data failed')
   
        for dataset in datasets:
            if year != '2015':
                urls.append(url_base[0] + dataset + 'h' + year + '.txt.gz')
            else:
                urls.append(url_base[1] + mon_str[int(month)-1] + dataset +
                            str(int(month)) + '2015.txt.gz')
        
        for url in urls:
            dataset = os.path.basename(url)
            zipped_file = os.path.join(save_dir, dataset)
            unzipped_file = zipped_file.replace('.gz', '')
            
            try:
                buoy_data.get_buoy_data(zipped_file, url)   # download and unzip
                temp, pres, atemp, dewp = buoy_data.find_skin_temp(self, unzipped_file, depths[urls.index(url)])
                
                self.buoy_id = datasets[urls.index(url)]
                self.buoy_location = buoy_coors[urls.index(url)]
                self.skin_temp = temp
                self.buoy_press = pres
                self.buoy_airtemp = atemp
                self.buoy_dewpnt = dewp

                logging.info('Used buoy dataset %s.'% dataset)
                break
                
            except buoy_data.BuoyDataError:
                logging.warning('Dataset %s didn\'t work (BuoyDataError). Trying a new one' % (dataset))
                continue
            except ValueError:
                logging.warning('Dataset %s didn\'t work (ValueError). Trying a new one' % (dataset))
                continue
            except IOError:
                logging.warning('Dataset %s didn\'t work (IOError). Trying a new one' % (dataset))
                continue
