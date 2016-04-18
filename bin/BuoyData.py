import numpy
import subprocess
import urllib2
import os
import utm
import re
import sys
import shutil

class BuoyData(object):
    """ Pick buoy, download dataet, and calculate skin_temp.
    
    Attributes:
        logger: logging object used to hold non-verbose output.
        metadata: dict of landsat metadata values
        corners: upper right and lower left corners of landsat scene, lat-lon
        buoy: buoy_id from CalibrationController object, can be None
        save_dir: directory in which to save datasets.
        dataset: base of url, used in trying multiple datasets.

    Methods:
        __init__(self, other): initialize using a CalibrationController object
        start_download(self): run one iteration of trying to download buoy data
            and compute skin_temp
        _find_datasets(self): find all datasets that lie within corners.
            Returns: datasets, buoy_coors, depths (lists).
        _save_buoy_data(self, sid): copy of _find_datasets tuned to a single id.
        _get_stationtable(self): download and unzip stationtable.txt
        _get_buoy_data(self, url): download specific dataset form url.
        _find_skin_temp(self, url, depth): compute skin temperature from 
            self.buoy dataset and depth.
    """
    def __init__(self, other):
        """ initialize using a CalibrationController object. """
        self.metadata = other.metadata
        self.corners = numpy.asarray([[0, 0]]*2, dtype=numpy.float32)
        self.corners[0] = self.metadata['CORNER_UR_LAT_PRODUCT'], \
            self.metadata['CORNER_UR_LON_PRODUCT']

        self.corners[1] = self.metadata['CORNER_LL_LAT_PRODUCT'], \
            self.metadata['CORNER_LL_LON_PRODUCT']

        self.buoy = other.buoy_id

        self.save_dir = os.path.join(other.filepath_base, 'data/shared/buoy')
        self.scene_dir = other.scene_dir
        self.dataset = None

    def start_download(self):
        """ download and process buoy data. """
        datasets, buoy_coors, depths = self.__find_datasets()
        return_vals = None

        url_base = ['http://www.ndbc.noaa.gov/data/historical/stdmet/',
                    'http://www.ndbc.noaa.gov/data/stdmet/']
        mon_str = ['Jan/', 'Feb/', 'Apr/', 'May/', 'Jun/', 'Jul/', 'Aug/',
                   'Sep/', 'Oct/', 'Nov/', 'Dec/']

        date = self.metadata['DATE_ACQUIRED']
        year = date[0:4]
        month = date[5:7]

        urls = []
        if datasets == [] or buoy_coors == [] or depths == []:
            self.logger.warning('.start_download: No buoys in scene...')
            if self.buoy:
                urls.append(url_base[0] + self.buoy + 'h' + year + '.txt.gz')
                urls.append(url_base[1] + mon_str[int(month) - 1] + self.buoy +
                            str(int(month)) + '2015.txt.gz')
                ret_vals = self.__save_buoy_data(self.buoy)
                if ret_vals != -1:
                    datasets, buoy_coors, depths = ret_vals
                else: 
                    print '.start_download: _save_buoy_data failed'
                    return -1
            else:
                print 'ERROR .start_download: No buoys in chosen landsat\
                                  scene and no buoy ID provided.'
                return -1
        else:
            for dataset in datasets:
                if year != '2015':
                    urls.append(url_base[0] + dataset + 'h' + year + '.txt.gz')
                else:
                    urls.append(url_base[1] + mon_str[int(month)-1] + dataset +
                                str(int(month)) + '2015.txt.gz')

            if self.buoy:
                try:
                    first_try = urls.pop(datasets.index(str(self.buoy)))
                    urls.insert(0, first_try)

                    first_try = depths.pop(datasets.index(self.buoy))
                    depths.insert(0, first_try)

                    first_try = buoy_coors.pop(datasets.index(self.buoy))
                    buoy_coors.insert(0, first_try)
                    
                    first_try = datasets.pop(datasets.index(self.buoy))
                    datasets.insert(0, first_try)
                except ValueError:
                    print '.start_download: Buoy %s was not found in landsat scene.' % self.buoy

        for url in urls:
            self.dataset = os.path.basename(url)
            zipped_file = os.path.join(self.save_dir, self.dataset)
            unzipped_file = zipped_file.replace('.gz', '')
            return_val = self.__get_buoy_data(url)

            if return_val == -1:
                print '.start_download: Dataset %s not found. Trying another buoy.' % self.dataset

                if os.path.exists(unzipped_file):
                    subprocess.Popen('rm '+unzipped_file, shell=True)
            else:
                ret_val = self.__find_skin_temp(url, depths[urls.index(url)])

                if ret_val == -1:
                    print '.start_download: The date range requested was not found in the data set %s.'% self.dataset

                    if os.path.exists(unzipped_file):
                        subprocess.Popen('rm '+unzipped_file, shell=True)
                else:
                    # good exit, return buoy actually used
                    skin_temp, pres, atemp, dewp = ret_val
                    
                    if skin_temp >= 600:
                        print '.start_download: No water temp data for selected date range in the data set %s.'% self.dataset

                        if os.path.exists(unzipped_file):
                            subprocess.Popen('rm '+unzipped_file, shell=True)

                    return_vals = [datasets[urls.index(url)],
                                   buoy_coors[urls.index(url)], skin_temp,
                                   pres, atemp, dewp]

                    if os.path.exists(unzipped_file):
                        try:
                            shutil.move(os.path.join(self.save_dir, unzipped_file), self.scene_dir)
                        except:
                            pass
                    print '.start_download: used dataset %s, good exit.'% self.dataset
                    break

        if return_vals:
            return return_vals
        else:
            print 'ERROR .start_download: No usable datasets were found'
            return -1
            
            
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
        
    def __save_buoy_data(self, sid):
        """ last-ditch attempt at getting buoy data. """
        filename = os.path.join(self.save_dir, 'station_table.txt')
        __ = self.__get_stationtable()
        
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


    def __get_buoy_data(self, url):
        """ download/ unzip appripriate buoy data from url. """

        try:
            # open url
            f = urllib2.urlopen(url)

            # write data to file
            filename = self.dataset

            with open(filename, "wb") as local_file:
                local_file.write(f.read())

            # move file to save_dir
            save_file = os.path.join(self.save_dir, filename)
            if not os.path.exists(save_file):
                subprocess.check_call('mv ' + filename + ' ' + self.save_dir,
                                      shell=True)

            # unzip if it is still zipped
            if '.gz' in filename:
                subprocess.check_call('gzip -d -f '+save_file, shell=True)
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

    def __find_skin_temp(self, url, depth):
        """ compute skin temperature. """
        import math

        # define filename
        filename = os.path.join(self.save_dir, self.dataset)
        filename = filename.replace('.gz', '')

        # parse year, month, day
        date = self.metadata['DATE_ACQUIRED']
        year = date[0:4]
        month = date[5:7]
        day = date[8:10]

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
            return -1

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
                return -1

        # calculate skin temperature
        if avg_wspd >= 4.5:
            d = 0.17   # Kelvin
        else:
            d = 0.0    # Kelvin

        a = 0.05 - (0.6 / avg_wspd) + (0.03 * math.log(avg_wspd))

        z = depth   # depth in meters

        # CALCULATE SKIN_TEMPERATURE. sry for the caps
        skin_temp = avg_wtmp + 273.15 - (a * z) - d

        return skin_temp, pres, atemp, dewp
