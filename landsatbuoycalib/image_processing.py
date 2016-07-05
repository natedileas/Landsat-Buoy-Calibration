import os
from PIL import Image, ImageDraw

import cv2
import numpy
from osgeo import gdal, osr
import ogr
import utm

def calc_radiance(cc, img_file, band):
    """
    Calculate image radiance for a given image file.

    Args:
        cc: CalibrationController object
        img_file: path/file of image to calculate radiance for
        band: image band, needed for dc to rad conversion

    Returns:
        radiance: L [W m-2 sr-1 um-1] of the image at the buoy location
    """

    # find Region Of Interest (PixelOI return)
    cc.poi = find_roi(img_file, cc.buoy_location[0], cc.buoy_location[1], cc.metadata['UTM_ZONE'])

    # calculate digital count average and convert to radiance of 3x3 area around poi
    dc_avg = calc_dc_avg(img_file, cc.poi)
    radiance = dc_to_rad(cc.satelite, band, cc.metadata, dc_avg)

    return radiance

def find_roi(img_file, lat, lon, zone):
    """
    Find pixel which corresponds to lat and lon in image.

    Args:
        img_file: full path to georeferenced image file
        lat, lon: float, location to find
        zone: utm zone in which the image is projected

    Returns:
        x, y: location in pixel space of the lat lon provided
    """
    
    
    ds = gdal.Open(img_file)   # open image
    gt = ds.GetGeoTransform()   # get data transform
    
    # change lat_lon to same projection
    l_x, l_y, l_zone, l_zone_let = utm.from_latlon(lat, lon)
    
    if zone != l_zone:
        l_x, l_y = convert_utm_zones(l_x, l_y, l_zone, zone)

    # calculate pixel locations- source: http://www.gdal.org/gdal_datamodel.html
    x = int((l_x - gt[0]) / gt[1])
    y = int((l_y - gt[3]) / gt[5])
    
    return x, y
    
def convert_utm_zones(x, y, zone_from, zone_to):
    """
    Convert lat/lon to appropriate utm zone.

    Args:
        x, y: lat and lon, projected in zone_from
        zone_from: inital utm projection zone 
        zone_to: final utm projection zone 

    Returns:
        x, y: lat and lon, projected in zone_to
    """

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
    """
    Calculate the digital count average of the region of interest.

    Args:
        filename: path/file of the image to operate on
        poi: pixel around which to calculate the average [x, y]

    Returns:
        dc_avg: digital count average of the 3x3 region around poi
    """

    im = Image.open(filename)
    im_loaded = im.load()
    
    roi = poi[0]-1, poi[1]+1   #ROI gives top left pixel location, 
                               #POI gives center tap location

    dc_sum = 0
    for i in range(3):
        for j in range(3):
            dc_sum += im_loaded[roi[0]+i, roi[1]+j]
    
    dc_avg = dc_sum / 9.0   #calculate dc_avg

    return dc_avg

def dc_to_rad(sat, band, metadata, dig_count):
    """
    Convert a digital count to radiance based on landsat constants.

    Args:
        sat: satelite to calculate for
        band: band to calculate for
        metadata: landsat metadata, dict
        dig_count: digital count to convert

    Returns:
        radiance: L [W m-2 sr-1 um-1]
    """
    
    if sat == 'LC8':   # L8
        if band == 10:
            L_add = metadata['RADIANCE_ADD_BAND_10']
            L_mult = metadata['RADIANCE_MULT_BAND_10']
        elif band == 11:
            L_add = metadata['RADIANCE_ADD_BAND_11']
            L_mult = metadata['RADIANCE_MULT_BAND_11']
        else:
            logging.error('Band was not 10 or 11 for landsat 8.')
            raise ValueError('Band was not 10 or 11 for landsat 8: %s' % band)
            
    elif sat == 'LE7':   # L7
        L_add = metadata['RADIANCE_ADD_BAND_6_VCID_2']
        L_mult = metadata['RADIANCE_MULT_BAND_6_VCID_2']
        
    elif sat == 'LT5':   # L5
        L_add = metadata['RADIANCE_ADD_BAND_6']
        L_mult = metadata['RADIANCE_MULT_BAND_6']

    else:
        logging.error('Sat was not 5, 7, or 8.')
        raise ValueError('Satelite string did not match: %s' % sat)

    radiance = dig_count * L_mult + L_add

    return radiance

def write_im(cc, img_file):
    """
    Write buoy and atmo data point locations on image for human inspection.

    Args:
        cc: CalibrationController object
        img_file: path/file to write on

    Returns:
        None
    """
    zone = cc.metadata['UTM_ZONE']
    narr_pix = []
    
    # get narr point locations
    for lat, lon in cc.narr_coor:
        narr_pix.append(find_roi(img_file, lat, lon, zone))

    # draw circle on top of image to signify narr points
    image = Image.open(img_file)
    
    # convert to proper format
    if image.mode == 'L':
        image = image.convert('RGB')
    elif 'I;16' in image.mode:
        image = image.point(lambda i:i*(1./256.0)).convert('RGB')

    img = numpy.asarray(image)
    gray_image = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl1 = clahe.apply(gray_image)

    img_corrected = Image.fromarray(cl1)
    img_corrected = img_corrected.convert('RGBA')
    
    draw = ImageDraw.Draw(img_corrected)
    r = 80
    
    for x, y in narr_pix:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0))
        
    # draw buoy onto image
    x = cc.poi[0]
    y = cc.poi[1]
    draw.ellipse((x - r, y - r, x + r, y + r), fill=(0, 255, 0))

    # downsample
    new_size = (int(image.size[0] / 15), int(image.size[1] / 15))
    image = img_corrected.resize(new_size, Image.ANTIALIAS)
    
    # put alpha mask in
    data = image.getdata()
    newData = []
    
    for item in data:
        #print item
        if item[0] < 5 and item[1] < 5 and item[2] < 5:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    
    image.putdata(newData)

    return image
