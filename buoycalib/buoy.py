import math
import os

import numpy
import datetime

from . import settings
from . import atmo
from .download import (url_download, ungzip)


class BuoyDataException(Exception):
    pass

class Buoy(object):
    def __init__(self, _id, lat, lon, thermometer_depth, height, skin_temp=None,
                 surf_press=None, surf_airtemp=None, surf_rh=None, url=None,
                 filename=None, bulk_temp=None):
         self.id = _id
         self.lat = lat
         self.lon = lon
         self.thermometer_depth = thermometer_depth
         self.height = height
         self.skin_temp = skin_temp
         self.bulk_temp = bulk_temp
         self.surf_press = surf_press
         self.surf_airtemp = surf_airtemp
         self.surf_rh = surf_rh

         self.url = url
         self.filename = filename

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return 'Buoy ID: {0} Lat: {1} Lon: {2}'.format(self.id, self.lat, self.lon)


def find_skin_temp(hour, data, headers, depth):
    """
    Convert bulk temp -> skin temperature.

    Args:
        cc: calibrationcontroller object, for data and time information
        data: data from buoy file
        depth: depth of thermometer on buoy

    Returns:
        skin_temp [Kelvin]

    Raises:
        Exception: if no data, date range wrong, etc.

    Notes:
        source: https://www.cis.rit.edu/~cnspci/references/theses/masters/miller2010.pdf
    """
    # compute 24hr wind speed and temperature
    avg_wspd = data[:, headers['WSPD']].mean()   # [m/s]
    avg_wtmp = data[:, headers['WTMP']].mean()   # [C]

    bulk_temp = avg_wtmp + 273.15   # [C -> K]

    # calculate skin temperature
    # part 1
    a = 0.05 - (0.6 / avg_wspd) + (0.03 * math.log(avg_wspd))
    z = depth   # depth in meters

    avg_skin_temp = avg_wtmp - (a * z) - 0.17

    # part 2
    b = 0.35 + (0.018 * math.exp(0.4 * avg_wspd))
    c = 1.32 - (0.64 * math.log(avg_wspd))

    t = int(hour - (c * z))
    T_zt = float(data[t, headers['WTMP']])    # temperature data from closest hour
    f_cz = (T_zt - avg_skin_temp) / numpy.exp(b*z)

    # combine
    skin_temp = avg_skin_temp + f_cz + 273.15   # [K]

    if skin_temp >= 600:
        raise BuoyDataException('No water temp data for selected date range in the data set')

    return skin_temp, bulk_temp


def calculate_buoy_information(scene, buoy_id=''):
    """
    Pick buoy dataset, download, and calculate skin_temp.

    Args: None

    Returns: None
    """
    ur_lat = scene.CORNER_UR_LAT_PRODUCT
    ur_lon = scene.CORNER_UR_LON_PRODUCT
    ll_lat = scene.CORNER_LL_LAT_PRODUCT
    ll_lon = scene.CORNER_LL_LON_PRODUCT
    corners = ur_lat, ll_lat, ur_lon, ll_lon

    datasets = datasets_in_corners(corners)
    try:
        if buoy_id and buoy_id in datasets:
            buoy = datasets[buoy_id]
            buoy.calc_info(scene.date)
            return buoy

        for ds in datasets:
            datasets[ds].calc_info(scene.date)
            return datasets[ds]

    except RemoteFileException as e:
        print(e)
    except BuoyDataException as e:
        print(e)

    raise BuoyDataException('No suitable buoy found.')


def datasets_in_corners(corners):
    """
    Get list of all NOAA buoy datasets that fall within a landsat scene.

    Args:
        corners: tuple of: (ur_lat, ll_lat, ur_lon, ll_lon)

    Return:
        [[Buoy_ID, lat, lon, thermometer_depth], [ ... ]]

    """
    stations = all_datasets()
    inside = {}

    # keep buoy stations and coordinates that fall within the corners
    for stat in stations:
        # check for latitude and longitude
        if point_in_corners(corners, (stations[stat].lat, stations[stat].lon)):
            inside[stat] = stations[stat]

    return inside


