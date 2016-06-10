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
import misc_functions as funcs

class CalibrationController(object):
    ############## ATTRIBUTES #################################################
    # buoy and related attributes
    _buoy_id = None
    buoy_location = None  # [lat, lon]
    skin_temp = None   # calculated from buoy dataset
    buoy_press = None
    buoy_airtemp = None
    buoy_dewpnt = None
    
    # modeled radiance and related attributes
    _modeled_radiance = None
    narr_coor = None
    
    # image radiance and related attributes
    _image_radiance = None
    metadata = None    # landsat metadata
    scenedatetime = None 
    poi = None
    
    # attributes that make up the lansat id
    satelite = None
    wrs2 = None
    date = None
    version = None
    
    # verbosity
    verbose = False
    
    ############## ENTRY POINT ################################################
    def __init__(self, LID, BID, DIR='./data/scenes/', verbose=False, atmo_src='narr'):
        """ set up CalibrationController object. """
        
        self.scene_id = LID
                
        self.filepath_base = os.path.realpath(os.path.join(__file__, '../..'))
        self.scene_dir = os.path.realpath(os.path.join(DIR, LID))
        
        self.atmo_src = atmo_src

        if not os.path.exists(self.scene_dir):
            os.makedirs(self.scene_dir)

        self.verbose = verbose
        if verbose is False:
            logging.basicConfig(filename=os.path.join(self.scene_dir, 'log.txt'), level=logging.INFO, filemode='w')
        else:
            logging.basicConfig(level=logging.INFO)

    
