#!/usr/bin/python

import os
from urllib2 import urlopen
import gzip
import shutil

import requests

CHUNK = 1024 * 1024 * 8   # 1 MB
S3_URL = 'https://landsat-pds.s3.amazonaws.com'


class RemoteFileException(Exception):
    pass


def url_download(url, out_dir):
    """ download a file (ftp or http) """
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    filename = url.split('/')[-1]
    filepath = os.path.join(out_dir, filename)

    if os.path.isfile(filepath):
        return filepath

    request = urlopen(url)

    with open(filepath, 'wb') as fileobj:
        while True:
            chunk = request.read(CHUNK)
            if not chunk:
                break
            fileobj.write(chunk)

    return filepath


def ungzip(filepath):
    """ un-gzip a fiile (equivalent of `gzip -d filepath`) """
    new_filepath = filepath.replace('.gz', '')
    with open(new_filepath, 'wb') as f_out, gzip.open(filepath, 'rb') as f_in:
        shutil.copyfileobj(f_in, f_out)

    return new_filepath


def remote_file_exists(url):
    status = requests.head(url).status_code

    if status != 200:
        raise RemoteFileException('File {0} doesn\'t exist.'.format(url))


def download_amazons3(scene_id, directory, bands=[10, 11, 'MTL']):
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

    scene_dir = directory + '/' + scene_id

    for url in urls:
        print('Downloaded: ', url_download(url, scene_dir))

    return scene_dir


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


def amazon_s3_url(sat, band):
    if band != 'MTL':
        filename = '%s_B%s.TIF' % (sat['scene'], band)
    else:
        filename = '%s_%s.txt' % (sat['scene'], band)

    return '/'.join([S3_URL, sat['sat'], sat['path'], sat['row'], sat['scene'], filename])

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Download a landsat scene.')

    parser.add_argument('scene_id', help='LANDSAT scene ID. Examples: LC80330412013145LGN00, LE70160382012348EDC00, LT50410372011144PAC01', nargs='+')
    parser.add_argument('-d', '--directory', help='Directory to download to.', default='.')
    parser.add_argument('-b', '--bands', nargs='+', help='Bands to download', default=['10', '11', 'MTL'])

    args = parser.parse_args()

    directory = os.path.normpath(args.directory)

    for scene in args.scene_id:
        print(scene, directory, args.bands)
        download_amazons3(scene, directory, args.bands)
