import os
import sys
import datetime
import re
import csv
import subprocess
import pickle

import ModeledRadProcessing
import ImageRadProcessing
import BuoyData
import landsatdata
from PIL import Image, ImageDraw

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
        
    ############## ENTRY POINT ##########################################################
    def __init__(self, LID, BID, DIR='./data/scenes/', verbose=False):
        """ set up CalibrationController object. """
        
        self.scene_id = LID
                
        self.filepath_base = os.path.realpath(os.path.join(__file__, '../..'))
        self.scene_dir = os.path.realpath(os.path.join(DIR, LID))
        
        self.verbose = verbose   # option for command line output

        if verbose is False:
            try:
                log_file = open(os.path.join(self.scene_dir, 'log.txt'), 'w')
                self.stdout = sys.stdout
                sys.stdout = log_file
            except IOError:
                pass
                
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
            ret_val = self.download_mod_data()
            if ret_val == -1:
                return
                
            # process
            return_vals = ModeledRadProcessing.ModeledRadProcessing(self).do_processing()   # make call
    
            if return_vals == -1:
                print 'calc_mod_radiance: return_vals were -1'
                return
            else:
                self._modeled_radiance, self.narr_coor = return_vals
            
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
        
        
    ############## MEMBER FUNCTIONS ##########################################################
    def __repr__(self):
        return self.__str__()
        
        
    def __str__(self):
        """ print calculated values. """
            
        output_items = ['Scene ID: %s'%self.scene_id]
        
        if self.modeled_radiance:
            output_items.append('Modeled: Band 10: %2.6f Band 11: %2.6f' % (self.modeled_radiance[0], self.modeled_radiance[1]))
        
        if self.image_radiance:
            output_items.append('Image:   Band 10: %2.6f Band 11: %2.6f' % (self.image_radiance[0], self.image_radiance[1]))
        
        if self._buoy_id:
            output_items.append('Buoy ID: %7s Lat-Lon: %8s Skin Temp: %4.4f' %(self.buoy_id, self.buoy_location, self.skin_temp))
            
        if self.verbose is False:
            sys.stdout = self.stdout
            
        return '\n'.join(output_items)
      
    def write_im(self):
        img = os.path.join(self.scene_dir, self.scene_id+'_B10.TIF')
        zone = self.metadata['UTM_ZONE']
        narr_pix = []
        
        # get narr point locations
        for lat, lon in self.narr_coor:
            narr_pix.append(ImageRadProcessing.find_roi(img, lat, lon, zone))

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
        
                    
    def download_mod_data(self):
        """ download NARR Data. """
    
        print 'download_mod_data: Downloading NARR Data'
    
        if os.path.exists(os.path.join(self.scene_dir, 'narr/HGT_1/1000.txt')):
            return 0
    
        # begin download of NARR data

        subprocess.check_call('chmod u+x ./bin/NARR_py.bash', shell=True)
        
        v = -1
        if self.verbose:
          v = 0
          
        ret_val = subprocess.call('./bin/NARR_py.bash %s %s %s' % (self.scene_dir, self.scene_id, v), shell=True)
        if ret_val == 1:
            print 'missing wgrib error' 
            sys.exit(-1)
    
    def download_img_data(self):
        """ download landsat images and parse metadata. """
        
        print '.download_img_data: Dealing with Landsat Data'
    
        # download landsat image data and assign returns
        downloaded_LID = landsatdata.download(self)

        self.satelite = downloaded_LID[2:3]
        self.scene_id = downloaded_LID

        # read in landsat metadata
        self.metadata = landsatdata.read_metadata(self)

    
    def calc_img_radiance(self):
        """ calculate image radiance. """
    
        print '.calc_img_radiance: Calculating Image Radiance'
        self.image_radiance, self.poi = ImageRadProcessing.ImageRadProcessing(self).do_processing()

        
    def calculate_buoy_information(self):
        """ pick buoy dataset, download, and calculate skin_temp. """
        
        print 'calculate_buoy_information: Downloading Buoy Data'
        return_vals = BuoyData.BuoyData(self).start_download()
    
        try:
            self.buoy_id = return_vals[0]
            self.buoy_location = return_vals[1]
            self.skin_temp = return_vals[2]
            self.buoy_press = return_vals[3]
            self.buoy_airtemp = return_vals[4]
            self.buoy_dewpnt = return_vals[5]
        except TypeError:
            print 'TypeError: BuoyData returns incorrect.'
