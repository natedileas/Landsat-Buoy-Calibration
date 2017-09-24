import datetime

from . import settings
from download import url_download, remote_file_exists
import image_processing as img


def download_amazons3(granule_id, bands):
    info = parse_granule(granule_id)
    scene_dir = settings.MODIS_DIR + '/' + granule_id

    urls = []

    for band in bands:
        # get url for the band
        url = amazon_s3_url(info, band)

        # make sure it exist
        remote_file_exists(url)
        urls.append(url)

    for url in urls:
        url_download(url, scene_dir)

    return scene_dir


def parse_granule(granule):
    parsed = {}

    if isinstance(granule, str) and len(granule) == 27:
        split = granule.split('.')
        parsed['product'] = split[0]
        parsed['date'] = split[1][1:]
        parsed['horizontal'] = split[2][1:3]
        parsed['vertical'] = split[2][4:6]
    else:   # TODO make custom exception
        raise Exception('Received incorrect scene: {0}'.format(granule))

    return parsed


def amazon_s3_url(sat, band):
    if band != 'MTL':
        filename = '%s_B%s.TIF' % (sat['scene'], band)
    else:
        filename = '%s_%s.txt' % (sat['scene'], band)

    return '/'.join([settings.MODIS_S3_URL, sat['sat'], sat['path'], sat['row'], sat['scene'], filename])
