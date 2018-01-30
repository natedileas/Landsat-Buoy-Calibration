
from buoycalib import (sat, buoy, atmo, radiance, modtran, settings)
import numpy


def modis(scene_id, buoy_id, atmo_source='merra', verbose=False, bands=[31, 32]):
    overpass_date, directory, metadata, [granule_filepath, geo_ref_filepath] = sat.modis.download(scene_id)
    rsrs = {b:settings.RSR_MODIS[b] for b in bands}

    buoy_file = buoy.download(buoy_id, overpass_date)
    buoy_lat, buoy_lon, buoy_depth, lower_atmo = buoy.info(buoy_id, buoy_file, overpass_date)
    skin_temp, bulk_temp = buoy.skin_temp(buoy_file, overpass_date, buoy_depth)
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
    wavelengths, upwell_rad, gnd_reflect, transmission = modtran.process(atmosphere, buoy_lat, buoy_lon, overpass_date, directory)

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


def landsat8(scene_id, buoy_id, atmo_source='merra', verbose=False, bands=[10, 11]):
    
    # satelite download
    # [:] thing is to shorthand to make a shallow copy
    overpass_date, directory, metadata = sat.landsat.download(scene_id, bands[:])
    rsrs = {b:settings.RSR_L8[b] for b in bands}

    # Buoy Stuff
    buoy_file = buoy.download(buoy_id, overpass_date)
    buoy_lat, buoy_lon, buoy_depth, lower_atmo = buoy.info(buoy_id, buoy_file, overpass_date)
    skin_temp, bulk_temp = buoy.skin_temp(buoy_file, overpass_date, buoy_depth)
    print('Buoy {0}: skin_temp: {1} lat: {2} lon:{3}'.format(buoy_id, skin_temp, buoy_lat, buoy_lon))

    # Atmosphere
    if atmo_source == 'merra':
        atmosphere = atmo.merra.process(overpass_date, buoy_lat, buoy_lon, verbose)
    elif atmo_source == 'narr':
        atmosphere = atmo.narr.process(overpass_date, buoy_lat, buoy_lon, verbose)
    else:
        raise ValueError('atmo_source is not one of (narr, merra)')

    # MODTRAN
    print('Running MODTRAN:')
    wavelengths, upwell_rad, gnd_reflect, transmission = modtran.process(atmosphere, buoy_lat, buoy_lon, overpass_date, directory)

    # LTOA calcs
    print('Ltoa Spectral Calculations:')
    mod_ltoa_spectral = radiance.calc_ltoa_spectral(wavelengths, upwell_rad, gnd_reflect, transmission, skin_temp)

    print(rsrs)

    img_ltoa = {}
    mod_ltoa = {}
    for b in bands:
        RSR_wavelengths, RSR = numpy.loadtxt(rsrs[b], unpack=True)
        img_ltoa[b] = sat.landsat.calc_ltoa(directory, metadata, buoy_lat, buoy_lon, b)
        mod_ltoa[b] = radiance.calc_ltoa(wavelengths, mod_ltoa_spectral, RSR_wavelengths, RSR)

    print('RADIANCE modeled: {1} img: {2}'.format(b, mod_ltoa, img_ltoa))

    return mod_ltoa, img_ltoa


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compute and compare the radiance values of \
     a landsat image to the propogated radiance of a NOAA buoy, using atmospheric data and MODTRAN. \
    \nIf atmospheric data or landsat images need to be downloaded,\
     it will take between 5-7 minutes for NARR, and 2-3 for MERRA. If nothing need to be downloaded,\
     it will usually take less than 30 seconds for a single scene.')

    parser.add_argument('scene_id', help='LANDSAT scene ID. Examples: LC80330412013145LGN00, LE70160382012348EDC00, LT50410372011144PAC01')
    parser.add_argument('buoy_id', help='NOAA Buoy ID. Example: 44009')
    parser.add_argument('-a', '--atmo', default='merra', choices=['merra', 'narr'], help='Choose atmospheric data source, choices:[narr, merra].')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')
    parser.add_argument('-b', '--bands', default=[10, 11], nargs='+')

    args = parser.parse_args()
    args.bands = [int(b) for b in args.bands]

    if args.scene_id[0:3] == 'LC8':   # Landsat 8
        ret = landsat8(args.scene_id, args.buoy_id, args.atmo, args.verbose, args.bands)

    elif args.scene_id[0:3] == 'MOD':   # Modis
        ret = modis(args.scene_id, args.buoy_id, args.atmo, args.verbose, args.bands)

    else:
        raise ValueError('Scene ID is not a valid format for (landsat8, modis)')
