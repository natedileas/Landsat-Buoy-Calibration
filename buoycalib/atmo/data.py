import math
import os
import itertools

import numpy
from netCDF4 import Dataset, num2date
import utm

import funcs


def open_netcdf4(filename):
    """
    Open data file in netCDF4 format.

    Args:
        filename: file to open

    Returns:
        rootgrp: data reference to variables stored in data file.

    Raises:
        IOError: if file does not exist at the expected path
    """
    if not os.path.isfile(filename):
        raise IOError('Data file not at path: {0}'.format(filename))

    rootgrp = Dataset(filename, "r", format="NETCDF4")
    return rootgrp


def points_in_scene(metadata, rootgrp, flat=False):
    """
    Get points which lie inside the landsat image.

    Args:
        metadata: landsat metadata, for edges
        rootgrp: netcdf4 object with NARR/MERRA data

    Returns:
        indexs, lat, lon: indexs and corresponding lat and lon for the points
        which lie inside the landsat image
    """

    lat = rootgrp.variables['lat'][:]
    lon = rootgrp.variables['lon'][:]

    if flat:
        lat = numpy.stack([lat]*lon.shape[0], axis=0)
        lon = numpy.stack([lon]*lat.shape[1], axis=1)

    # define corners
    ul_lat = metadata['CORNER_UL_LAT_PRODUCT'] + 0.5
    ul_lon = metadata['CORNER_UL_LON_PRODUCT'] - 0.5
    lr_lat = metadata['CORNER_LR_LAT_PRODUCT'] - 0.5
    lr_lon = metadata['CORNER_LR_LON_PRODUCT'] + 0.5

    # pull out points that lie within the corners (only works for NW quadrant)
    # TODO make better, make work for all quadrants
    indexs = numpy.where((lat < ul_lat) & (lat > lr_lat) & (lon > ul_lon) &
                         (lon < lr_lon))

    return indexs, lat, lon


def choose_points(in_landsat, lat, lon, buoy_lat, buoy_lon):
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

    buoy_x, buoy_y, buoy_zone_num, __ = utm.from_latlon(buoy_lat, buoy_lon)
    distances = []

    for i in range(len(latvalues)):
        east, north, zone_num, zone_let = utm.from_latlon(latvalues[i], lonvalues[i])

        dist = distance_in_utm(east, north, buoy_x, buoy_y)
        distances.append(dist)

    in_landsat = zip(in_landsat[0], in_landsat[1])
    narr_dict = zip(distances, latvalues, lonvalues, numpy.asarray(in_landsat, dtype=object))
    sorted_points = sorted(narr_dict)

    for chosen_points in itertools.combinations(sorted_points, 4):
        chosen_points = numpy.asarray(chosen_points)

        if funcs.is_square_test(chosen_points[:,1:3]) is True:
            break

    return chosen_points[:, 3], chosen_points[:, 1:3]


def closest_hours(time_data, time_units, date):
    dates = num2date(time_data, time_units)
    t1, t2 = sorted(abs(dates - date).argsort()[:2])

    return t1, t2


def convert_sh_rh(spec_hum, temp_k, pressure):
    """
    Converts specific humidity to relative humidity.

    Args:
        spec_hum: specific humidity
        temp_k: temperature, in kelvin
        pressure: pressure, in mB

    Returns:
        rel_hum: relative humidity, (1d numpy array)

    Notes:
        http://earthscience.stackexchange.com/questions/2360/how-do-i-convert-specific-humidity-to-relative-humidity
    """
    # TODO add units to docstring and formulas

    temp_k = numpy.asarray(temp_k, dtype=numpy.float64)

    # convert input variables
    temp_c = temp_k - 273.15   # convert to celcius from kelvin

    # compute relative humidity
    a = (17.67 * temp_c) / (temp_k - 29.65)

    rel_hum = 26.3 * pressure * spec_hum * (1 / numpy.exp(a))

    return rel_hum


