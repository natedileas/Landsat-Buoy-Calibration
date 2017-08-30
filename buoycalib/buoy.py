import logging
import math
import os
import re
import subprocess
import urllib2

import numpy
import utm

import settings

class BuoyDataError(Exception):
    """ Exception for lack of buoy data in the expected file. """
    def __init__(self, msg):
        self.msg=msg

    def __str__(self):
        return repr(self.msg)

 def calculate_buoy_information(self):
        """
        Pick buoy dataset, download, and calculate skin_temp.

        Args: None

        Returns: None
        """
        datasets, buoy_coors, depths = buoy_data.find_datasets(self)
        
        filename = os.path.join(settings.NOAA_DIR, 'buoy_height.txt')
        buoys, heights = numpy.genfromtxt(filename, skip_header=7, usecols=(0,1), unpack=True)
        buoy_heights = dict(zip(buoys, heights))
        
        year = self.date.strftime('%Y')
        mon_str = self.date.strftime('%b')
        month = self.date.strftime('%m')
        hour = self.scenedatetime.hour
        
        if self.buoy_id:
            if self.buoy_id in datasets:
                idx = datasets.index(self.buoy_id)
                datasets = [datasets[idx]]
                depths = [depths[idx]]
            else:
                logging.error('User Requested Buoy is not in scene.')
                sys.exit(-1)
        
        for idx, buoy in enumerate(datasets):
            if self.date.year < 2016:
                url = settings.NOAA_URLS[0] % (buoy, year)
            else:
                url = settings.NOAA_URLS[1] % (mon_str, buoy, int(month))
            
            zipped_file = os.path.join(settings.NOAA_DIR, os.path.basename(url))
            unzipped_file = zipped_file.replace('.gz', '')
            
            try:
                if not buoy_data.get_buoy_data(zipped_file, url): 
                    continue

                data, headers = buoy_data.open_buoy_data(self, unzipped_file)
                self.skin_temp = buoy_data.find_skin_temp(hour, data, headers, depths[idx])
                
                self.buoy_id = buoy
                self.buoy_location = buoy_coors[idx]
                
                try:
                    self.buoy_height = buoy_heights[self.buoy_id]
                except KeyError:
                    self.buoy_height = 0.0
                
                try:
                    self.buoy_press = data[hour, headers['BAR']]
                except KeyError:
                    self.buoy_press = data[hour, headers['PRES']]

                self.buoy_airtemp = data[hour, headers['ATMP']]
                self.buoy_dewpnt = data[hour, headers['DEWP']]
                self.buoy_rh = atmo_data.calc_rh(self.buoy_airtemp, self.buoy_dewpnt)

                logging.info('Used buoy: %s'% buoy)
                break
                
            except buoy_data.BuoyDataError as e:
                logging.warning('Dataset %s didn\'t work (%s). Trying a new one' % (buoy, e))
                continue
                
        if not self.buoy_location:
            logging.error('User Requested Buoy Did not work.')
            sys.exit(-1)


def find_datasets(cc):
    """
    Get list of possible datasets. 

    Args:
        save_dir: directory in which to save the file
        corners: corners of the landsat image

    Returns:
        datasets, coordinates, depths: lists of buoy ids, their coordinates, and their depths

    Notes:
        The station_table.txt file is hugely inconsistent and not really computer-friendly.
    """

    corners = numpy.asarray([[0, 0]]*2, dtype=numpy.float32)
    corners[0] = cc.metadata['CORNER_UR_LAT_PRODUCT'], \
        cc.metadata['CORNER_UR_LON_PRODUCT']

    corners[1] = cc.metadata['CORNER_LL_LAT_PRODUCT'], \
        cc.metadata['CORNER_LL_LON_PRODUCT']

    filename = os.path.join(settings.NOAA_DIR, 'station_table.txt')

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
        logging.error("HTTP Error: %s %s" % (e.reason, url))
        return False
    except urllib2.URLError, e:
        logging.error("URL Error:", e.reason, url)
        return False
    except OSError, e:
        logging.error('OSError: ', e.reason, filename)
        return False

    return True
    
def open_buoy_data(cc, filename):
    """
    Open a downloaded buoy data file and extract data from it.
    
    Args:
        cc: calibrationcontroller object, for date
        filename: buoy file to open
    
    Returns:
        data: from file, trimmed to date
        
    Raises:
        BuoyDataError: if no data is found in file
    
    """
    date = cc.date.strftime('%Y %m %d')
    date_short_year = date[2:]
    data = []

    with open(filename, 'r') as f:
        header = f.readline()

        for line in f:
            if date in line or date_short_year in line:
                data.append(line.strip('\n').split())

    if data == []:
        raise BuoyDataError('No data in file? %s.'% filename)
        
    data = numpy.asarray(data, dtype=float)

    headers = dict(zip(header.split(), range(len(data[:,0]))))

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
        BuoyDataError: if no data, date range wrong, etc.

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
    f_cz = (T_zt - avg_skin_temp) / math.exp(b*z)

    # combine
    skin_temp = avg_skin_temp + f_cz + 273.15   # [K]

    if skin_temp >= 600:
        raise BuoyDataError('No water temp data for selected date range in the data set')

    return skin_temp
