import os
import sys
import datetime
import re
import subprocess
import numpy
import logging

import modeled_processing as mod_proc
import image_processing as img_proc
import buoy_data
import landsat_data
import narr_data
import merra_data

class CalibrationController(object):
    def __init__(self, LID, BID=None, DIR='/dirs/home/ugrad/nid4986/landsat_data/', atmo_src='narr', verbose=False):
        """ set up CalibrationController object. """
        
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

    
    ### GETTERS AND SETTERS ###
    @property
    def scene_id(self):
        """ scene_id getter. stored internally as different parts. """
        
        lid = '%s%s%s%s%s' % (self.satelite, self.wrs2, self.date.strftime('%Y%j'), \
        self.station, self.version)
        return lid


    @scene_id.setter
    def scene_id(self, new_id):
        """ scene_id setter. check for validity before assignment. """
        
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
        """ buoy_id getter. """
        
        return self._buoy_id

    @buoy_id.setter
    def buoy_id(self, new_id):
        """ buoy_id setter. check for validity before assignment. """
        
        match = re.match('^\d{5}$', new_id)

        if match:   # if it matches the pattern
            self._buoy_id = match.group()
        else:
            self._buoy_id = new_id
            logging.warning('.buoy_id: @buoy_id.setter: %s is the wrong format' % new_id)

    #### MEMBER FUNCTIONS ###
    def __repr__(self):
        return self.__str__()
        
    def __str__(self):
        """ print calculated values. """
            
        output_items = ['Scene ID: %s'%self.scene_id]
        
        output_items.append('Modeled: %s' % (self.modeled_radiance))
        output_items.append('Image: %s' % (self.image_radiance))
        
        output_items.append('Buoy ID: %7s Lat-Lon: %8s Skin Temp: %s' %(self.buoy_id, self.buoy_location, self.skin_temp))
            
        return '\n'.join(output_items)
    
    ### helper functions ###
    def calc_all(self):
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

    ### real work functions ###
  
    def download_mod_data(self):
        """ download atmospheric data. """
        logging.info('Downloading atmospheric data.')

        if self.atmo_src == 'narr':
            narr_data.download(self)
        elif self.atmo_src == 'merra':
            merra_data.download(self)
            
    def run_modtran(self):
        logging.info('Generating tape5 files.')
        # read in narr data and generate tape5 files and caseList
        point_dir, self.narr_coor = mod_proc.make_tape5s(self)
        
        logging.info('Running modtran.')
        mod_proc.run_modtran(point_dir)
        
        logging.info('Parsing modtran output.')
        upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect = mod_proc.parse_tape7scn(point_dir)
        return upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect

    
    def download_img_data(self):
        """ download landsat images and parse metadata. """
        
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
        """ pick buoy dataset, download, and calculate skin_temp. """
        
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
                temp, pres, atemp, dewp = buoy_data.find_skin_temp(unzipped_file, self.metadata, url, depths[urls.index(url)])
                
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
