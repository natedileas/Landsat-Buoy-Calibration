import math

import numpy

from . import settings
from .download import url_download, remote_file_exists, ungzip, RemoteFileException
from . import atmo


class BuoyDataException(Exception):
    pass


def calculate_buoy_information(metadata, buoy_id=''):
    """
    Pick buoy dataset, download, and calculate skin_temp.

    Args: None

    Returns: None
    """
    ur_lat = metadata['CORNER_UR_LAT_PRODUCT']
    ur_lon = metadata['CORNER_UR_LON_PRODUCT']
    ll_lat = metadata['CORNER_LL_LAT_PRODUCT']
    ll_lon = metadata['CORNER_LL_LON_PRODUCT']
    corners = ur_lat, ll_lat, ur_lon, ll_lon

    datasets = datasets_in_corners(corners)

    if buoy_id and buoy_id in datasets:
        info = calc_ds_info(datasets[buoy_id], metadata['date'])

    for ds in datasets:
        try:
            info = calc_ds_info(datasets[ds], metadata['date'])
            break
        except RemoteFileException as e:
            print(e)
        except BuoyDataException as e:
            print(e)

    return info


def calc_ds_info(dataset, date):
    """
    [buoy_id, lat, lon, depth]
    """
    buoy, lat, lon, depth, height = dataset

    if date.year < 2016:
        url = settings.NOAA_URLS[0] % (buoy, date.year)
    else:
        url = settings.NOAA_URLS[1] % (date.strftime('%b'), buoy, date.strftime('%m'))

    data_file = download_noaa(url)

    data, headers = load(data_file, date)

    skin_temp = find_skin_temp(date.hour, data, headers, depth)

    try:
        buoy_press = data[date.hour, headers['BAR']]
    except KeyError:
        buoy_press = data[date.hour, headers['PRES']]

    buoy_airtemp = data[date.hour, headers['ATMP']]
    buoy_dewpnt = data[date.hour, headers['DEWP']]
    buoy_rh = atmo.data.calc_rh(buoy_airtemp, buoy_dewpnt)

    dataset.extend([skin_temp, buoy_press, buoy_airtemp, buoy_rh])

    return dataset


def all_datasets():
	# TODO memoize
    """
    Get list of all NOAA buoy datasets.

    Return:
        [[Buoy_ID, lat, lon, thermometer_depth, height], [ ... ]]

    """
    buoys, heights = numpy.genfromtxt(settings.BUOY_TXT, skip_header=7,
                                      usecols=(0, 1), unpack=True)
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

            buoy_stations[sid] = [sid, lat, lon, depth, buoy_heights.get(sid, 0)]

    return buoy_stations


def datasets_in_corners(corners):
    """
    Get list of all NOAA buoy datasets that fall within a landsat scene.

    Args:
        corners: tuple of: (ur_lat, ll_lat, ur_lon, ll_lon)

    Return:
        [[Buoy_ID, lat, lon, thermometer_depth], [ ... ]]

    """
    stations = all_datasets()

    ur_lat, ll_lat, ur_lon, ll_lon = corners

    inside = {}

    # keep buoy stations and coordinates that fall within the corners
    for stat in stations:
        buoy_lat = stations[stat][1]
        buoy_lon = stations[stat][2]

        # check for latitude
        if buoy_lat > ll_lat and buoy_lat < ur_lat:
            if buoy_lon > ll_lon and buoy_lon < ur_lon:  # check for longitude
                inside[stat] = stations[stat]

    return inside


def download_noaa(url):
    """
    Download and unzip appripriate buoy data from url.

    Args:
        url: url to download data from
    """
    remote_file_exists(url)
    filename = url_download(url, settings.NOAA_DIR)

    if '.gz' in filename:
        filename = ungzip(filename)

    return filename


def load(filename, date):
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
    date = date.strftime('%Y %m %d')
    date_short_year = date[2:]
    data = []

    with open(filename, 'r') as f:
        header = f.readline()

        for line in f:
            if date in line or date_short_year in line:
                data.append(line.strip('\n').split())

    if data == []:
        raise BuoyDataException('No matching date in file? {0} {1}.'.format(date, filename))

    data = numpy.asarray(data, dtype=float)

    headers = dict(zip(header.split(), range(len(data[:, 0]))))

    return data, headers


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
    avg_wspd = data[:, headers['WSPD']].mean()   # [m s-1]
    avg_wtmp = data[:, headers['WTMP']].mean()   # [C]

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

    return skin_temp
