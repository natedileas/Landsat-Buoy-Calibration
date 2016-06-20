import logging
import math
import os
import re
import subprocess
import urllib2

import numpy
import utm

class BuoyDataError(Exception):
    """ Exception for lack of buoy data in the expected file. """
    def __init__(self, msg):
        self.msg=msg

    def __str__(self):
        return repr(self.msg)

def get_stationtable(save_dir):
    """ 
    Downloads and unzips station_table.txt. 

    Args:
        save_dir: directory in which to save the file

    Returns:
        True or False: depending on whether or not it has been downloaded 
    """

    # define names
    filename = os.path.join(save_dir, 'station_table.txt')
    url = "http://www.ndbc.noaa.gov/data/stations/station_table.txt"

    if not os.path.exists(filename):
        try:
            # open url
            f = urllib2.urlopen(url)

            data = f.read()

            # write data to file
            with open(filename, "wb") as local_file:
                local_file.write(data)

            return 0

        except urllib2.HTTPError, e:
            print "HTTP Error:", e.code, url
            return False
        except urllib2.URLError, e:
            print "URL Error:", e.reason, url
            return False
        except OSError, e:
            print 'OSError: ', e.reason
            return False

    return True

def find_datasets(save_dir, corners):
    """
    Get list of possible datasets. 

    Args:
        save_dir: directory in which to save the file
        corners: corners of the landsat image

    Returns:
        datasets, coordinates, depths: lists of buoy ids, their coordinates, and their depths

    Notes:
        The staion_table.txt file is hugely inconsistent and not computer-friendly.
    """

    filename = os.path.join(save_dir, 'station_table.txt')

    # read in and zip coordinates and buoy SIDs
    # use reg expressions to find matching strings in lines
    lat_lon_search = re.compile('\d\d\.\d\d\d [NS] \d?\d\d\.\d\d\d [WE]')
    # search for SID (station ID)
    sid_search = re.compile('\A\w*')
    buoy_stations = []
    SID = []
    depth = 0.5

    with open(filename, 'r') as f:
        f.readline()
        f.readline()

        for line in f:
            lat_lon = lat_lon_search.search(line)  # latitude and longitude
            sid = sid_search.search(line)   # station ID

            if lat_lon and sid:
                lat_lon = lat_lon.group()
                lat_lon = lat_lon.split()

                sid = sid.group()
                lat_lon.append(sid)

                if lat_lon[3] == 'W':
                    lat_lon[2] = float(lat_lon[2]) * (-1)
                else:
                    lat_lon[2] = float(lat_lon[2])

                if lat_lon[1] == 'S':
                    lat_lon[0] = float(lat_lon[0]) * (-1)
                else:
                    lat_lon[0] = float(lat_lon[0])

                if 'ARES' in line:
                    depth = 1.0
                elif 'AMPS' in line:   # TODO add more payload options
                    depth = 0.6
                else:
                    depth = 0.8

                buoy_stations.append([lat_lon[4], [lat_lon[0],
                                      lat_lon[2]], depth])  # SID, LAT, LON

    datasets = []
    coordinates = []
    depths = []

    # keep buoy stations and coordinates that fall within the corners
    # of the image, save to datasets, coordinates, depths
    for i in range(len(buoy_stations)):
        buoy_lat = buoy_stations[i][1][0]
        buoy_lon = buoy_stations[i][1][1]

        # check for latitude
        if buoy_lat > corners[1, 0] and buoy_lat < corners[0, 0]:
            # check for longitude
            if buoy_lon > corners[1, 1] and buoy_lon < corners[0, 1]:
                datasets.append(buoy_stations[i][0])
                coordinates.append(buoy_stations[i][1])
                depths.append(buoy_stations[i][2])

    return datasets, coordinates, depths
        
