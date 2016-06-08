import numpy
import subprocess
import urllib2
import os
import utm
import re
import sys
import shutil
import math

class BuoyDataError(Exception):
    pass
            
def get_stationtable(save_dir):
    """ download and unzip station_table.txt. """
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
            return -1
        except urllib2.URLError, e:
            print "URL Error:", e.reason, url
            return -1
        except OSError, e:
            print 'OSError: ', e.reason
            return -1
    else:
        return 0
        

def find_datasets(save_dir, corners):
    """ get list of possible datasets. """
    # define names
    filename = os.path.join(save_dir, 'station_table.txt')

    # read in and zip coordinates and buoy SIDs
    # use reg expressions to find matching strings in lines
    # search for lat/lon
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
            if buoy_lon > corners[1, 1]:
                if buoy_lon < corners[0, 1]:
                    datasets.append(buoy_stations[i][0])
                    coordinates.append(buoy_stations[i][1])
                    depths.append(buoy_stations[i][2])

    return datasets, coordinates, depths
        
def search_stationtable(save_dir, sid):
    """ last-ditch attempt at getting buoy data. """
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
    """ download/ unzip appripriate buoy data from url. """

    try:
        # open url
        f = urllib2.urlopen(url)

        # write data to file

        with open(filename, "wb") as local_file:
            local_file.write(f.read())

        # unzip if it is still zipped
        if '.gz' in filename:
            subprocess.check_call('gzip -d -f '+filename, shell=True)
            # subprocess.Popen('rm '+filename, shell=True)

    except urllib2.HTTPError, e:
        return -1
    except urllib2.URLError, e:
        print "URL Error:", e.reason, url
        sys.exit()
    except OSError, e:
        print 'OSError: ', e.reason
        sys.exit()

    return 0

def find_skin_temp(filename, metadata, url, depth):
    """ compute skin temperature. """
    
    # source: https://www.cis.rit.edu/~cnspci/references/theses/masters/miller2010.pdf

    # parse year, month, day
    date = metadata['DATE_ACQUIRED']
    year = date[0:4]
    month = date[5:7]
    day = date[8:10]

    hour = float(metadata['SCENE_CENTER_TIME'][0:2])

    date = year+' '+month+' '+day+' 00'    # reformat date
    chars = ['\n']    # characters to remove from line
    data = []
    line = ' '

    # open file, get rid of empty spaces and unwanted characters
    # then append to data
    with open(filename, 'r') as f:
        while line != '':
            line = f.readline()
            if date in line:
                for i in range(24):
                    if i != 0:
                        line = f.readline()
                    line = line.translate(None, ''.join(chars))
                    data.append(filter(None, line.split(' ')))
                break

    if data == [[]] or []:
        raise BuoyDataError('No data in file? %s.'% filename)

    # compute 24hr wind speed and temperature
    avg_wspd = 0    # m/s
    avg_wtmp = 0    # C
    pres = 0
    atemp = 0
    dewp = 0

    for i in range(24):
        try:
            avg_wspd += float(data[i][6]) / 24
            avg_wtmp += float(data[i][14]) / 24
            pres += float(data[i][12]) / 24
            atemp += float(data[i][13]) / 24
            dewp += float(data[i][15]) / 24
        except ValueError:
            pass
        except IndexError:
            raise BuoyDataError('No data in file? %s. (IndexError)'% filename)

    # calculate skin temperature
    z = depth   # depth in meters

    # part 1
    a = 0.05 - (0.6 / avg_wspd) + (0.03 * math.log(avg_wspd))
    avg_skin_temp = avg_wtmp - (a * z) - 0.17

    # part 2
    b = 0.35 + (0.018 * math.exp(0.4 * avg_wspd))
    c = 1.32 - (0.64 * math.log(avg_wspd))
    t = int(hour - (c * z))
    T_zt = float(data[t][14])    # get temperature data from that specific hour 
    f_cz = (T_zt - avg_skin_temp) / math.exp(b*z)

    # combine
    skin_temp = avg_skin_temp + f_cz + 273.15

    if skin_temp >= 600:
        raise BuoyDataError('No water temp data for selected date range in the data set %s.'% filename)

    return skin_temp, pres, atemp, dewp
