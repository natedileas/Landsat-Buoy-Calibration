import os

import requests

import settings
import download

def download_amazons3(scene_id, bands=['MTL', 10, 11]):
    sat = parse_scene(scene_id)

    if 'MTL' not in bands:
        bands.append('MTL')

    urls = []

    for band in bands:
        # get url for the band
        url = amazon_s3_url(sat, band)

        # make sure it exist
        remote_file_exists(url)
        urls.append(url)

    scene_dir = settings.LANDSAT_DIR + '/' + scene_id

    for url in urls:
        download.url_download(url, scene_dir)

    meta_file = '{0}/{1}_MTL.txt'.format(scene_dir, scene_id)
    metadata = read_metadata(meta_file)
    metadata['scene_dir'] = scene_dir

    return metadata


def parse_scene(scene_id):
    anatomy = {
            'path': None,
            'row': None,
            'sat': None,
            'scene': scene_id
    }
    if isinstance(scene_id, str) and len(scene_id) == 21:
        anatomy['path'] = scene_id[3:6]
        anatomy['row'] = scene_id[6:9]
        anatomy['sat'] = 'L' + scene_id[2:3]
    elif isinstance(scene_id, str) and len(scene_id) == 40:
        anatomy['path'] = scene_id[10:13]
        anatomy['row'] = scene_id[13:16]
        anatomy['sat'] = 'c{0}/L{1}'.format(scene_id[-4], scene_id[3])
    else:
        raise Exception('Received incorrect scene: {0}'.format(scene_id))

    return anatomy


def remote_file_exists(url):
    status = requests.head(url).status_code

    if status != 200:
        raise Exception('RemoteFileDoesntExist')


def amazon_s3_url(sat, band):
    if band != 'MTL':
        filename = '%s_B%s.TIF' % (sat['scene'], band)
    else:
        filename = '%s_%s.txt' % (sat['scene'], band)

    return '/'.join([settings.S3_URL, sat['sat'], sat['path'], sat['row'], sat['scene'], filename])


def read_metadata(filename):
    """
    Read landsat metadata from MTL file and return a dict with the values.

    Args:
        filename: absolute file location of metadata file

    Returns:
        metadata: dict of landsat metadata from _MTL.txt file.
    """
    # TODO strip group and end-group statements, add date handling, make really robust
    chars = ['\n', '"', '\'']    # characters to remove from lines
    metadata = {}

    with open(filename, 'r') as mtl_file:
        for line in mtl_file:
            try:
                info = line.strip(' ').split(' = ')
                info[1] = info[1].translate(None, ''.join(chars))
                metadata[info[0]] = float(info[1])
            except ValueError:
                metadata[info[0]] = info[1]
            except IndexError:
                metadata[info[0]] = info[0]

    return metadata


def calc_radiance(metadata, band):
    img_file = metadata['img_file']
    poi = img.find_roi(img_file, metadata['BUOY_LAT'], metadata['BUOY_LON'], metadata['UTM_ZONE'])

    # calculate digital count average of 3x3 area around poi
    dc_avg = img.calc_dc_avg(img_file, poi)

    if band == 10:
        L_add = metadata['RADIANCE_ADD_BAND_10']
        L_mult = metadata['RADIANCE_MULT_BAND_10']
    elif band == 11:
        L_add = metadata['RADIANCE_ADD_BAND_11']
        L_mult = metadata['RADIANCE_MULT_BAND_11']

    radiance = dc_avg * L_mult + L_add

    return radiance