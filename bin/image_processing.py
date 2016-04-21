from osgeo import gdal, osr
from PIL import Image, ImageDraw
import numpy
import os
import utm
import ogr
import osr

def find_roi(img_file, lat, lon, zone):
    """ find the region of interest in pixel coordinates. """
    # open image
    ds = gdal.Open(img_file)
    #get data transform
    gt = ds.GetGeoTransform()
    
    #change lat_lon to same projection
    ret_val = utm.from_latlon(lat, lon)
    
    l_x = ret_val[0]
    l_y = ret_val[1]
        
    if zone != ret_val[2]:
        l_x, l_y = convert_utm_zones(l_x, l_y, ret_val[2], zone)

    #calculate pixel locations- 
    #source:http://www.gdal.org/gdal_datamodel.html
    x = int((l_x - gt[0]) / gt[1])
    y = int((l_y - gt[3]) / gt[5])
    
    return x, y
    
def convert_utm_zones(x, y, zone_from, zone_to):
    """ convert lat/lon to appropriate utm zone. """

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
     
def calc_dc_avg(filename, poi):
    """ calculate the digital count average. """
    #open image
    im = Image.open(filename)
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

def dc_to_rad(band, metadata, DCavg):
    """ Convert digital count average to radiance. """
    
    if band == 10:
        L_add = metadata['RADIANCE_ADD_BAND_10']
        L_mult = metadata['RADIANCE_MULT_BAND_10']
    if band == 11:
        L_add = metadata['RADIANCE_ADD_BAND_11']
        L_mult = metadata['RADIANCE_MULT_BAND_11']

    #calculate LLambda
    LLambdaaddmult = DCavg * L_mult + L_add
        
    return LLambdaaddmult


def write_im(cc):
    img = os.path.join(cc.scene_dir, cc.scene_id+'_B10.TIF')
    zone = cc.metadata['UTM_ZONE']
    narr_pix = []
    
    # get narr point locations
    for lat, lon in cc.narr_coor:
        narr_pix.append(find_roi(img, lat, lon, zone))

    # draw circle on top of image to signify narr points
    image = Image.open(img)
    draw = ImageDraw.Draw(image)
    rx = 50
    ry = 23
    
    for x, y in narr_pix:
        draw.ellipse((x*2-rx, y-ry, x*2+rx, y+ry), fill=255)
        
    # draw buoy onto image
    x = cc.poi[0]
    y = cc.poi[1]
    draw.ellipse((x*2-rx, y-ry, x*2+rx, y+ry), fill=0)

    # downsample
    image.mode = 'I'
    image = image.point(lambda i:i*(1./256)).convert('L')
    image = image.resize((500, 486), Image.ANTIALIAS)
    
    # save
    save_path = os.path.join(cc.scene_dir, cc.scene_id+'_mod.TIF')
    image.save(save_path)