#!/usr/bin/python

from buoycalib import (sat)
import os

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Download a landsat scene.')

    parser.add_argument('granule_id', help='MODIS Granule ID, example: ', nargs='+')
    parser.add_argument('-d', '--directory', help='Directory to download to.', default='.')

    args = parser.parse_args()

    directory = os.path.normpath(args.directory)

    for scene in args.granule_id:
        print(scene, directory)
        print(sat.modis.download(scene, directory))
