
import buoycalib


def run_all(scene_id, buoy_id, atmo_source='merra', bands=[10, 11]):
    print('Downloading Scene: {0} Bands: {1}'.format(scene_id, bands))
    scene = buoycalib.landsat.download_amazons3(scene_id, bands)

    print('Downloading Buoy: {0} '.format(buoy_id))
    buoy = buoycalib.buoy.calculate_buoy_information(scene, buoy_id)
    print(buoy)

    print('Processing Atmosphere:')
    atmosphere = buoycalib.atmo.process(atmo_source, scene, buoy)

    print('Running MODTRAN:')
    modtran_out = buoycalib.modtran.process(atmosphere, buoy.lat, buoy.lon, scene.date, scene.directory)

    print('Ltoa Spectral Calculations:')
    mod_ltoa_spectral = buoycalib.radiance.calc_ltoa_spectral(modtran_out, buoy.skin_temp)

    if 'MTL' in bands: bands.remove('MTL')   # TODO fix stupid thing here

    for b in bands:
        mod_ltoa = buoycalib.radiance.calc_ltoa(modtran_out[2], mod_ltoa_spectral, buoycalib.settings.RSR_L8[b])
        img_ltoa = buoycalib.landsat.calc_ltoa(scene, buoy.lat, buoy.lon, b)

        print('Radiance Calculation Band {0}: modeled: {1} img: {2}'.format(b, mod_ltoa, img_ltoa))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Compute and compare the radiance values of \
     a landsat image to the propogated radiance of a NOAA buoy, using atmospheric data and MODTRAN. \
    \nIf atmospheric data or landsat images need to be downloaded,\
     it will take between 5-7 minutes for NARR, and 2-3 for MERRA. If nothing need to be downloaded,\
     it will usually take less than 30 seconds for a single scene.')

    parser.add_argument('scene_id', help='LANDSAT scene ID. Examples: LC80330412013145LGN00, LE70160382012348EDC00, LT50410372011144PAC01', nargs='+')
    parser.add_argument('-b', '--buoy_id', help='NOAA Buoy ID. Example: 44009', default='')
    parser.add_argument('-a', '--atmo', default='merra', choices=['merra', 'narr'], help='Choose atmospheric data source, choices:[narr, merra].')

    args = parser.parse_args()

    for LID in args.scene_id:
        run_all(LID, args.buoy_id, args.atmo)
