import itertools
import os
import logging

from netCDF4 import Dataset, num2date
import numpy
import utm

import image_processing as img_proc
import atmo_data
import misc_functions as funcs
import settings
from ..download import url_download


def download(metadata):
    """
    Download NARR Data (netCDF4 format) via ftp.

    Args:
        metadata
    """
    # TODO fix narr urls to include new format strings

    date = metadata['date'].strftime('%Y%m')   # YYYYMM
    metadata['narr_files'] = []

    for url in settings.NARR_URLS:
        url = url % date

        filename = url_download(url, settings.NARR_DIR)
        metadata['narr_files'].append(filename)

    return metadata


def open_(metadata):
    """
    Open NARR files (netCDF4 format).

    Args:
        cc: CalibrationController object

    Returns:
        data: list of references to variables stored in NARR data files.
            [temp, height, specific_humidity]

    Raises:
        IOError: if files do not exist at the expected path
    """
    data = []

    for data_file in metadata['narr_files']:

        if not os.path.isfile(data_file):
            raise IOError('NARR Data is not at path: {0}'.format(data_file))

        data.append(Dataset(data_file, "r", format="NETCDF4"))

    return data


def get_points(metadata, data):
    """
    Get points which lie inside the landsat image.

    Args:
        metadata: landsat metadata, for edges
        data: netcdf4 object with NARR data

    Returns:
        indexs, lat, lon: indexs and corresponding lat and lon for the points
        which lie inside the landsat image
    """

    lat = data.variables['lat'][:]
    lon = data.variables['lon'][:]

    # define corners
    UL_lat = metadata['CORNER_UL_LAT_PRODUCT'] + 0.5
    UL_lon = metadata['CORNER_UL_LON_PRODUCT'] - 0.5
    LR_lat = metadata['CORNER_LR_LAT_PRODUCT'] - 0.5
    LR_lon = metadata['CORNER_LR_LON_PRODUCT'] + 0.5

    # pull out points that lie within the corners (only works for NW quadrant)
    indexs = numpy.where((lat < UL_lat) & (lat > LR_lat) & (lon > UL_lon) &
                         (lon < LR_lon))

    return indexs, lat, lon


def choose_points(in_landsat, lat, lon, buoy_coors):
    """
    Choose the four points which will be used.

    Args:
        in_landsat, lat, lon: points which lie inside, in lat and lon
            as well as indices into the netcdf4 variables.
        buoy_coors: lat, lon where the buoy is

    Returns:
        chosen indices, and chosen lats and lons
    """

    latvalues = lat[in_landsat]
    lonvalues = lon[in_landsat]

    buoy_x, buoy_y, buoy_zone_num, buoy_zone_let = utm.from_latlon(*buoy_coors)
    distances = []

    for i in range(len(latvalues)):
        east, north, zone_num, zone_let = utm.from_latlon(latvalues[i], lonvalues[i])

        dist = atmo_data.distance_in_utm(east, north, buoy_x, buoy_y)
        distances.append(dist)

    in_landsat = zip(in_landsat[0], in_landsat[1])
    narr_dict = zip(distances, latvalues, lonvalues, numpy.asarray(in_landsat, dtype=object))
    sorted_points = sorted(narr_dict)

    for chosen_points in itertools.combinations(sorted_points, 4):
        chosen_points = numpy.asarray(chosen_points)

        if funcs.is_square_test(chosen_points[:,1:3]) is True:
            break

    return chosen_points[:, 3], chosen_points[:, 1:3]


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
    rhum_1 = atmo_data.convert_sh_rh(shum_1, tmp_1, pressure)
    rhum_2 = atmo_data.convert_sh_rh(shum_2, tmp_2, pressure)

    return ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressure


def calc_profile(metadata):
    """
    Choose points and retreive narr data from file.

    Args:
        cc: CalibrationController object

    Returns:
        data: atmospheric data, shape = (7, 4, 29)
            ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
        narr_coor: coordinates of the atmospheric data points
    """

    temp, height, shum = open_(metadata)

    # choose narr points
    narr_indices, lat, lon = get_points(metadata, temp)
    chosen_idxs, narr_coor = choose_points(narr_indices, lat, lon, metadata['buoy_location'])

    # read in NARR data
    data = read(metadata, temp, height, shum, chosen_idxs)

    # load standard atmosphere for mid-lat summer
    stan_atmo = numpy.loadtxt(settings.STAN_ATMO, unpack=True)

    interp_time = atmo_data.interpolate_time(metadata, *data)   # interplolate in time
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
