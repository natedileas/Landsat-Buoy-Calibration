#!/usr/bin/python

from buoycalib import (sat)
import os

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
        sat.landsat.download(scene, args.bands, directory)
