from osgeo import gdal, osr
from PIL import Image
import logging
import numpy
import os
import utm

class ImageRadProcessing(object):
    """ Calculate Image Radiance.
    
    Attributes:
        logger: logging object used for non-verbose output.
        scene_id: scene id assigned from CalibrationController object.
        metadata: landsat metadata, dict.
        buoy_coor: coordinates of buoy, list.
        save_dir: directory where the landsat images reside
        which_landsat: landsat version and band, list.
        filename: name of landsat file to load, string.
        
    Methods:
        __init__(self, other): initialize the attributes using a CalibrationController object
        do_processing(self): run a set of processing stuff, returns list of radiances
        _calc_dc_avg(self, poi): calculate the digital count average 
        _find_roi(self): find the region of interest
        _convert_utm_zones(self, x, y, zone_from, zone_to): convert lat/lon to appropriate utm zone
        _dc_to_rad(self, DCavg): calculate the iamge radiance from the digital count average
    """
    def __init__(self, other):
        """ initialize the attributes using a CalibrationController object """
        #initialize logger
        logging.basicConfig(filename='CalibrationController.log', filemode='w'\
                            , level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.scene_id = other._scene_id
        self.metadata = other.metadata
        self.buoy_coor = [other.buoy_latitude, other.buoy_longitude]
        self.save_dir = os.path.join(other.filepath_base, other.image_file_extension)
        
        if other.satelite == 8:
            self.which_landsat = [8,2]
            self.filename = '%s' % ( self.metadata['FILE_NAME_BAND_10'])
        else: 
            self.which_landsat = [7,1]
            self.filename = '%d.TIF' % (self.metadata['FILE_NAME_BAND_6_VCID_2'])
        
        #strip unwanted characters and make a solid path
        self.filename = self.filename.translate(None, ''.join('"'))   
        self.filename = os.path.join(self.save_dir, self.filename)
        
    def do_processing(self):
        """ compute the image radiance. """
        image_radiance = []
        
        num_bands = self.which_landsat[1]
        for i in range(num_bands):
           self.logger.info('do_processing: band %s of %s', i+1, num_bands)
           
           poi = self.__find_roi()

           dc_avg = self.__calc_dc_avg(poi)
           image_radiance.append(self.__dc_to_rad(dc_avg))
           
           if self.which_landsat == [7,1]: break
           else: 
               self.which_landsat = [8,1]
               self.filename = '%s' %(self.metadata['FILE_NAME_BAND_11'])
               #strip unwanted characters and make a solid path
               self.filename = self.filename.translate(None, ''.join('"'))   
               self.filename = os.path.join(self.save_dir, self.filename)
            
        return image_radiance, poi
        
    def __calc_dc_avg(self, poi):
        """ calculate the digital count average. """
        #open image
        im = Image.open(self.filename)
        im_loaded = im.load()
        
        roi = poi[0]-1, poi[1]+1   #ROI gives top left pixel location, 
                                   #POI gives center tap location

        dc_sum = 0   #allocate for ROI dc_sum
        #extract ROI DCs
        for i in range(3):
            for j in range(3):
                dc_sum += im_loaded[roi[0]+i, roi[1]+j]
        
        dc_avg = dc_sum / 9.0   #calculate dc_avg
   
        return dc_avg
        
    def __find_roi(self):
        """ find the rgion of interest in pixel coordinates. """
        # open image
        ds = gdal.Open(self.filename)
        #get data transform
        gt = ds.GetGeoTransform()
        
        #change lat_lon to same projection
        ret_val = utm.from_latlon(self.buoy_coor[0], self.buoy_coor[1])
        
        l_x = ret_val[0]
        l_y = ret_val[1]
            
        if self.metadata['UTM_ZONE'] != ret_val[2]:
            l_x, l_y = self.__convert_utm_zones(l_x, l_y, ret_val[2], self.metadata['UTM_ZONE'])
        
        #calculate pixel locations- 
        #source:http://www.gdal.org/gdal_datamodel.html
        x = int((l_x - gt[0]) / gt[1])
        y = int((l_y - gt[3]) / gt[5])
        
        return x, y
        
    def __convert_utm_zones(self, x, y, zone_from, zone_to):
        """ convert lat/lon to appropriate utm zone. """
        import ogr, osr
    
        # Spatial Reference System
        inputEPSG = int(float('326' + str(zone_from)))
        outputEPSG = int(float('326' + str(zone_to)))
    
        # create a geometry from coordinates
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y)
    
        # create coordinate transformation
        inSpatialRef = osr.SpatialReference()
        inSpatialRef.ImportFromEPSG(inputEPSG)
    
        outSpatialRef = osr.SpatialReference()
        outSpatialRef.ImportFromEPSG(outputEPSG)
    
        coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
    
        # transform point
        point.Transform(coordTransform)
    
        return point.GetX(), point.GetY()
    
    def __dc_to_rad(self, DCavg):
        """ Convert digital count average to radiance. """
        #load values from metadata for calculation
        metadata = self.metadata
        which_landsat = self.which_landsat
        
        if which_landsat == [8,2]:
            L_add = metadata['RADIANCE_ADD_BAND_10']
            L_mult = metadata['RADIANCE_MULT_BAND_10']
        if which_landsat == [8,1]:
            L_add = metadata['RADIANCE_ADD_BAND_11']
            L_mult = metadata['RADIANCE_MULT_BAND_11']
        if which_landsat == [7,1]:
            L_add = metadata['RADIANCE_ADD_BAND_6_VCID_2']
            L_mult = metadata['RADIANCE_MULT_BAND_6_VCID_2']
   
        #calculate LLambda
        LLambdaaddmult = DCavg * L_mult + L_add
            
        return LLambdaaddmult        
