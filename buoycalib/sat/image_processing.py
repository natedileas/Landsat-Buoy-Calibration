from PIL import Image
from osgeo import gdal, osr
import ogr
import utm


class OutOfRangeError(Exception):
    pass


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
    dataset = gdal.Open(img_file)   # open image
    geotransform = dataset.GetGeoTransform()   # get data transform

    # change lat_lon to same projection
    l_x, l_y, l_zone, l_zone_let = utm.from_latlon(lat, lon)

    if zone != l_zone:
        l_x, l_y = convert_utm_zones(l_x, l_y, l_zone, zone)

    # calculate pixel locations: http://www.gdal.org/gdal_datamodel.html
    x = int((l_x - geotransform[0]) / geotransform[1])   # latitude
    y = int((l_y - geotransform[3]) / geotransform[5])   # longitude

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
    input_epsg = int(float('326' + str(zone_from)))
    output_epsg = int(float('326' + str(zone_to)))

    # create a geometry from coordinates
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(x, y)

    # create coordinate transformation
    in_spatial_ref = osr.SpatialReference()
    in_spatial_ref.ImportFromEPSG(input_epsg)

    out_spatial_ref = osr.SpatialReference()
    out_spatial_ref.ImportFromEPSG(output_epsg)

    coord_trans = osr.CoordinateTransformation(in_spatial_ref, out_spatial_ref)

    # transform point
    point.Transform(coord_trans)

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

    img = Image.open(filename)

    w, h = img.size
    if not 0 < poi[0] < w or not 0 < poi[1] < h:
        raise OutOfRangeError('POI out of range.')

    img_loaded = img.load()


    # ROI gives top left pixel location
    # POI gives center tap location
    roi = poi[0] - 1, poi[1] + 1

    dc_sum = 0
    for i in range(3):
        for j in range(3):
            dc_sum += img_loaded[roi[0] + i, roi[1] + j]

    dc_avg = dc_sum / 9.0   # calculate dc_avg

    return dc_avg
