import datetime
import logging
import itertools
import os
import subprocess
import sys

import numpy
import utm

import data
from .. import settings
from ..download import url_download


def download(date):
    """
    Download MERRA data via ftp.

    Args:
        cc: CalibrationController object

    Returns:
        None
    """
    # year with century, zero padded month, then full date
    # TODO fix merra url to include new format strings
    url = settings.MERRA_URL % (date.strftime('%Y'), date.strftime('%m'),
                                date.strftime('%Y%m%d'))

    filename = url_download(url, settings.MERRA_DIR)
    return filename


def read(date, atmo_data, chosen_points):
    """
    Pull out chosen data and do some basic processing.

    Args:
        date: python datetime object
        atmo_data: netcdf4 object to MERRA data
        chosen_points: indices into netcdf4 object

    Returns:
        atmo_data: shape=(7, 4, 42), units=[km, K, %, hPa]
            ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
    """
    chosen_points = numpy.array(list(chosen_points))

    latidx = tuple(chosen_points[:, 0])
    lonidx = tuple(chosen_points[:, 1])

    t1, t2 = data.closest_hours(atmo_data.variables['time'], date)

    index1 = (t1, slice(None), latidx, lonidx)
    index2 = (t2, slice(None), latidx, lonidx)

    p = numpy.array(atmo_data.variables['lev'][:])
    pressure = numpy.reshape([p]*4, (4, len(p)))

    # the .T on the end is a transpose
    temp1 = numpy.diagonal(atmo_data.variables['T'][index1], axis1=1, axis2=2).T
    temp2 = numpy.diagonal(atmo_data.variables['T'][index2], axis1=1, axis2=2).T

    rh1 = numpy.diagonal(atmo_data.variables['RH'][index1], axis1=1, axis2=2).T   # relative humidity
    rh2 = numpy.diagonal(atmo_data.variables['RH'][index2], axis1=1, axis2=2).T

    height1 = numpy.diagonal(atmo_data.variables['H'][index1], axis1=1, axis2=2).T   # height
    height2 = numpy.diagonal(atmo_data.variables['H'][index2], axis1=1, axis2=2).T

    return height1 / 1000.0, height2 / 1000.0, temp1, temp2, rh1 * 100, rh2 * 100, pressure


def calc_profile(metadata, buoy_info):
    """
    Choose points and retreive merra data from file.

    Args:
        cc: CalibrationController object

    Returns:
        data: atmospheric data, shape = (7, 4, 42)
            ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
        chosen_points_lat_lon: coordinates of the atmospheric data points
    """
    filename = download(metadata['date'])
    atmo_data = data.open_netcdf4(filename)

    # choose points
    indices, lat, lon = data.points_in_scene(metadata, atmo_data, flat=True)
    chosen_idxs, data_coor = data.choose_points(indices, lat, lon, buoy_info[1], buoy_info[2])

    # retrieve data
    raw_atmo = read(metadata['date'], atmo_data, chosen_idxs)

    # load standard atmosphere for mid-lat summer
    stan_atmo = numpy.loadtxt(settings.STAN_ATMO, unpack=True)

    interp_time = data.interpolate_time(metadata, *raw_atmo)   # interplolate in time
    atmo_profiles = data.generate_profiles(interp_time, stan_atmo, raw_atmo[6])
    atmo_profiles = numpy.asarray(atmo_profiles)

    if len(numpy.where(atmo_profiles > 1e10)[0]) != 0:
        logging.warning('No data for some points. Extrapolating.')

        bad_points = zip(*numpy.where(atmo_profiles > 1e10))

        for i in bad_points:
            profile = numpy.delete(atmo_profiles[i[0], i[1]], i[2])

            fit = numpy.polyfit(range(i[2], 5+i[2]), profile[:5], 1)   # linear extrap
            line = numpy.poly1d(fit)

            new_profile = numpy.insert(profile, 0, line(i[2]))
            atmo_profiles[i[0], i[1]] = new_profile

    interp_profile = data.bilinear_interp_space([buoy_info[1], buoy_info[2]], atmo_profiles, data_coor)
    interp_profile = numpy.asarray(interp_profile)

    return interp_profile, data_coor
