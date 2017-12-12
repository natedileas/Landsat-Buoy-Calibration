import math
import os
import itertools

import numpy
from netCDF4 import Dataset, num2date
import utm

from . import funcs


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

    SR1 = s / (numpy.cos(e1 / r))
    SR2 = s / (numpy.cos(((e2 - e1) / 6) / r))
    SR3 = s / (numpy.cos(e2 / r))

    Edist = ((e2 - e1) / 6) * (SR1 + 4 * SR2 + SR3)

    dist = numpy.sqrt(Edist**2 + (n2 - n1)**2)

    return dist


