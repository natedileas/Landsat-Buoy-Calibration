import numpy
from netCDF4 import num2date

from . import (data, funcs)
from .. import (settings, interp)
from ..download import url_download


def download(date):
    """
    Download NARR Data (netCDF4 format) via ftp.

    Args:
        scene
    """
    # TODO fix narr urls to include new format strings

    date = date.strftime('%Y%m')   # YYYYMM
    narr_files = []

    for url in settings.NARR_URLS:
        url = url % date

        filename = url_download(url, settings.NARR_DIR)
        narr_files.append(filename)

    return narr_files

def process(source, date, buoy, verbose=False):
    """
    process atmospheric data, yield an atmosphere
    """
    files = download(date)

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
