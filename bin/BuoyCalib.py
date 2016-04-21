import os
import sys
import datetime
import re
import csv
import subprocess
import pickle
from PIL import Image, ImageDraw
import numpy

import modeled_processing as mod_proc
import image_processing as img_proc
import buoy_data
import landsat_data


class CalibrationController(object):
    ############## ATTRIBUTES ##########################################################
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
    poi = None
    
    # attributes that make up the lansat id
    satelite = None
    wrs2 = None
    date = None
    version = None
    _verbose = False
    
    ############## ENTRY POINT ##########################################################
    def __init__(self, LID, BID, DIR='./data/scenes/', verbose=False):
        """ set up CalibrationController object. """
        
        self.scene_id = LID
                
        self.filepath_base = os.path.realpath(os.path.join(__file__, '../..'))
        self.scene_dir = os.path.realpath(os.path.join(DIR, LID))
        
        self._verbose = verbose
    
############## GETTERS AND SETTERS ##########################################################
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
            print 'WARNING scene_id.setter: %s is the wrong format' % new_id


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
            print 'WARNING .buoy_id: @buoy_id.setter: the given buoy id is the wrong format'
     
            
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
        
    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, v):
        self._verbose = v   # option for command line output

        if v is False:
            try:
                log_file = open(os.path.join(self.scene_dir, 'log.txt'), 'w')
                self.stdout = sys.stdout
                sys.stdout = log_file
            except IOError:
                pass
        if v is True:
            try:
                sys.stdout = self.stdout
            except:
                pass

    ############## MEMBER FUNCTIONS ##########################################################
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
    
    def write_im(self):
        img = os.path.join(self.scene_dir, self.scene_id+'_B10.TIF')
        zone = self.metadata['UTM_ZONE']
        narr_pix = []
        
        # get narr point locations
        for lat, lon in self.narr_coor:
            narr_pix.append(img_proc.find_roi(img, lat, lon, zone))

        # draw circle on top of image to signify narr points
        image = Image.open(img)
        draw = ImageDraw.Draw(image)
        rx = 50
        ry = 23
        
        for x, y in narr_pix:
            draw.ellipse((x*2-rx, y-ry, x*2+rx, y+ry), fill=255)
            
        # draw buoy onto image
        x = self.poi[0]
        y = self.poi[1]
        draw.ellipse((x*2-rx, y-ry, x*2+rx, y+ry), fill=0)

        # downsample
        image.mode = 'I'
        image = image.point(lambda i:i*(1./256)).convert('L')
        image = image.resize((500, 486), Image.ANTIALIAS)
        
        # save
        save_path = os.path.join(self.scene_dir, self.scene_id+'_mod.TIF')
        image.save(save_path)
        
    def to_csv(self, f):
        """ write results to csv format. """
        
        w = csv.writer(f, quoting=csv.QUOTE_NONE, )
        w.writerow(self.fmt_items(', '))
        
        
    def fmt_items(self, delim=', '):
        """ helper function for self.to_csv. """
        
        items = [self.scene_id]
        
        if self._buoy_id:
            items.append(str(self.buoy_location[0]))   # lat
            items.append(str(self.buoy_location[1]))   # lon
                
        items.append(self.date.strftime('%m/%d/%Y'))   # year
        items.append(self.date.strftime('%j'))   # doy
        items.append(self.wrs2[0:3])   # path
        items.append(self.wrs2[3:6])   # row
        items.append(' ')   # day/ night
        items.append(self.buoy_id)   # buoy id
        items.append(' ')   # sca
        items.append(' ')   # detector
        items.append(' ')   # temp difference band 10
        items.append(' ')   # temp difference band 11
        
        if self.modeled_radiance and self.image_radiance:
            items.append(str(self.image_radiance[0]))  # band 10
            items.append(str(self.modeled_radiance[0]))   # band 10
            items.append(str(self.image_radiance[1]))   # band 11
            items.append(str(self.modeled_radiance[1]))   # band 11
            items.append(str(self.skin_temp))   # buoy (skin) temp

        return items

    ### real work functions ###
                    
    def download_mod_data(self):
        """ download NARR Data. """
    
        print 'download_mod_data: Downloading NARR Data'
    
        if os.path.exists(os.path.join(self.scene_dir, 'narr/HGT_1/1000.txt')):
            return 0
    
        # begin download of NARR data
        os.chmod('./bin/NARR_py.bash', 0755)
          
        ret_val = subprocess.call('./bin/NARR_py.bash %s %s %s' % (self.scene_dir, self.scene_id, int(self.verbose)), shell=True)
        if ret_val == 1:
            print 'missing wgrib error' 
            sys.exit(-1)
            
    def calc_mod_radiance(self):
        """ calculate modeled radiance for band 10 and 11. """
            
        print 'Generating tape5 files.'
        # read in narr data and generate tape5 files and caseList
        caseList, self.narr_coor = mod_proc.make_tape5s(self)
        
        print 'Running modtran.'
        # change access to prevent errors
        modtran_bash_path = os.path.join(self.filepath_base, 'bin/modtran.bash')
        os.chmod(modtran_bash_path, 0755)
           
        subprocess.check_call('./bin/modtran.bash %s %s' % (-int(self.verbose), os.path.join(self.scene_dir, 'points')), shell=True)
        
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
        
        print 'Parsing tape6 files.'
        upwell_rad = []
        downwell_rad = []
        wavelengths = []
        transmission = []
        gnd_reflect = []
        
        for i in range(4):
            caseList_p = caseList[i]
            ret_vals = mod_proc.read_tape6(caseList_p)
            
            upwell_rad = numpy.append(upwell_rad, ret_vals[0])   # W cm-2 sr-1 um-1
            downwell_rad = numpy.append(downwell_rad, ret_vals[1])   # W cm-2 sr-1 um-1
            wavelengths = ret_vals[2]   # microns
            transmission = numpy.append(transmission, ret_vals[3])   # no units
            gnd_reflect = numpy.append(gnd_reflect, ret_vals[4])   # W cm-2 sr-1 um-1
            
        # interpolate to buoy location
        upwell_rad = mod_proc.offset_bilinear_interp(upwell_rad, self.narr_coor, self.buoy_location)
        downwell_rad = mod_proc.offset_bilinear_interp(downwell_rad, self.narr_coor, self.buoy_location)
        transmission = mod_proc.offset_bilinear_interp(transmission, self.narr_coor, self.buoy_location)
        gnd_reflect = mod_proc.offset_bilinear_interp(gnd_reflect, self.narr_coor, self.buoy_location)

        rsr_files = [[10, './data/shared/L8_B10.rsp'], \
                     [11, './data/shared/L8_B11.rsp']]
        modeled_rad = []
        
        for band, rsr_file in rsr_files:
            
            print 'Modeled Radiance Processing: Band %s' % (band)

            RSR, RSR_wavelengths = mod_proc.read_RSR(rsr_file)
            
            # resample to rsr wavelength range
            upwell = numpy.interp(RSR_wavelengths, wavelengths, upwell_rad)
            downwell = numpy.interp(RSR_wavelengths, wavelengths, downwell_rad)
            tau = numpy.interp(RSR_wavelengths, wavelengths, transmission)
            gnd_ref = numpy.interp(RSR_wavelengths, wavelengths, gnd_reflect)
            spec_ref = numpy.interp(RSR_wavelengths, spec_r_wvlens, spec_r)
            
            spec_emis= 1 - spec_ref   # calculate emissivity

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
            numerator = mod_proc.integrate(RSR_wavelengths, Ltoa * RSR)
            denominator = mod_proc.integrate(RSR_wavelengths, RSR)
            modeled_rad.append((numerator / denominator) / 1e6)  # W m-2 sr-1 um-1
                
        self.modeled_radiance = modeled_rad

    def download_img_data(self):
        """ download landsat images and parse metadata. """
        
        print '.download_img_data: Dealing with Landsat Data'
    
        # download landsat image data and assign returns
        downloaded_LID = landsat_data.download(self)

        self.satelite = downloaded_LID[2:3]
        self.scene_id = downloaded_LID

        # read in landsat metadata
        self.metadata = landsat_data.read_metadata(self)

    
    def calc_img_radiance(self):
        """ calculate image radiance for band 10 and 11. """
        
        img_files = [[10, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_10'])], \
                     [11, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_11'])]]
        im_rad = []
        
        for band, img_file in img_files:
           print 'Image Radiance Processing: Band %s' % (band)
           
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
                print '.start_download: _save_buoy_data failed'
   
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
                temp, pres, atemp, dewp = buoy_data.find_skin_temp(unzipped_file, self.metadata['DATE_ACQUIRED'], url, depths[urls.index(url)])
                
                self.buoy_id = datasets[urls.index(url)]
                self.buoy_location = buoy_coors[urls.index(url)]
                self.skin_temp = temp
                self.buoy_press = pres
                self.buoy_airtemp = atemp
                self.buoy_dewpnt = dewp
                  
                print 'Used buoy dataset %s.'% dataset
                break
                
            except buoy_data.BuoyDataError:
                print 'Dataset %s didn\'t work (BuoyDataError). Trying a new one' % (dataset)
                continue
            except ValueError:
                print 'Dataset %s didn\'t work (ValueError). Trying a new one' % (dataset)
                continue
            except IOError:
                print 'Dataset %s didn\'t work (IOError). Trying a new one' % (dataset)
                continue
