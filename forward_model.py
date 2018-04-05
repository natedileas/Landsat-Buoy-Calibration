import warnings

from buoycalib import (sat, buoy, atmo, radiance, modtran, settings, download, display)

import numpy
import cv2


def modis(scene_id, buoy_id, atmo_source='merra', verbose=False, bands=[31, 32]):
    overpass_date, directory, metadata, [granule_filepath, geo_ref_filepath] = sat.modis.download(scene_id)
    rsrs = {b:settings.RSR_MODIS[b] for b in bands}

    buoy_file = buoy.download(buoy_id, overpass_date)
    buoy_lat, buoy_lon, buoy_depth, bulk_temp, skin_temp, lower_atmo = buoy.info(buoy_id, buoy_file, overpass_date)
    #print('Buoy {0}: skin_temp: {1} lat: {2} lon:{3}'.format(buoy_id, skin_temp, buoy_lat, buoy_lon))
    
    # Atmosphere
    if atmo_source == 'merra':
        atmosphere = atmo.merra.process(overpass_date, buoy_lat, buoy_lon, verbose)
    elif atmo_source == 'narr':
        atmosphere = atmo.narr.process(overpass_date, buoy_lat, buoy_lon, verbose)
    else:
        raise ValueError('atmo_source is not one of (narr, merra)')

    # MODTRAN
    #print('Running MODTRAN:')
    modtran_directory = '{0}/{1}_{2}'.format(settings.MODTRAN_DIR, scene_id, buoy_id)
    wavelengths, upwell_rad, gnd_reflect, transmission = modtran.process(atmosphere, buoy_lat, buoy_lon, overpass_date, modtran_directory)

    # LTOA calcs
    #print('Ltoa Spectral Calculations:')
    mod_ltoa_spectral = radiance.calc_ltoa_spectral(wavelengths, upwell_rad, gnd_reflect, transmission, skin_temp)

    #print(rsrs)

    img_ltoa = sat.modis.calc_ltoa_direct(granule_filepath, geo_ref_filepath, buoy_lat, buoy_lon, bands)

    mod_ltoa = {}
    for b in bands:
        RSR_wavelengths, RSR = sat.modis.load_rsr(rsrs[b])
        mod_ltoa[b] = radiance.calc_ltoa(wavelengths, mod_ltoa_spectral, RSR_wavelengths, RSR)

    #print('RADIANCE \nmodeled: {1} \nimg: {2}'.format(b, mod_ltoa, img_ltoa))

    return mod_ltoa, img_ltoa, buoy_id, skin_temp, buoy_lat, buoy_lon


def landsat8(scene_id, atmo_source='merra', verbose=False, bands=[10, 11]):
    image = display.landsat_preview(args.scene_id, args.buoy_id)
    
    cv2.imshow('Landsat Preview', image)
    cv2.waitKey(50)
    
    # satelite download
    # [:] thing is to shorthand to make a shallow copy
    overpass_date, directory, metadata = sat.landsat.download(scene_id, bands[:])
    rsrs = {b:settings.RSR_L8[b] for b in bands}

    corners = sat.landsat.corners(metadata)
    buoys = buoy.datasets_in_corners(corners)

    if not buoys:
        raise buoy.BuoyDataException('no buoys in scene')

    data = {}

    for buoy_id in buoys:
        try:
            buoy_file = buoy.download(buoy_id, overpass_date)
        except download.RemoteFileException:
            warnings.warn('Buoy {0} does not have data for this date.'.format(buoy_id), RuntimeWarning)
            continue
        buoy_lat, buoy_lon, buoy_depth, bulk_temp, skin_temp, lower_atmo = buoy.info(buoy_id, buoy_file, overpass_date)

        # Atmosphere
        if atmo_source == 'merra':
            atmosphere = atmo.merra.process(overpass_date, buoy_lat, buoy_lon, verbose)
        elif atmo_source == 'narr':
            atmosphere = atmo.narr.process(overpass_date, buoy_lat, buoy_lon, verbose)
        else:
            raise ValueError('atmo_source is not one of (narr, merra)')

        # MODTRAN
        modtran_directory = '{0}/{1}_{2}'.format(settings.MODTRAN_DIR, scene_id, buoy_id)
        wavelengths, upwell_rad, gnd_reflect, transmission = modtran.process(atmosphere, buoy_lat, buoy_lon, overpass_date, modtran_directory)

        # LTOA calcs
        mod_ltoa_spectral = radiance.calc_ltoa_spectral(wavelengths, upwell_rad, gnd_reflect, transmission, skin_temp)

        img_ltoa = {}
        mod_ltoa = {}
        for b in bands:
            RSR_wavelengths, RSR = numpy.loadtxt(rsrs[b], unpack=True)
            img_ltoa[b] = sat.landsat.calc_ltoa(directory, metadata, buoy_lat, buoy_lon, b)
            mod_ltoa[b] = radiance.calc_ltoa(wavelengths, mod_ltoa_spectral, RSR_wavelengths, RSR)

        data[buoy_id] = (buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa)

    return data


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compute and compare the radiance values of \
     a landsat image to the propogated radiance of a NOAA buoy, using atmospheric data and MODTRAN. ')

    parser.add_argument('scene_id', help='LANDSAT or MODIS scene ID. Examples: LC08_L1TP_017030_20170703_20170715_01_T1, MOD021KM.A2011154.1650.006.2014224075807.hdf')
    parser.add_argument('buoy_id', help='NOAA Buoy ID. Example: 45012')
    parser.add_argument('-a', '--atmo', default='merra', choices=['merra', 'narr'], help='Choose atmospheric data source, choices:[narr, merra].')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    parser.add_argument('-s', '--save', default=True, action='store_false')
    parser.add_argument('-b', '--bands', nargs='+')

    args = parser.parse_args()

    if args.scene_id[0:3] in ('LC8', 'LC0'):   # Landsat 8
        bands = [int(b) for b in args.bands] if args.bands is not None else [10, 11]
        ret = landsat8(args.scene_id, args.atmo, args.verbose, bands)

    elif args.scene_id[0:3] == 'MOD':   # Modis
        bands = [int(b) for b in args.bands] if args.bands is not None else [31, 32]
        ret = modis(args.scene_id, args.buoy_id, args.atmo, args.verbose, bands)

    else:
        raise ValueError('Scene ID is not a valid format for (landsat8, modis)')

    print('Scene_ID, Buoy_ID, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa')
    for key in ret.keys():
        buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa = ret[key]
        print(args.scene_id, buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa)

    if args.save:
        with open('results.txt', 'w') as f:
            print('# Scene_ID, Buoy_ID, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa', file=f, sep=', ')
            for key in ret.keys():
                buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa = ret[key]
                print(args.scene_id, buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa, file=f, sep=', ')