def point_in_corners(corners, point):
    ur_lat, ll_lat, ur_lon, ll_lon = corners
    lat, lon = point

    if ur_lat > 0 and not (ll_lat < lat < ur_lat):
        return False
    elif ur_lat <= 0 and not (ll_lat > lat > ur_lat):
        return False

    if ur_lon > 0 and not (ll_lon > lon > ur_lon):
        return False
    elif ur_lon <= 0 and not (ll_lon < lon < ur_lon):
        return False

    return True


def all_datasets():
	# TODO memoize
    """
    Get list of all NOAA buoy datasets.

    Return:
        [[Buoy_ID, lat, lon, thermometer_depth, height], [ ... ]]

    """
    buoys, heights, anemometer_height = numpy.genfromtxt(settings.BUOY_TXT, skip_header=7,
                                      usecols=(0, 1, 3), unpack=True)
    buoy_heights = dict(zip(buoys, heights))

    buoy_stations = {}

    with open(settings.STATION_TXT, 'r') as f:
        f.readline()
        f.readline()

        for line in f:
            info = line.split('|')
            sid = info[0]   # 1st column, Station ID
            if not sid.isdigit():  # TODO check if is buoy or ground station
                continue
            payload = info[5]   # 6th column, buoy payload type

            lat_lon = info[6].split(' (')[0]   # 7th column, discard part
            lat_lon = lat_lon.split()

            if lat_lon[1] == 'S':
                lat = float(lat_lon[0]) * (-1)
            else:
                lat = float(lat_lon[0])

            if lat_lon[3] == 'W':
                lon = float(lat_lon[2]) * (-1)
            else:
                lon = float(lat_lon[2])

            # TODO research and add more payload options
            if payload == 'ARES payload':
                depth = 1.0
            elif payload == 'AMPS payload':
                depth = 0.6
            else:
                depth = 0.8

            buoy_stations[sid] = Buoy(sid, lat, lon, depth, buoy_heights.get(sid, 0))

    return buoy_stations


def download(id, date, directory=settings.NOAA_DIR):
    """
    Download and unzip appripriate buoy data from url.

    Args:
        url: url to download data from
    """
    if date.year < 2018:
        url = settings.NOAA_URLS[0] % (id, date.year)
    else:
        url = settings.NOAA_URLS[1] % (date.strftime('%b'), id, date.strftime('%m'))

    filename = url_download(url, directory)

    if '.gz' in filename:
        filename = ungzip(filename)

    return filename


def skin_temp(file, date, thermometer_depth):
    """
    Args:
    """
    data, headers = load(file, date)

    skin_temp, bulk_temp = find_skin_temp(date.hour, data, headers, thermometer_depth)

    return skin_temp, bulk_temp


def info(buoy_id, file, overpass_date):
    buoy_file = download(buoy_id, overpass_date)
    data, headers, dates, units = load(buoy_file)
    b = all_datasets()[buoy_id]
    buoy_depth = b.thermometer_depth

    #data, headers = load(file)
    dt_slice = [i for i, d in enumerate(dates) if abs(d - overpass_date) < datetime.timedelta(hours=24)]
    closest_dt = min([(i, abs(overpass_date - d)) for i, d in enumerate(dates)], key=lambda i: i[1])

    w_temp = data[dt_slice, headers.index('WTMP')]
    wind_spd = data[dt_slice, headers.index('WSPD')]

    try:
        surf_airtemp = data[closest_dt[0], headers.index('ATMP')]
    except IndexError:
        raise BuoyDataException('out of range, no data available')

    try:
        surf_press = data[closest_dt[0], headers.index('BAR')]
    except ValueError:
        surf_press = data[closest_dt[0], headers.index('PRES')]

    surf_dewpnt = data[closest_dt[0], headers.index('DEWP')]
    surf_rh = atmo.data.calc_rh(surf_airtemp, surf_dewpnt)

    bulk_temp = data[closest_dt[0], headers.index('WTMP')]

    skin_temp = calc_skin_temp(data, dates, headers, overpass_date, buoy_depth)

    return b.lat, b.lon, b.thermometer_depth, bulk_temp, skin_temp, [surf_press, surf_airtemp, surf_dewpnt, surf_rh]


