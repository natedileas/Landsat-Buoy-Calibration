import numpy

from . import (modtran, atmo, sat, radiance, settings)
from .atmo import merra

def error_bar(scene_id, buoy_id, skin_temp, skin_temp_std, overpass_date, buoy_lat, buoy_lon, rsrs, bands):
    atmos = merra.error_bar_atmos(overpass_date, buoy_lat, buoy_lon)

    modeled_ltoas = {b:[] for b in bands}
    for temp in [skin_temp+skin_temp_std, skin_temp-skin_temp_std]:
        for i, atmo in enumerate(atmos):
            modtran_directory = '{0}/{1}_{2}_{3}_{4}'.format(settings.MODTRAN_DIR, scene_id, buoy_id, temp, i)
            wavelengths, upwell_rad, gnd_reflect, transmission = modtran.process(atmo, buoy_lat, buoy_lon, overpass_date, modtran_directory, temp)
            mod_ltoa_spectral = radiance.calc_ltoa_spectral(wavelengths, upwell_rad, gnd_reflect, transmission, skin_temp)

            for b in bands:
                if scene_id[0:3] == 'MOD':
                    RSR_wavelengths, RSR = sat.modis.load_rsr(rsrs[b])
                elif scene_id[0:3] in ('LC8', 'LC0'):
                    RSR_wavelengths, RSR = numpy.loadtxt(rsrs[b], unpack=True)

                modeled_ltoas[b].append(radiance.calc_ltoa(wavelengths, mod_ltoa_spectral, RSR_wavelengths, RSR))

    error = {b:numpy.asarray(modeled_ltoas[b]).std() for b in modeled_ltoas}
    return error