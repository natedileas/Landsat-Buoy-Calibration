import os
import sys
import datetime
import re
import csv

import NarrData
import ModeledRadProcessing
import LandsatData
import BuoyData

class CalCon(object):
    _buoy_id = None
    buoy_location = None  # lat, lon
    skin_temp = None   # calculated from buoy dataset
    buoy_press = None
    buoy_airtemp = None
    buoy_dewpnt = None
    
    metadata = None    # landsat metadata
    
    _modeled_radiance = None
    narr_coor = None
    
    _image_radiance = None
    cloud_cover = None
    poi = None
    
    # attributes that make up the lansat id
    satelite = None
    wrs2 = None
    date = None
    version = None
        
    def __init__(self, LID, verbose=True, reprocess=False):
        self.scene_id = LID
                
        self.filepath_base = os.path.realpath(__file__)
        match = re.search('/bin/BuoyCalib.pyc?', self.filepath_base)
        if match:
            self.filepath_base = self.filepath_base.replace(match.group(), '')

        self.scene_dir = os.path.join(self.filepath_base, './data/scenes/%s' % self.scene_id)
        
        self.verbose = verbose   # option for command line output
        
        if reprocess is False:
            try:
                self.read_latest()
            except IOError:
                pass
        
        if verbose is False:
            log_file = open(os.path.join(self.scene_dir, 'log.txt'), 'w')
            self.stdout = sys.stdout
            sys.stdout = log_file
        
    @property
    def scene_id(self):
        lid = '%s%s%sLGN%s' % (self.satelite, self.wrs2, self.date.strftime('%Y%j'), self.version)
        return lid

    @scene_id.setter
    def scene_id(self, new_id):
        match = re.match('L[CE][78]\d{13}LGN0[0-5]', new_id)

        if match:
            new_id = match.group()
            self.satelite = new_id[0:3]
            self.wrs2 = new_id[3:9]
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
            match = re.match('\d{5}', new_id)

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
            
    @property
    def modeled_radiance(self):
        if not self._modeled_radiance:
            # do everything necesary to calculate mod_radiance
            
            if not self.metadata:
                download_img_data(self)
            if not self.buoy_location:
                calculate_buoy_information(self)
                
            # download
            ret_val=download_mod_data(self)
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
        self._modeled_radiance = new_rad
        
    @property
    def image_radiance(self):
        if not self._image_radiance:
            if not self.metadata:
                download_img_data(self)
            if not self.buoy_location:
                calculate_buoy_information(self)
            calc_img_radiance(self)
        return self._image_radiance
        
    @image_radiance.setter
    def image_radiance(self, new_rad):
        self._image_radiance = new_rad
        
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

    def output(self):
        out_file = os.path.join(self.scene_dir, 'latest_rad.txt')
        
        with open(out_file, 'w') as f:
            if self.buoy_id:
                f.write('BID: %7s BLL: %4s %4s temp: %4.4f\n' %(self.buoy_id, self.buoy_location[0], self.buoy_location[1], self.skin_temp))
            
            if self.modeled_radiance:
                f.write('M10: %2.6f M11: %2.6f\n' % (self.modeled_radiance[0], self.modeled_radiance[1]))
        
            if self.image_radiance:
                f.write('I10: %2.6f I11: %2.6f\n' % (self.image_radiance[0], self.image_radiance[1]))
        
    def read_latest(self):
        out_file = os.path.join(self.scene_dir, 'latest_rad.txt')
        
        try:
            with open(out_file, 'r') as f:
                for line in f:
                    data = line.split()
                    if 'BID' in line:
                        self.buoy_id = data[1]
                        self.buoy_location = [float(data[3]), float(data[4])]
                        self.skin_temp = float(data[-1])
                    if 'M10' in line:
                        self.modeled_radiance = float(data[1]), float(data[3])
                    if 'I10' in line:
                        self.image_radiance = float(data[1]), float(data[3])
                    
        except OSError:
            pass
            
    def to_csv(self, f):
        w = csv.writer(f, quoting=csv.QUOTE_NONE, )
        w.writerow(self.fmt_items(', '))
        
    def fmt_items(self, delim=', '):
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
        
                    
def download_mod_data(cc):

    print 'download_mod_data: Downloading NARR Data'

    ret_val = NarrData.download(cc)   # make call
    
    if ret_val == -1:
        print 'download_mod_data: missing wgrib issue'
        return -1

    return 0

def download_img_data(cc):
    """ download landsat image and parse metadata. """
    print '.download_img_data: Dealing with Landsat Data'

    return_vals = LandsatData.download(cc)   # make call

    if return_vals:   # make sure return_vals exist and are good returns
        if return_vals == -1:
            print 'WARNING .download_img_data: something went wrong'
            return -1
        else:          # otherwise, assign values
            cc.satelite = return_vals[0][2:3]
            cc.scene_id = return_vals[0]
            cc.metadata = return_vals[1]
            return 0
    else:
        return -1

def calc_img_radiance(cc):
    """ calculate image radiance. """
    import ImageRadProcessing

    print '.calc_img_radiance: Calculating Image Radiance'
    return_vals = ImageRadProcessing.ImageRadProcessing(cc).do_processing()

    cc.image_radiance = return_vals[0]
    cc.poi = return_vals[1]
    return 0
    
def calculate_buoy_information(cc):
    """pick buoy dataset, download, and calculate skin_temp. """
    print 'calculate_buoy_information: Downloading Buoy Data'
    return_vals = BuoyData.BuoyData(cc).start_download()

    if return_vals:
        if return_vals == -1:
            return -1
        else:
            cc.buoy_id = return_vals[0]
            cc.buoy_location = return_vals[1]
            cc.skin_temp = return_vals[2]
            cc.buoy_press = return_vals[3]
            cc.buoy_airtemp = return_vals[4]
            cc.buoy_dewpnt = return_vals[5]
            return 0
    else:
        return -1

    return 0

    
