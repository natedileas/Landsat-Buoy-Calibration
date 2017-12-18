
from buoycalib import (sat, buoy, atmo, radiance, modtran, settings)


def run_all(scene_id, buoy_id, atmo_source='merra', verbose=False, bands=[10, 11]):
    
    # satelite download
    if scene_id[0:3] == 'LC8':   # Landsat 8
        # [:] thing is to shorthand to make a shallow copy
        overpass_date, directory, metadata = sat.landsat.download(scene_id, bands[:])
        rsrs = {b:settings.RSR_L8[b] for b in bands}

    elif scene_id[0:3] == 'MOD':   # Modis
        overpass_date, directory, metadata, files = sat.modis.download(scene_id)
        rsrs = {b:settings.RSR_MODIS[b] for b in bands}

    else:
        raise ValueError('Scene ID is not a valid format for (landsat8, modis)')

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
    modtran_out = modtran.process(atmosphere, buoy_lat, buoy_lon, overpass_date, directory)

    # LTOA calcs
    print('Ltoa Spectral Calculations:')
    mod_ltoa_spectral = radiance.calc_ltoa_spectral(modtran_out, skin_temp)

    if 'MTL' in bands: bands.remove('MTL')   # TODO fix stupid thing here

    for b in bands:
        mod_ltoa = radiance.calc_ltoa(modtran_out[2], mod_ltoa_spectral, rsrs[b])
        img_ltoa = sat.landsat.calc_ltoa(directory, metadata, buoy_lat, buoy_lon, b)

        print('Radiance Calculation Band {0}: modeled: {1} img: {2}'.format(b, mod_ltoa, img_ltoa))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compute and compare the radiance values of \
     a landsat image to the propogated radiance of a NOAA buoy, using atmospheric data and MODTRAN. \
    \nIf atmospheric data or landsat images need to be downloaded,\
     it will take between 5-7 minutes for NARR, and 2-3 for MERRA. If nothing need to be downloaded,\
     it will usually take less than 30 seconds for a single scene.')

    parser.add_argument('scene_id', help='LANDSAT scene ID. Examples: LC80330412013145LGN00, LE70160382012348EDC00, LT50410372011144PAC01', nargs='+')
    parser.add_argument('buoy_id', help='NOAA Buoy ID. Example: 44009')
    parser.add_argument('-a', '--atmo', default='merra', choices=['merra', 'narr'], help='Choose atmospheric data source, choices:[narr, merra].')
    parser.add_argument('-v', '--verbose', default=False, action='store_true')

    args = parser.parse_args()

    for LID in args.scene_id:
        run_all(LID, args.buoy_id, args.atmo, args.verbose)