def dewpoint_temp(temp, relhum):
    """
    Calculates dewpoint temperature from temp and humidity.

    Args:
        temp: temperature, in celcius (1d numpy array)
        relhum: relative humidity, in percent (0-100), (1d numpy array)

    Returns:
        dewpoint temperature, in celcius (1d numpy array)

    Notes:
        source:http://climate.envsci.rutgers.edu/pdf/LawrenceRHdewpointBAMS.pdf
    """
    return temp - ((100 - relhum) / 5)   # kelvin


def calc_rh(atmp, dewpoint):
    """
    Calculate relative humidity from temperature and dewpoint.

    Args:
        atmp: air temperature [C]
        depoint: dewpoint temperature [C]

    Returns:
        rh: relative humidity [%]

    Notes:
        http://andrew.rsmas.miami.edu/bmcnoldy/Humidity.html
    """
    c1 = 17.625
    c2 = 243.04

    rh = 100 * math.exp((c1*dewpoint)/(c2+dewpoint)) / math.exp((c1*atmp)/(c2+atmp))
    return rh


def convert_geopotential_geometric(geopotential, lat):
    """
    Convert array of geopotential heights to geometric heights.

    Args:
        geopotential: Geopotential Height, i.e. height measured without acconting for latititude
        lat: latitude

    Returns:
        geometric height: height measured from sea level, accounting for latititude

    Notes:
        source: http://www.ofcm.gov/fmh3/pdf/12-app-d.pdf
        http://gis.stackexchange.com/questions/20200/how-do-you-compute-the-earths-radius-at-a-given-geodetic-latitude
    """
    radlat = (lat * math.pi) / 180.0   # convert latitiude to radians

    # gravity at latitude
    grav_lat = 9.80616 * (1 - 0.002637 * numpy.cos(2 * radlat) + 0.0000059 * numpy.power(numpy.cos(2 * radlat), 2))

    # radius of earth at latitude: R(f)^2 = ( (a^2 cos(f))^2 + (b^2 sin(f))^2 ) / ( (a cos(f))^2 + (b sin(f))^2 )
    R_max = 6378.137    # km
    R_min = 6356.752    # km

    part1 = numpy.power((R_max ** 2) * numpy.cos(radlat), 2)
    part2 = numpy.power((R_min ** 2) * numpy.sin(radlat), 2) 
    part3 = numpy.power(R_max * numpy.cos(radlat), 2)
    part4 = numpy.power(R_min * numpy.sin(radlat), 2)
    R_lat = numpy.sqrt((part1 + part2) / (part3 + part4))

    # ratio of average gravity to estimated gravity
    grav_ratio = grav_lat * R_lat / 9.80665   #average gravity

    # calculate geometric height
    geometric_height = [[0]]*4
    for i in range(4):
        geometric_height[i] = ((R_lat[i] * geopotential[i]) / numpy.absolute(grav_ratio[i] - geopotential[i]))

    return numpy.asarray(geometric_height)

 
def distance_in_utm(e1, n1, e2, n2):
    """
    Calculate distance between 2 sets of UTM coordinates.

    Args:
        e1: east value for point 1
        n1: north value for point 1
        e2: east value for point 2
        n2: north value for point 2

    Returns:
        d: distance (in UTM space) between point 1 and 2
    """
    s = 0.9996    # scale factor
    r = 6378137.0    # Earth radius

    SR1 = s / (math.cos(e1 / r))
    SR2 = s / (math.cos(((e2 - e1) / 6) / r))
    SR3 = s / (math.cos(e2 / r))

    Edist = ((e2 - e1) / 6) * (SR1 + 4 * SR2 + SR3)

    dist = math.sqrt(Edist**2 + (n2 - n1)**2)

    return dist