def search_stationtable(save_dir, sid):
    """
    Last-ditch attempt at getting buoy data. 

    Args:

    Returns:

    Raises:

    Notes:
    """
    filename = os.path.join(save_dir, 'station_table.txt')
    
    sid = str(sid)
    # read in and zip coordinates and buoy SIDs
    # use reg expressions to find matching strings in lines
    # search for lat/lon
    lat_lon_search = re.compile('\d\d\.\d\d\d [NS] \d?\d\d\.\d\d\d [WE]')

    with open(filename, 'r') as f:
        f.readline()
        f.readline()

        for line in f:
            if sid in line:
                lat_lon = lat_lon_search.search(line)  # latitude and longitude

                if lat_lon:
                    lat_lon = lat_lon.group()
                    lat_lon = lat_lon.split()

                    if lat_lon[3] == 'W':
                        lat_lon[2] = float(lat_lon[2]) * (-1)
                    else:
                        lat_lon[2] = float(lat_lon[2])

                    if lat_lon[1] == 'S':
                        lat_lon[0] = float(lat_lon[0]) * (-1)
                    else:
                        lat_lon[0] = float(lat_lon[0])

                    if 'ARES' in line:
                        depth = 1.0
                    elif 'AMPS' in line:   # TODO add more payload options
                        depth = 0.6
                    else:
                        depth = 0.8
                    
                    
                    return sid, [lat_lon[0], lat_lon[2]], depth
                else:
                    self.logger.warning('lat_lon search returned none')
                    return -1
        return -1


def get_buoy_data(filename, url):
    """
    Download/ unzip appripriate buoy data from url.

    Args:
        filename: path/file to save buoy data file
        url: url to download data from

    Returns:
        True or False: depending on whether or not it has been downloaded 

    """

    try:
        # open url
        f = urllib2.urlopen(url)

        # write data to file

        with open(filename, "wb") as local_file:
            local_file.write(f.read())

        # unzip if it is still zipped 
        # TODO replace with python unzip method
        if '.gz' in filename:
            subprocess.check_call('gzip -d -f '+filename, shell=True)
            # subprocess.Popen('rm '+filename, shell=True)

    except urllib2.HTTPError, e:
        return False
    except urllib2.URLError, e:
        logging.error("URL Error:", e.reason, url)
        return False
    except OSError, e:
        logging.error('OSError: ', e.reason, filename)
        return False

    return True


def find_skin_temp(cc, filename, depth):
    """
    Convert bulk temp -> skin temperature.

    Args:
        cc: calibrationcontroller object, for data and time information
        filename: filename to get data from
        depth: depth of thermometer on buoy

    Returns:
        skin_temp, pres, atemp, dewp: all parameters of the buoy

    Raises:
        BuoyDataError: if no data, date range wrong, etc.

    Notes:
        source: https://www.cis.rit.edu/~cnspci/references/theses/masters/miller2010.pdf
    """

    hour = cc.scenedatetime.hour
    
    date = cc.date.strftime('%Y %m %d')
    data = []

    with open(filename, 'r') as f:
        for line in f:
            if date in line:
                data.append(line.strip('\n').split())

    if data is []:
        raise BuoyDataError('No data in file? %s.'% filename)
        
    data = numpy.asarray(data, dtype=float)

    # compute 24hr wind speed and temperature
    avg_wspd = data[:,6].mean()   # [m s-1]
    avg_wtmp = data[:,14].mean()   # [C]
    
    pres = data[:,12].mean()
    atemp = data[:,13].mean()
    dewp = data[:,15].mean()

    # calculate skin temperature
    # part 1
    a = 0.05 - (0.6 / avg_wspd) + (0.03 * math.log(avg_wspd))
    z = depth   # depth in meters
    
    avg_skin_temp = avg_wtmp - (a * z) - 0.17

    # part 2
    b = 0.35 + (0.018 * math.exp(0.4 * avg_wspd))
    c = 1.32 - (0.64 * math.log(avg_wspd))
    
    t = int(hour - (c * z))
    T_zt = float(data[t][14])    # temperature data from closest hour
    f_cz = (T_zt - avg_skin_temp) / math.exp(b*z)

    # combine
    skin_temp = avg_skin_temp + f_cz + 273.15

    if skin_temp >= 600:
        raise BuoyDataError('No water temp data for selected date range in the data set %s.'% filename)

    return skin_temp, pres, atemp, dewp
