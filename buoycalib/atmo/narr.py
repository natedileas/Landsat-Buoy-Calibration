import itertools
import os
import logging

from netCDF4 import num2date
import numpy

from .. import settings
from ..download import url_download
import data


def download(date):
    """
    Download NARR Data (netCDF4 format) via ftp.

    Args:
        metadata
    """
    # TODO fix narr urls to include new format strings

    date = date.strftime('%Y%m')   # YYYYMM
    narr_files = []

    for url in settings.NARR_URLS:
        url = url % date

        filename = url_download(url, settings.NARR_DIR)
        narr_files.append(filename)

    return narr_files


def read(cc, temp, height, shum, chosen_points):
    """
    Pull out chosen data and do some basic processing.

    Args:
        cc: CalibrationController object
        temp, height, shum: netcdf4 objects
        chosen_points: idices to 4 chosen points

    Returns:
        data: shape=(7, 4, 29), units=[km, K, %, torr]
            ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
    """

    chosen_points = numpy.array(list(chosen_points))
    latidx = tuple(chosen_points[:, 0])
    lonidx = tuple(chosen_points[:, 1])

    times = temp.variables['time']
    dates = num2date(times[:], times.units)
    t1, t2 = sorted(abs(dates-cc.scenedatetime).argsort()[:2])

    p = numpy.array(temp.variables['level'][:])
    pressure = numpy.reshape([p]*4, (4, len(p)))

    # the .T on the end is a transpose
    tmp_1 = numpy.diagonal(temp.variables['air'][t1, :, latidx, lonidx], axis1=1, axis2=2).T
    tmp_2 = numpy.diagonal(temp.variables['air'][t2, :, latidx, lonidx], axis1=1, axis2=2).T

    ght_1 = numpy.diagonal(height.variables['hgt'][t1, :, latidx, lonidx], axis1=1, axis2=2).T / 1000.0   # convert m to km
    ght_2 = numpy.diagonal(height.variables['hgt'][t2, :, latidx, lonidx], axis1=1, axis2=2).T / 1000.0

    shum_1 = numpy.diagonal(shum.variables['shum'][t1, :, latidx, lonidx], axis1=1, axis2=2).T
    shum_2 = numpy.diagonal(shum.variables['shum'][t2, :, latidx, lonidx], axis1=1, axis2=2).T
    rhum_1 = data.convert_sh_rh(shum_1, tmp_1, pressure)
    rhum_2 = data.convert_sh_rh(shum_2, tmp_2, pressure)

    return ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressure


def calc_profile(metadata, buoy):
    """
    Choose points and retreive narr data from file.

    Args:
        cc: CalibrationController object

    Returns:
        data: atmospheric data, shape = (7, 4, 29)
            ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
        narr_coor: coordinates of the atmospheric data points
    """
    temp_file, height_file, shum_file = download(metadata['date'])

    temp = data.open_netcdf4(temp_file)
    height = data.open_netcdf4(height_file)
    shum = data.open_netcdf4(shum_file)

    # choose narr points
    indices, lat, lon = data.points_in_scene(metadata, temp)
    chosen_idxs, narr_coor = data.choose_points(indices, lat, lon, metadata['buoy_location'])

    # read in NARR data
    narr_data = read(metadata, temp, height, shum, chosen_idxs)

    # load standard atmosphere for mid-lat summer
    stan_atmo = numpy.loadtxt(settings.STAN_ATMO, unpack=True)

    interp_time = data.interpolate_time(metadata, *data)   # interplolate in time
    atmo_profiles = numpy.asarray(atmo_data.generate_profiles(interp_time, stan_atmo, data[6]))

    interp_profile = atmo_data.offset_interp_space(metadata['buoy_location'], atmo_profiles, narr_coor)

    if len(numpy.where(atmo_profiles > 32765)[0]) != 0:
        print(numpy.where(atmo_profiles > 32765))
        logging.warning('No data for some points. Extrapolating.')

        bad_points = zip(*numpy.where(atmo_profiles > 32765))

        for i in bad_points:
            profile = numpy.delete(atmo_profiles[i[0], i[1]], i[2])

            fit = numpy.polyfit(range(i[2], 5+i[2]), profile[:5], 1)   # linear extrap
            line = numpy.poly1d(fit)

            new_profile = numpy.insert(profile, 0, line(i[2]))
            atmo_profiles[i[0], i[1]] = new_profile

    return interp_profile, narr_coor
