import warnings

from buoycalib import (sat, buoy, atmo, radiance, modtran, settings, download, display, error_bar)

import numpy
import cv2


def modis(scene_id, atmo_source='merra', verbose=False, bands=[31, 32]):
    image = display.modis_preview(scene_id)
    
    cv2.imshow('MODIS Preview', image)
    cv2.waitKey(50)
    cv2.imwrite('preview_{0}.jpg'.format(scene_id), image)

    overpass_date, directory, metadata, [granule_filepath, geo_ref_filepath] = sat.modis.download(scene_id)
    rsrs = {b:settings.RSR_MODIS[b] for b in bands}

    corners = sat.modis.corners(metadata)
    buoys = buoy.datasets_in_corners(corners)

    if not buoys:
        raise buoy.BuoyDataException('no buoys in scene')

    data = {}

    for buoy_id in buoys:
        try:
            buoy_file = buoy.download(buoy_id, overpass_date)
            buoy_lat, buoy_lon, buoy_depth, bulk_temp, skin_temp, lower_atmo = buoy.info(buoy_id, buoy_file, overpass_date)
        except download.RemoteFileException:
            warnings.warn('Buoy {0} does not have data for this date.'.format(buoy_id), RuntimeWarning)
            continue
        except buoy.BuoyDataException as e:
            warnings.warn(str(e), RuntimeWarning)
            continue

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
        wavelengths, upwell_rad, gnd_reflect, transmission = modtran.process(atmosphere, buoy_lat, buoy_lon, overpass_date, modtran_directory, skin_temp)

        # LTOA calcs
        #print('Ltoa Spectral Calculations:')
        mod_ltoa_spectral = radiance.calc_ltoa_spectral(wavelengths, upwell_rad, gnd_reflect, transmission, skin_temp)

        img_ltoa, units = sat.modis.calc_ltoa_direct(granule_filepath, geo_ref_filepath, buoy_lat, buoy_lon, bands)

        mod_ltoa = {}
        for b in bands:
            RSR_wavelengths, RSR = sat.modis.load_rsr(rsrs[b])
            mod_ltoa[b] = radiance.calc_ltoa(wavelengths, mod_ltoa_spectral, RSR_wavelengths, RSR)

        error = error_bar.error_bar(scene_id, buoy_id, skin_temp, 0.35, overpass_date, buoy_lat, buoy_lon, rsrs, bands)
        print((buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, error, img_ltoa, overpass_date))
        data[buoy_id] = (buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, error, img_ltoa, overpass_date)
    
    return data


def landsat8(scene_id, atmo_source='merra', verbose=False, bands=[10, 11]):
    image = display.landsat_preview(scene_id, '')
    
    cv2.imshow('Landsat Preview', image)
    cv2.waitKey(50)
    cv2.imwrite('preview_{0}.jpg'.format(scene_id), image)
    
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
            buoy_lat, buoy_lon, buoy_depth, bulk_temp, skin_temp, lower_atmo = buoy.info(buoy_id, buoy_file, overpass_date)
        except download.RemoteFileException:
            warnings.warn('Buoy {0} does not have data for this date.'.format(buoy_id), RuntimeWarning)
            continue
        except buoy.BuoyDataException as e:
            warnings.warn(str(e), RuntimeWarning)
            continue

        # Atmosphere
        if atmo_source == 'merra':
            atmosphere = atmo.merra.process(overpass_date, buoy_lat, buoy_lon, verbose)
        elif atmo_source == 'narr':
            atmosphere = atmo.narr.process(overpass_date, buoy_lat, buoy_lon, verbose)
        else:
            raise ValueError('atmo_source is not one of (narr, merra)')

        # MODTRAN
        modtran_directory = '{0}/{1}_{2}'.format(settings.MODTRAN_DIR, scene_id, buoy_id)
        wavelengths, upwell_rad, gnd_reflect, transmission = modtran.process(atmosphere, buoy_lat, buoy_lon, overpass_date, modtran_directory, skin_temp)

        # LTOA calcs
        mod_ltoa_spectral = radiance.calc_ltoa_spectral(wavelengths, upwell_rad, gnd_reflect, transmission, skin_temp)

        img_ltoa = {}
        mod_ltoa = {}
        try:
            for b in bands:
                RSR_wavelengths, RSR = numpy.loadtxt(rsrs[b], unpack=True)
                img_ltoa[b] = sat.landsat.calc_ltoa(directory, metadata, buoy_lat, buoy_lon, b)
                mod_ltoa[b] = radiance.calc_ltoa(wavelengths, mod_ltoa_spectral, RSR_wavelengths, RSR)
        except RuntimeError as e:
            warnings.warn(str(e), RuntimeWarning)
            continue

        error = error_bar.error_bar(scene_id, buoy_id, skin_temp, 0.305, overpass_date, buoy_lat, buoy_lon, rsrs, bands)

        data[buoy_id] = (buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, error, img_ltoa, overpass_date)

    return data


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compute and compare the radiance values of \
     a landsat image to the propogated radiance of a NOAA buoy, using atmospheric data and MODTRAN. ')

    parser.add_argument('scene_id', help='LANDSAT or MODIS scene ID. Examples: LC08_L1TP_017030_20170703_20170715_01_T1, MOD021KM.A2011154.1650.006.2014224075807.hdf')
    parser.add_argument('-a', '--atmo', default='merra', choices=['merra', 'narr'], help='Choose atmospheric data source, choices:[narr, merra].')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    parser.add_argument('-s', '--save', default='results.txt')
    parser.add_argument('-w', '--warnings', default=False, action='store_true')
    parser.add_argument('-d', '--bands', nargs='+')

    args = parser.parse_args()

    if not args.warnings:
        warnings.filterwarnings("ignore")

    if args.scene_id[0:3] in ('LC8', 'LC0'):   # Landsat 8
        bands = [int(b) for b in args.bands] if args.bands is not None else [10, 11]
        ret = landsat8(args.scene_id, args.atmo, args.verbose, bands)

    elif args.scene_id[0:3] == 'MOD':   # Modis
        bands = [int(b) for b in args.bands] if args.bands is not None else [31, 32]
        ret = modis(args.scene_id, args.atmo, args.verbose, bands)

    else:
        raise ValueError('Scene ID is not a valid format for (landsat8, modis)')

    print('Scene_ID, Date, Buoy_ID, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod1, mod2, img1, img2, error1, error2')
    for key in ret.keys():
        buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, error, img_ltoa, date = ret[key]
        print(args.scene_id, date.strftime('%Y/%m/%d'), buoy_id, bulk_temp, skin_temp, buoy_lat, \
            buoy_lon, *mod_ltoa.values(), *img_ltoa.values(), *error.values())

    if args.save:
        with open(args.save, 'w') as f:
            print('#Scene_ID, Date, Buoy_ID, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod1, mod2, img1, img2, error1, error2', file=f, sep=', ')
            for key in ret.keys():
                buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, error, img_ltoa, date = ret[key]
                print(args.scene_id, date.strftime('%Y/%m/%d'), buoy_id, bulk_temp, skin_temp, buoy_lat, \
                    buoy_lon, *mod_ltoa.values(), *img_ltoa.values(), *error.values(), file=f, sep=', ')