def load(filename):
    """
    Open a downloaded buoy data file and extract data from it.

    Args:
        date: datetime object
        filename: buoy file to open

    Returns:
        data: from file, trimmed to date

    Raises:
        Exception: if no data is found in file
    """
    def _filter(iter):
        # NOAA NDBC uses 99.0 and 999.0 as a placeholder for no data
        new = []
        for item in iter:
            i = float(item)
            if i == 99 or i == 999:
                new.append(numpy.nan)
            else:
                new.append(i)
        return new

    dates = []
    lines = []
    with open(filename, 'r') as f:
        header = f.readline()
        unit = f.readline()

        for line in f:
            date_str = ' '.join(line.split()[:5])

            if len(line.split()[0]) == 4:
                date_dt = datetime.datetime.strptime(date_str, '%Y %m %d %H %M')
            elif len(line.split()[0]) == 2:
                date_dt = datetime.datetime.strptime(date_str, '%y %m %d %H %M')

            data = _filter(line.split()[5:])
            lines.append(data)
            dates.append(date_dt)

    headers = header.split()[5:]
    units = unit.split()[5:]
    lines = numpy.asarray(lines)

    return lines, headers, dates, units


def calc_skin_temp(data, dates, headers, overpass_date, buoy_depth):
    dt = [(i, d) for i, d in enumerate(dates) if abs(d - overpass_date) < datetime.timedelta(hours=12)]
    if len(dt) == 0:
        raise BuoyDataException('No Buoy Data')

    dt_slice, dt_times = zip(*dt)
    w_temp = data[dt_slice, headers.index('WTMP')]
    wind_spd = data[dt_slice, headers.index('WSPD')]
    closest_dt = min([(i, abs(overpass_date - d)) for i, d in enumerate(dates)], key=lambda i: i[1])
    T_zt = data[closest_dt[0], headers.index('WSPD')]


    # 24 hour average wind Speed at 10 meters (measured at 5 meters) 
    u_m = wind_speed_height_correction(numpy.nanmean(wind_spd), 5, 10)
    
    avg_wtmp = numpy.nanmean(w_temp)

    a = 0.05 - (0.6 / u_m) + (0.03 * numpy.log(u_m))   # thermal gradient
    z = buoy_depth   # depth in meters

    avg_skin_temp = avg_wtmp - (a * z) - 0.17

    # part 2
    b = 0.35 + (0.018 * numpy.exp(0.4 * u_m))
    c = 1.32 - (0.64 * numpy.log(u_m))

    if numpy.isnan(c):
        raise BuoyDataException('no wind speed data')


    f_cz = (w_temp - avg_skin_temp) / numpy.exp(b*z)
    cz = datetime.timedelta(hours=c*z)
    t_cz = [dt_to_dec_hour(dt + cz) for dt in dt_times]
    t = [dt_to_dec_hour(dt) for dt in dt_times]
    
    f = numpy.interp(t_cz, t, f_cz)

    # combine
    skin_temp = avg_skin_temp +  + 273.15   # [K]

    # check for validity
    if not (1.5 < u_m < 7.6):
        if (1.1 < a*z < 0) and (1 < numpy.exp(b*z) < 6) and (0 < c*z < 4):
            pass
        else:
            raise BuoyDataException('Wind Speed out of range')

    #if (-1.1 < a*z < 0) and (1 < numpy.exp(b*z) < 6) and (0 < c*z < 4):
    #    pass
    #else:
    #    print(a*z, numpy.exp(b*z), c*z)

    return skin_temp

def wind_speed_height_correction(wspd, h1, h2, n=0.1):
    # equation 2.9 in padula, simpolified wind speed correction
    return wspd * (h2 / h1) ** n

def dt_to_dec_hour(dt):
    return dt.hour + dt.minute / 60