############## GETTERS AND SETTERS ############################################
    @property
    def scene_id(self):
        """ scene_id getter. stored internally as different parts. """
        
        lid = '%s%s%sLGN%s' % (self.satelite, self.wrs2, self.date.strftime('%Y%j'), self.version)
        return lid


    @scene_id.setter
    def scene_id(self, new_id):
        """ scene_id setter. check for validity before assignment. """
        
        match = re.match('L[CE][78]\d{13}LGN0[0-5]', new_id)

        if match:
            new_id = match.group()
            self.satelite = new_id[0:3]
            self.wrs2 = new_id[3:9]
            self.date = datetime.datetime.strptime(new_id[9:16], '%Y%j')
            self.version = new_id[-2:]

        else:
            logging.warning('scene_id.setter: %s is the wrong format' % new_id)


    @property
    def buoy_id(self):
        """ buoy_id getter. """
        
        return self._buoy_id


    @buoy_id.setter
    def buoy_id(self, new_id):
        """ buoy_id setter. check for validity before assignment. """
        
        match = re.match('\d{5}', new_id)

        if match:   # if it matches the pattern
            self._buoy_id = match.group()
        else:
            self._buoy_id = new_id
            logging.warning('.buoy_id: @buoy_id.setter: the given buoy id is the wrong format')
     
            
    @property
    def modeled_radiance(self):
        """ modeled_radiance getter. calulates it if not already calculated. """
        
        if not self._modeled_radiance:
            # do everything necesary to calculate mod_radiance
            
            if not self.metadata:
                self.download_img_data()
            if not self.buoy_location:
                self.calculate_buoy_information()
                
            # download
            self.download_mod_data()
                
            # process
            self.calc_mod_radiance()
            
        return self._modeled_radiance
    
    
    @modeled_radiance.setter
    def modeled_radiance(self, new_rad):
        """ modeled_radiance setter. """
        
        self._modeled_radiance = new_rad
        
        
    @property
    def image_radiance(self):
        """ image_radiance getter. calulates it if not already calculated. """
        
        if not self._image_radiance:
            if not self.metadata:
                self.download_img_data()
            if not self.buoy_location:
                self.calculate_buoy_information()
            self.calc_img_radiance()
        return self._image_radiance
        
        
    @image_radiance.setter
    def image_radiance(self, new_rad):
        """ image_radiance setter. """
        
        self._image_radiance = new_rad

    ############## MEMBER FUNCTIONS ###########################################
    def __repr__(self):
        return self.__str__()
        
        
    def __str__(self):
        """ print calculated values. """
            
        output_items = ['Scene ID: %s'%self.scene_id]
        
        if self._modeled_radiance:
            output_items.append('Modeled: Band 10: %2.6f Band 11: %2.6f' % (self._modeled_radiance[0], self._modeled_radiance[1]))
        
        if self._image_radiance:
            output_items.append('Image:   Band 10: %2.6f Band 11: %2.6f' % (self._image_radiance[0], self._image_radiance[1]))
        
        if self._buoy_id:
            output_items.append('Buoy ID: %7s Lat-Lon: %8s Skin Temp: %4.4f' %(self.buoy_id, self.buoy_location, self.skin_temp))
            
        return '\n'.join(output_items)
    
    ### helper functions ###
    def calc_all(self):
         self.download_img_data()
         self.calculate_buoy_information()
         self.download_mod_data()
         self.calc_mod_radiance() 
         self.calc_img_radiance()

    ### real work functions ###
                    
    def download_mod_data(self):
        """ download atmospheric data. """
        logging.info('Downloading atmospheric data.')

        if self.atmo_src == 'narr':
            narr_data.download(self)
        elif self.atmo_src == 'merra':
            merra_data.download(self)

    def calc_mod_radiance(self):
        """ calculate modeled radiance for band 10 and 11. """
            
        logging.info('Generating tape5 files.')
        # read in narr data and generate tape5 files and caseList
        point_dir, self.narr_coor = mod_proc.make_tape5s(self)
        
        logging.info('Running modtran.')
        mod_proc.run_modtran(point_dir)
        
        # Load Emissivity / Reflectivity
        spec_r = numpy.array(0)
        spec_r_wvlens = numpy.array(0)
        water_file = './data/shared/water.txt'
        
        with open(water_file, 'r') as f:
            water_file = f.readlines()
            for line in water_file[3:]:
                data = line.split()
                spec_r_wvlens = numpy.append(spec_r_wvlens, float(data[0]))
                spec_r = numpy.append(spec_r, float(data[1].replace('\n', '')))
        
        logging.info('Parsing tape files.')
        ret_vals = mod_proc.parse_tape7scn(point_dir)
        upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect = ret_vals

        rsr_files = [[10, './data/shared/L8_B10.rsp'], \
                     [11, './data/shared/L8_B11.rsp']]
        modeled_rad = []
        
        for band, rsr_file in rsr_files:
            
            logging.info('Modeled Radiance Processing: Band %s' % (band))

            RSR, RSR_wavelengths = mod_proc.read_RSR(rsr_file)
            
            # resample to rsr wavelength range
            upwell = numpy.interp(RSR_wavelengths, wavelengths, upwell_rad)
            downwell = numpy.interp(RSR_wavelengths, wavelengths, downwell_rad)
            tau = numpy.interp(RSR_wavelengths, wavelengths, transmission)
            gnd_ref = numpy.interp(RSR_wavelengths, wavelengths, gnd_reflect)
            spec_ref = numpy.interp(RSR_wavelengths, spec_r_wvlens, spec_r)
            
            spec_emis = 1 - spec_ref   # calculate emissivity

            RSR_wavelengths = numpy.asarray(RSR_wavelengths) / 1e6   # convert to meters
            
            # calculate temperature array
            Lt = mod_proc.calc_temperature_array(RSR_wavelengths, self.skin_temp)  # w m-2 sr-1 m-1
            
            # calculate top of atmosphere radiance (Ltoa)
            # NEW METHOD 
            ## Ltoa = (Lbb(T) * tau * emis) + (gnd_ref * reflect) + pth_thermal
            term1 = Lt * spec_emis * tau # W m-2 sr-1 m-1
            term2 = spec_ref * gnd_ref * 1e10 # W m-2 sr-1 m-1
            Ltoa = (upwell * 1e10) + term1 + term2   # W m-2 sr-1 m-1
            
            # calculate observed radiance
            numerator = funcs.integrate(RSR_wavelengths, Ltoa * RSR)
            denominator = funcs.integrate(RSR_wavelengths, RSR)
            modeled_rad.append((numerator / denominator) / 1e6)  # W m-2 sr-1 um-1
                
        self.modeled_radiance = modeled_rad

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

    def calc_img_radiance(self):
        """ calculate image radiance for band 10 and 11. """
        
        img_files = [[10, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_10'])], \
                     [11, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_11'])]]
        im_rad = []
        
        for band, img_file in img_files:
           logging.info('Image Radiance Processing: Band %s' % (band))
           
           # find Region Of Interest (PixelOI return)
           self.poi = img_proc.find_roi(img_file, self.buoy_location[0], self.buoy_location[1], self.metadata['UTM_ZONE'])
            
           # calculate digital count average and convert to radiance of 3x3 area around poi
           dc_avg = img_proc.calc_dc_avg(img_file, self.poi)
           im_rad.append(img_proc.dc_to_rad(band, self.metadata, dc_avg))
        
        self.image_radiance = im_rad

    def calculate_buoy_information(self):
        """ pick buoy dataset, download, and calculate skin_temp. """
        
        corners = numpy.asarray([[0, 0]]*2, dtype=numpy.float32)
        corners[0] = self.metadata['CORNER_UR_LAT_PRODUCT'], \
            self.metadata['CORNER_UR_LON_PRODUCT']

        corners[1] = self.metadata['CORNER_LL_LAT_PRODUCT'], \
            self.metadata['CORNER_LL_LON_PRODUCT']

        save_dir = os.path.join(self.filepath_base, 'data/shared/buoy')
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
