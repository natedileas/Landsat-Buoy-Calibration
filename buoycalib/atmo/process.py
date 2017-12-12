import numpy
from netCDF4 import num2date

from . import (narr, merra, data, funcs)
from .. import (settings, interp)

def process(source, date, buoy, verbose=False):
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

        latidx = tuple(chosen_idxs[0])
        lonidx = tuple(chosen_idxs[1])

        t1, t2 = data.closest_hours(temp_netcdf.variables['time'][:],
                                    temp_netcdf.variables['time'].units, date)

        t1_dt = num2date(temp_netcdf.variables['time'][t1], temp_netcdf.variables['time'].units)
        t2_dt = num2date(temp_netcdf.variables['time'][t2], temp_netcdf.variables['time'].units)

        index1 = (t1, slice(None), latidx, lonidx)
        index2 = (t2, slice(None), latidx, lonidx)

        press = numpy.array(temp_netcdf.variables['level'][:])

        # the .T on the end is a transpose
        temp1 = numpy.diagonal(temp_netcdf.variables['air'][index1], axis1=1, axis2=2).T
        temp2 = numpy.diagonal(temp_netcdf.variables['air'][index2], axis1=1, axis2=2).T

        height1 = numpy.diagonal(height_netcdf.variables['hgt'][index1], axis1=1, axis2=2).T / 1000.0   # convert m to km
        height2 = numpy.diagonal(height_netcdf.variables['hgt'][index2], axis1=1, axis2=2).T / 1000.0

        shum_1 = numpy.diagonal(shum_netcdf.variables['shum'][index1], axis1=1, axis2=2).T
        shum_2 = numpy.diagonal(shum_netcdf.variables['shum'][index2], axis1=1, axis2=2).T
        rhum1 = data.convert_sh_rh(shum_1, temp1, press)
        rhum2 = data.convert_sh_rh(shum_2, temp2, press)

    elif source == 'merra':
        filename = files
        atmo_data = data.open_netcdf4(filename)

        # choose points
        lat = atmo_data.variables['lat'][:]
        lon = atmo_data.variables['lon'][:]
        lat = numpy.stack([lat]*lon.shape[0], axis=0)
        lon = numpy.stack([lon]*lat.shape[1], axis=1)
        chosen_idxs, data_coor = funcs.choose_points(lat, lon, buoy.lat, buoy.lon)

        latidx = tuple(chosen_idxs[0])
        lonidx = tuple(chosen_idxs[1])

        t1, t2 = data.closest_hours(atmo_data.variables['time'][:].data,
                                    atmo_data.variables['time'].units, date)
        t1_dt = num2date(atmo_data.variables['time'][t1], atmo_data.variables['time'].units)
        t2_dt = num2date(atmo_data.variables['time'][t2], atmo_data.variables['time'].units)

        index1 = (t1, slice(None), latidx, lonidx)
        index2 = (t2, slice(None), latidx, lonidx)

        press = numpy.array(atmo_data.variables['lev'][:])

        # the .T on the end is a transpose
        temp1 = numpy.diagonal(atmo_data.variables['T'][index1], axis1=1, axis2=2).T
        temp2 = numpy.diagonal(atmo_data.variables['T'][index2], axis1=1, axis2=2).T

        rhum1 = numpy.diagonal(atmo_data.variables['RH'][index1], axis1=1, axis2=2).T   # relative humidity
        rhum2 = numpy.diagonal(atmo_data.variables['RH'][index2], axis1=1, axis2=2).T

        height1 = numpy.diagonal(atmo_data.variables['H'][index1], axis1=1, axis2=2).T / 1000.0   # height
        height2 = numpy.diagonal(atmo_data.variables['H'][index2], axis1=1, axis2=2).T / 1000.0

    else:
        raise ValueError('Source must be one of (\'narr\' or \'merra\'): {0}'.format(source))

    # interpolate in time, now they are shape (4, N)
    t = interp.interp_time(date, temp1, temp2, t1_dt, t2_dt)
    h = interp.interp_time(date, height1, height2, t1_dt, t2_dt)
    rh = interp.interp_time(date, rhum1, rhum2, t1_dt, t2_dt)
    
    # interpolate in space, now they are shape (1, N)
    height = interp.idw(h, data_coor, [buoy.lat, buoy.lon])
    temp = interp.idw(t, data_coor, [buoy.lat, buoy.lon])
    relhum = interp.idw(rh, data_coor, [buoy.lat, buoy.lon])

    # get rid of nans 
    # TODO is this still necesary?
    #cutoff = height[numpy.isnan(height)].shape[0]

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

    if verbose:
        # send out plots and stuff
        stuff = numpy.asarray([height, press, temp, relhum]).T
        h = 'Height [km], Pressure[kPa], Temperature[k], Relative_Humidity[0-100]' + '\nCoordinates: {0} Buoy:{1}'.format(data_coor, buoy)
        
        numpy.savetxt('atmosphere_{0}_{1}_{2}.txt'.format(source, date.strftime('%Y%m%d'), buoy.id), stuff, fmt='%7.2f, %7.2f, %7.2f, %7.2f', header=h)

    return height, press, temp, relhum