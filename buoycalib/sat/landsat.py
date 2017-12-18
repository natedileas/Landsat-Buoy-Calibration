import datetime

from osgeo import gdal, osr
import ogr
import utm

from .. import settings
from ..download import url_download
from . import image_processing as img

def download(scene_id, bands=[10, 11, 'MTL'], directory_=settings.LANDSAT_DIR):
    directory = directory_ + '/' + scene_id

    if 'MTL' not in bands:
        bands.append('MTL')

    for band in bands:
        # get url for the band
        url = amazon_s3_url(scene_id, band)
        url_download(url, directory)

    meta_file = '{0}/{1}_MTL.txt'.format(directory, scene_id)
    metadata = read_metadata(meta_file)

    return metadata['date'], directory, metadata


def amazon_s3_url(scene_id, band):
    info = parse_L8(scene_id)

    if band != 'MTL':
        filename = '%s_B%s.TIF' % (info['id'], band)
    else:
        filename = '%s_%s.txt' % (info['id'], band)

    return '/'.join([settings.LANDSAT_S3_URL, info['sat'], info['path'], info['row'], info['id'], filename])


def parse_L8(scene_id):
    parsed = {}

    if len(scene_id) == 21:
        parsed['sat'] = 'L' + scene_id[2:3]
        parsed['path'] = scene_id[3:6]
        parsed['row'] = scene_id[6:9]
        parsed['id'] = scene_id
    elif len(scene_id) == 40:
        parsed['s'] = 'c{0}/L{1}'.format(scene_id[-4], scene_id[3])
        parsed['path'] = scene_id[10:13]
        parsed['row'] = scene_id[13:16]
        parsed['id'] = scene_id
    else:
        raise Exception('Received incorrect scene: {0}'.format(scene_id))

    return parsed

def read_metadata(filename):
    """
    Read landsat metadata from MTL file and return a dict with the values.

    Args:
        filename: absolute file location of metadata file

    Returns:
        metadata: dict of landsat metadata from _MTL.txt file.
    """
    def _replace(string, chars):
        for c in chars:
            string = string.replace(c, '')
        return string

    # TODO make really robust
    chars = ['\n', '"', '\'']    # characters to remove from lines
    metadata = {}

    with open(filename, 'r') as mtl_file:
        for line in mtl_file:
            try:
                info = _replace(line.strip(' '), chars).split(' = ')
                if 'GROUP' in info or 'END_GROUP' in info or 'END' in info:
                    continue
                info[1] = _replace(info[1], chars)
                metadata[info[0]] = float(info[1])
            except ValueError:
                metadata[info[0]] = info[1]

    dt_str = metadata['DATE_ACQUIRED'] + ' ' + metadata['SCENE_CENTER_TIME'][:8]
    metadata['date'] = datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')

    return metadata


def calc_ltoa(directory, metadata, lat, lon, band):
    """
    Calculate image radiance from metadata

    Args:
        metadata: landsat scene metadata
        lat: point of interest latitude
        lon: point of interest longitude
        band: image band to calculate form

    Returns:
        radiance: L [W m-2 sr-1 um-1] of the image at the buoy location
    """
    img_file = directory + '/' + metadata['FILE_NAME_BAND_' + str(band)]

    dataset = gdal.Open(img_file)   # open image
    geotransform = dataset.GetGeoTransform()   # get data transform

    # change lat_lon to same projection
    l_x, l_y, l_zone, l_zone_let = utm.from_latlon(lat, lon)

    if metadata['UTM_ZONE'] != l_zone:
        l_x, l_y = convert_utm_zones(l_x, l_y, l_zone, metadata['UTM_ZONE'])

    # calculate pixel locations: http://www.gdal.org/gdal_datamodel.html
    x = int((l_x - geotransform[0]) / geotransform[1])   # latitude
    y = int((l_y - geotransform[3]) / geotransform[5])   # longitude

    # calculate digital count average of 3x3 area around poi
    # TODO add ROI width parameter
    image_data = dataset.ReadAsArray()
    dc_avg = image_data[y-1:y+2, x-1:x+2].mean()

    add = metadata['RADIANCE_ADD_BAND_' + str(band)]
    mult = metadata['RADIANCE_MULT_BAND_' + str(band)]

    radiance = dc_avg * mult + add

    return radiance