def interpolate_time(metadata, h1, h2, t1, t2, r1, r2, p):
    """
    Interpolate in time. 7 profiles -> 4 profiles.

    Args:
        metadata:
        h1, h2: height
        t1, t2: temperature
        r1, r2: realtive humidity
        p: pressure

    Returns:
        height, rhum, temp: all the parts of the profile

    Notes:
        Credit: Monica Cook.
    """
    # determine three hour-increment before and after scene center scan time
    # TODO replace with python datetime methods
    time = metadata['SCENE_CENTER_TIME'].replace('"', '')
    hour = int(time[0:2])
    minute = int(time[3:5])
    second = int(time[6:8])

    date = metadata['DATE_ACQUIRED']
    year = int(date[0:4])
    month = int(date[5:7])
    day = int(date[8:10])

    rem1 = hour % 3
    rem2 = 3 - rem1
    hour1 = hour - rem1
    hour2 = hour + rem2

    # round to nearest minute
    if second > 30: minute = minute + 100

    # convert hour-min acquisition time to decimal time
    time = hour + minute / 60.0

    # interpolate in time
    height = h1 + (time-hour1) * ((h2 - h1)/(hour2 - hour1))
    rhum = r1 + (time-hour1) * ((r2 - r1)/(hour2 - hour1))
    temp = t1 + (time-hour1) * ((t2 - t1)/(hour2 - hour1))

    return height, rhum, temp


def offset_interp_space(buoy_coor, atmo_profiles, narr_coor):
    """
    Interpolate in space between the 4 profiles with an offset algorithm.

    Args:
        buoy_coor: coordinates to interpolate to
        atmo_profiles: data to interpolate
        narr_coor: coordinates to interpolate from

    Returns:
        the interpolated profile
    """
    atmo_profiles = numpy.array(atmo_profiles)
    length = numpy.shape(atmo_profiles)[2]
    atmo_profiles = numpy.array(atmo_profiles[:, :length])
    narr_coor = numpy.asarray(narr_coor, dtype=float).round(8)

    alpha, beta = calc_interp_weights(narr_coor, buoy_coor)

    if abs(alpha) > 100 or abs(beta) > 100:
        alpha, beta = calc_interp_weights(numpy.absolute(narr_coor), numpy.absolute(buoy_coor))

    height = use_interp_weights(atmo_profiles[:, 0], alpha, beta)
    press = use_interp_weights(atmo_profiles[:, 1], alpha, beta)
    temp = use_interp_weights(atmo_profiles[:, 2], alpha, beta)
    relhum = use_interp_weights(atmo_profiles[:, 3], alpha, beta)

    return height, press, temp, relhum


def calc_interp_weights(interp_from, interp_to):
    """
    Calculate weights for the offset bilinear interpolation  of 4 points.

    Args:
        interp_from: coordinates to interpolate from
        interp_to: coordinates to interpolate to

    Returns:
        alpha, beta: weights to use with use_interp_weights()

    Notes:
        this function is intended to be paired with use_interp_weights().
        Source: 
    """
    a = -interp_from[0,0] + interp_from[2,0]
    b = -interp_from[0,0] + interp_from[1,0]
    c = interp_from[0,0] - interp_from[1,0] - interp_from[2,0] + interp_from[3,0]
    d = interp_to[0] - interp_from[0,0]

    e = -interp_from[0,1] + interp_from[2,1]
    f = -interp_from[0,1] + interp_from[1,1]
    g = interp_from[0,1] - interp_from[1,1] - interp_from[2,1] + interp_from[3,1]
    h = interp_to[1] - interp_from[0,1]

    i = math.sqrt(abs(-4*(c*e - a*g)*(d*f - b*h) + (b*e - a*f + d*g - c*h)**2))

    alpha = -(b*e - a*f + d*g - c*h + i)/(2*c*e - 2*a*g)
    beta  = -(b*e - a*f - d*g + c*h + i)/(2*c*f - 2*b*g)

    return alpha, beta


def use_interp_weights(array, alpha, beta):
    """ Calculate the offset bilinear interpolation  of 4 points. """
    return ((1 - alpha) * ((1 - beta) * array[0] + beta * array[1]) + \
            alpha * ((1 - beta) * array[2] + beta * array[3]))


