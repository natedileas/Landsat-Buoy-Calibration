import numpy

from . import (narr, merra, data, funcs, idw)
from .. import settings

def process(source, date, buoy):
    """
    process atmospheric data, yield an atmosphere
    """
    mod = narr if source == 'narr' else merra
    
    files = mod.download(date)

    if source == 'narr':
        temp_file, height_file, shum_file = files
        temp_netcdf = data.open_netcdf4(temp_file)
        height_netcdf = data.open_netcdf4(height_file)
        shum_netcdf = data.open_netcdf4(shum_file)

        # choose points
        lat = temp_netcdf.variables['lat'][:]
        lon = temp_netcdf.variables['lon'][:]

        chosen_idxs, data_coor = funcs.choose_points(lat, lon, buoy.lat, buoy.lon)

        h, t, rh, p = mod.read(date, temp_netcdf, height_netcdf, shum_netcdf, chosen_idxs)
        
    elif source == 'merra':
        filename = files
        atmo_data = data.open_netcdf4(filename)

        # choose points
        lat = atmo_data.variables['lat'][:]
        lon = atmo_data.variables['lon'][:]
        lat = numpy.stack([lat]*lon.shape[0], axis=0)
        lon = numpy.stack([lon]*lat.shape[1], axis=1)
        chosen_idxs, data_coor = funcs.choose_points(lat, lon, buoy.lat, buoy.lat)

        h, t, rh, p = mod.read(date, atmo_data, chosen_idxs)

    else:
        raise ValueError('Source must be one of (\'narr\' or \'merra\'): {0}'.format(source))

    # interpolate in space, now they are shape (1, N)
    # total is (4, N)

    height = idw.idw(h, data_coor, [buoy.lat, buoy.lon])
    temp = idw.idw(t, data_coor, [buoy.lat, buoy.lon])
    relhum = idw.idw(rh, data_coor, [buoy.lat, buoy.lon])
    press = idw.idw(p, data_coor, [buoy.lat, buoy.lon])

    """alpha, beta = data.calc_interp_weights(data_coor, [buoy.lat, buoy.lon])
                if numpy.isinf(alpha) or numpy.isinf(beta):
                    height, temp, helhum, press = data.bilinear_interp_space([buoy.lat, buoy.lon], (h, t, rh, p), data_coor)
                else:
                    height = data.use_interp_weights(h, alpha, beta)
                    temp = data.use_interp_weights(t, alpha, beta)
                    relhum = data.use_interp_weights(rh, alpha, beta)
                    press = data.use_interp_weights(p, alpha, beta)"""

    #print(data_coor, [buoy.lat, buoy.lon])
    # load standard atmosphere for mid-lat summer
    # TODO evaluate standard atmo validity, add different ones for different TOY?
    stan_atmo = numpy.loadtxt(settings.STAN_ATMO, unpack=True)
    stan_height, stan_press, stan_temp, stan_relhum = stan_atmo
    # add standard atmo above cutoff index
    cutoff_idx = numpy.abs(stan_press - press[-1]).argmin()
    height = numpy.append(height, stan_height[cutoff_idx:])
    press = numpy.append(press, stan_press[cutoff_idx:])
    temp = numpy.append(temp, stan_temp[cutoff_idx:])
    relhum = numpy.append(relhum, stan_relhum[cutoff_idx:])

    # TODO add buoy stuff to bottom of atmosphere

    return height, press, temp, relhum