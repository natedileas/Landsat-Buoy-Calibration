#!/usr/bin/python

import buoycalib


def run_all(scene_id, buoy_id, atmo_source='merra', bands=[10, 11]):
    metadata = buoycalib.landsat.download_amazons3(scene_id, bands)
    print(metadata['date'], metadata['date'].hour)

    buoy_info = buoycalib.buoy.calculate_buoy_information(metadata, buoy_id)
    print(buoy_info)

    atmosphere, corridinates = buoycalib.atmo.process(atmo_source, metadata, buoy_info)
    print atmosphere.shape

    modtran_out = buoycalib.modtran.process(atmosphere, buoy_info[1], buoy_info[2], metadata['date'], metadata['scene_dir'])

    mod_ltoa_spectral = buoycalib.radiance.calc_ltoa_spectral(modtran_out, buoy_info[4])
    for b in bands:
        mod_ltoa = buoycalib.radiance.calc_ltoa(modtran_out[2], mod_ltoa_spectral, buoycalib.settings.RSR_L8_B10)
        img_ltoa = buoycalib.landsat.calc_ltoa(metadata)

        print('band: {0} ltoa: {1} img: {2}'.format(b, mod_ltoa, img_ltoa))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compute and compare the radiance values of \
     a landsat image to the propogated radiance of a NOAA buoy, using NARR data and MODTRAN. \
     Works with landsat 5, 7, and 8. \nIf atmospheric data or landsat images need to be downloaded,\
     it will take between 5-7 minutes for NARR, and 2-3 for MERRA. If nothing need to be downloaded,\
     it will usually take less than 2 minutes for a single scene.')

    parser.add_argument('scene_id', help='LANDSAT scene ID. Examples: LC80330412013145LGN00, LE70160382012348EDC00, LT50410372011144PAC01', nargs='+')

    parser.add_argument('-b', '--buoy_id', help='NOAA Buoy ID. Example: 44009', default='')
    parser.add_argument('-i', '--image', help="draw NARR points and Buoy location on landsat image.", action='store_true', default=False)
    parser.add_argument('-s', '--show', help="show images on command line.", action='store_true', default=False)
    parser.add_argument('-o', '--Nooutput', help="Don't serialize, useful for testing.", action='store_true', default=False)
    parser.add_argument('-m', '--merra', help='Use MERRA-2 Data instead of NARR Data.', action='store_true', default=False)
    parser.add_argument('-v', '--verbose', help="Verbose: Specify to see command line output.", action='store_true', default=False)
    parser.add_argument('-r', '--reprocess', help="Add to explicitly reprocess.", action='store_true', default=False)

    args = parser.parse_args()

    for LID in args.scene_id:
        atmo_data_src = 'merra'

        run_all(LID, args.buoy_id, atmo_data_src)