def bilinear_interp_space(buoy_coor, atmo_profiles, data_coor):
    """
    Interpolate in space between the 4 profiles.

    Args:
        buoy_coor: coordinates to interpolate to
        atmo_profiles: data to interpolate
        data_coor: coordinates to interpolate from

    Returns:
        the interpolated profile
    """
    # shape of atmo profiles - 4 x 4 x X
    #                     points x data type x layers
    atmo_profiles = numpy.array(atmo_profiles)
    length = numpy.shape(atmo_profiles)[2]
    atmo_profiles = numpy.array(atmo_profiles[:,:length])
    data_coor = list(data_coor)

    height_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,0,:]) for i in range(4)]
    height = bilinear_interpolation(buoy_coor[0], buoy_coor[1], height_points)

    press_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,1,:]) for i in range(4)]
    press = bilinear_interpolation(buoy_coor[0], buoy_coor[1], press_points)

    temp_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,2,:]) for i in range(4)]
    temp = bilinear_interpolation(buoy_coor[0], buoy_coor[1], temp_points)

    relhum_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,3,:]) for i in range(4)]
    relhum = bilinear_interpolation(buoy_coor[0], buoy_coor[1], relhum_points)

    return [height, press, temp, relhum]


def bilinear_interpolation(x, y, points):
    """Interpolate (x,y) from values associated with four points.

    Args:
        x, y: point to interpolate to
        points: The four points are a list of four triplets:  (x, y, value).
        The four points can be in any order.  They should form a rectangle.

    Returns:
        Interpolated stuff.

    Raises:
        ValueError: if points are not the right type/values to use this function

    Notes:
        See formula at:  http://en.wikipedia.org/wiki/Bilinear_interpolation
    """

    points = sorted(points)               # order points by x, then by y
    (x1, y1, q11), (_x1, y2, q12), (x2, _y1, q21), (_x2, _y2, q22) = points

    if x1 != _x1 or x2 != _x2 or y1 != _y1 or y2 != _y2:
        raise ValueError('points do not form a rectangle')
    if not x1 <= x <= x2 or not y1 <= y <= y2:
        raise ValueError('(x, y) not within the rectangle')

    return (q11 * (x2 - x) * (y2 - y) +
            q21 * (x - x1) * (y2 - y) +
            q12 * (x2 - x) * (y - y1) +
            q22 * (x - x1) * (y - y1)
           ) / ((x2 - x1) * (y2 - y1) + 0.0)


def generate_profiles(interp_atmo, stan_atmo, pressures):
    """
    Add standard atmosphere to top of NARR or MERRA atmo data.

    Args:
        interp_atmo: NARR or MERRA data
        stan_atmo: summer mid-lat MODTRAN standard atmosphere
        pressures: pressure levels

    Returns:
        [hgt, p, t, rh] * 4: one list for each point
    """
    height, rhum, temp = interp_atmo
    stan_height, stan_press, stan_temp, stan_rhum = stan_atmo

    profiles = []

    for point_idx in range(4):

        p = pressures[0]
        t = temp[point_idx]
        hgt = height[point_idx]
        rh = rhum[point_idx]

        gdalt = hgt[0]

        # interpolate linearly between stan atmo and input data
        above = numpy.where(stan_height > hgt[-1])[0]
        if len(above) > 0:
            interpolateTo = above[0]

            newHeight = (stan_height[interpolateTo] + hgt[-1]) / 2.0

            newPressure2 = p[-1] + (newHeight - hgt[-1]) * \
            ((stan_press[interpolateTo] - p[-1]) / (stan_height[interpolateTo] - hgt[-1]))

            newTemperature2 = t[-1] + (newHeight - hgt[-1]) * \
            ((stan_temp[interpolateTo] - t[-1]) / (stan_height[interpolateTo] - hgt[-1]))

            newRelativeHumidity2 = rh[-1] + (newHeight - hgt[-1]) * \
            ((stan_rhum[interpolateTo] - rh[-1]) / (stan_height[interpolateTo] - hgt[-1]))

            hgt = numpy.append(numpy.append(hgt, newHeight), stan_height[interpolateTo:-1])
            p = numpy.append(numpy.append(p, newPressure2), stan_press[interpolateTo:-1])
            t = numpy.append(numpy.append(t, newTemperature2), stan_temp[interpolateTo:-1])
            rh = numpy.append(numpy.append(rh, newRelativeHumidity2), stan_rhum[interpolateTo:-1])

        profiles.append([hgt, p, t, rh])

    return profiles
