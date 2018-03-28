import datetime

from osgeo import gdal, osr
import ogr
import utm

from .. import settings
from ..download import url_download, RemoteFileException, ungzip
from . import image_processing as img


def download(scene_id, bands, directory_=settings.LANDSAT_DIR):
    directory = directory_ + '/' + scene_id

    if 'MTL' not in bands:
        bands.append('MTL')

    for band in bands:
        # get url for the band
        try:   # amazon s3 only has stuff from 2017 on
            url = amazon_s3_url(scene_id, band)
            fp = url_download(url, directory)

        except RemoteFileException:   # try to use EarthExplorer
            scene_id = product2entityid(scene_id)
            url = earthexplorer_url(scene_id)
            fp = url_download(url, directory, _filename=scene_id+'.gz', auth=settings.EARTH_EXPLORER_LOGIN)
            fp = ungzip(fp)

    meta_file = '{0}/{1}_MTL.txt'.format(directory, scene_id)
    metadata = read_metadata(meta_file)

    return metadata['date'], directory, metadata


def product2entityid(product_id):
    if len(product_id) == 21:
        return product_id

    sat = 'c{0}/L{1}'.format(product_id[-4], product_id[3])
    path = product_id[10:13]
    row = product_id[13:16]

    date = datetime.datetime.strptime(product_id[17:25], '%Y%m%d')

    return 'LC8{path}{row}{date}LGN{vers}'.format(path=path, row=row, date=date.strftime('%Y%j'), vers='01')


def amazon_s3_url(scene_id, band):
    info = parse_L8(scene_id)

    if band != 'MTL':
        filename = '%s_B%s.TIF' % (info['id'], band)
    else:
        filename = '%s_%s.txt' % (info['id'], band)

    return '/'.join([settings.LANDSAT_S3_URL, info['sat'], info['path'], info['row'], info['id'], filename])


def earthexplorer_url(scene_id):

    return settings.LANDSAT_EE_URL.format(scene_id)


def parse_L8(scene_id):
    parsed = {}

    if len(scene_id) == 21:
        parsed['sat'] = 'L' + scene_id[2:3]
        parsed['path'] = scene_id[3:6]
        parsed['row'] = scene_id[6:9]
        parsed['id'] = scene_id
    elif len(scene_id) == 40:
        parsed['sat'] = 'c{0}/L{1}'.format(scene_id[-4], scene_id[3])
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
        l_x, l_y = img.convert_utm_zones(l_x, l_y, l_zone, metadata['UTM_ZONE'])

    # calculate pixel locations: http://www.gdal.org/gdal_datamodel.html
    x = int((l_x - geotransform[0]) / geotransform[1])   # latitude
    y = int((l_y - geotransform[3]) / geotransform[5])   # longitude

    # TODO check if x, y are within bounds

    # calculate digital count average of 3x3 area around poi
    # TODO add ROI width parameter
    image_data = dataset.ReadAsArray()
    #print(image_data, image_data.shape, image_data.mean(), y, x)
    dc_avg = image_data[y-1:y+2, x-1:x+2].mean()

    add = metadata['RADIANCE_ADD_BAND_' + str(band)]
    mult = metadata['RADIANCE_MULT_BAND_' + str(band)]

    radiance = dc_avg * mult + add
    #print(dc_avg, mult, add)

    return radiance
