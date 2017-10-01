import datetime

from .. import settings
from ..download import url_download, remote_file_exists
from .. import image_processing as img
from .Scene import id_to_scene

def download_amazons3(scene_id, bands=[10, 11, 'MTL']):
    scene = id_to_scene(scene_id)

    if 'MTL' not in bands:
        bands.append('MTL')

    urls = []

    for band in bands:
        # get url for the band
        url = amazon_s3_url(scene, band)

        # make sure it exist
        remote_file_exists(url)
        urls.append(url)

    scene.scene_dir = settings.LANDSAT_DIR + '/' + scene_id

    for url in urls:
        url_download(url, scene.scene_dir)

    meta_file = '{0}/{1}_MTL.txt'.format(scene.scene_dir, scene_id)
    scene.metadata = read_metadata(meta_file)

    return scene


def amazon_s3_url(scene, band):
    if band != 'MTL':
        filename = '%s_B%s.TIF' % (scene.id, band)
    else:
        filename = '%s_%s.txt' % (scene.id, band)

    return '/'.join([settings.LANDSAT_S3_URL, scene.satellite, scene.path, scene.row, scene.id, filename])


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


def calc_ltoa(metadata, lat, lon, band):
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
    # TODO fix this
    img_file = metadata['scene_dir'] + '/' + metadata['FILE_NAME_BAND_' + str(band)]
    poi = img.find_roi(img_file, lat, lon, metadata['UTM_ZONE'])

    # calculate digital count average of 3x3 area around poi
    dc_avg = img.calc_dc_avg(img_file, poi)

    add = metadata['RADIANCE_ADD_BAND_' + str(band)]
    mult = metadata['RADIANCE_MULT_BAND_' + str(band)]

    radiance = dc_avg * mult + add

    return radiance
