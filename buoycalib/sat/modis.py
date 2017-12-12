import datetime

from .. import settings
from ..download import url_download, remote_file_exists
from . import image_processing as img


def download(granule_id):
    """ download a MODIS scene by granule ID. """
    info = parse_granule(granule_id)
    scene_dir = settings.MODIS_DIR + '/' + granule_id

    urls = []

    url = '/'.join([settings.MODIS_URL, info['product'], info['date'].strftime('%Y/%j'), granule_id])
    url_download(url, scene_dir)

    # TODO parse metadata / georeference

    return scene_dir


def parse_granule(granule):
    # reference: https://lpdaac.usgs.gov/dataset_discovery/modis
    """
    MOD09A1 - Product Short Name
    .A2006001 - Julian Date of Acquisition (A-YYYYDDD)
    .h08v05 - Tile Identifier (horizontalXXverticalYY)
    .005 - Collection Version
    .2006012234567 - Julian Date of Production (YYYYDDDHHMMSS)
    .hdf - Data Format (HDF-EOS)
    """
    parsed = {}

    if isinstance(granule, str) and len(granule) == 44:
        split = granule.split('.')
        parsed['product'] = split[0]
        parsed['date'] = datetime.datetime.strptime(split[1], 'A%Y%j')
        parsed['horizontal'] = split[2][1:3]
        parsed['vertical'] = split[2][4:6]
    else:   # TODO make custom exception
        raise Exception('Received incorrect scene: {0}'.format(granule))

    return parsed
