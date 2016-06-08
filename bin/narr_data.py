import numpy
import linecache
import utm
import itertools
import os
import sys
import subprocess

import image_processing as img_proc
import atmo_data
import misc_functions as funcs

def download(cc):
    """ download NARR Data (netCDF4 format). """
    
    narr_urls = ['ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/air.%s.nc', \
                    'ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/hgt.%s.nc',\
                    'ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/shum.%s.nc']
    
    date = cc.date.strftime('%Y%m')   # %s should be YYYYMM
    
    for url in narr_urls:
        url = url % date
        
        if os.path.isfile(os.path.join(cc.scene_dir, url.split('/')[-1])):   # if file already downloaded
            return
            
        subprocess.check_call('wget %s -P %s' % (url, cc.scene_dir), shell=True)

def open(cc):
    """ open NARR file (netCDF4 format). """

    data = []
    narr_files = ['air.%s.nc', 'hgt.%s.nc', 'shum.%s.nc']

    date = cc.date.strftime('%Y%m')
    
    for data_file in narr_files:
        data_file = data_file % date
        
        if os.path.isfile(os.path.join(cc.scene_dir, data_file)) is not True:   # if file already downloaded
            logging.error('NARR Data file does not exist at the expected path: %' % data_file)
            sys.exit(1)

        data.append(Dataset(data_file, "r", format="NETCDF4"))
        
    # order of returns is temp, height, specific humidity
    return data

def get_points(metadata, data):
    """ choose points within scene corners. """
    lat = data.variables['lat'][:]
    lon = data.variables['lon'][:]

    # define corners
    UL_lat = metadata['CORNER_UL_LAT_PRODUCT'] + 0.5
    UL_lon = metadata['CORNER_UL_LON_PRODUCT'] - 0.5
    LR_lat = metadata['CORNER_LR_LAT_PRODUCT'] - 0.5
    LR_lon = metadata['CORNER_LR_LON_PRODUCT'] + 0.5

    # pull out points that lie within the corners
    indexs = numpy.where((lat<UL_lat) & (lat>LR_lat) & (lon>UL_lon) & (lon<LR_lon))

    return indexs, lat, lon

def choose_points(inLandsat, lat, lon, buoy_coors): 
    latvalues = lat[inLandsat]
    lonvalues = lon[inLandsat]

    buoy_x, buoy_y, buoy_zone_num, buoy_zone_let = utm.from_latlon(*buoy_coors)
    distances = []
    
    for i in range(len(latvalues)):
        east, north, zone_num, zone_let = utm.from_latlon(latvalues[i], lonvalues[i])
        
        dist = atmo_data.distance_in_utm(east, north, buoy_x, buoy_y)
        distances.append(dist)

    narr_dict = zip(distances, latvalues, lonvalues, inLandsat)
    sorted_points = sorted(narr_dict)

    for chosen_points in itertools.combinations(sorted_points, 4):
        chosen_points = numpy.asarray(chosen_points)
        
        if funcs.is_square_test(chosen_points[:,1:3]) is True:
            break

    return chosen_points[:,3], chosen_points[:, 1:3]
    
def read(narr_indices, scene_dir):
    p = numpy.asarray([1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 725, 700, 650, 600, 550, 500, 450, 400, 350, 300, 275, 250, 225, 200, 175, 150, 125, 100])
    pressures = numpy.reshape([p]*4, (4,29))
    dirs = ['HGT_1', 'HGT_2', 'TMP_1', 'TMP_2', 'SHUM_1', 'SHUM_2']
    
    data = [[] for i in range(6)]

    for d in dirs:
        for i in narr_indices:
            for press in p:
                filename = os.path.join(scene_dir, 'narr', d, str(press)+'.txt')
                data[dirs.index(d)].append(float(linecache.getline(filename, int(i+2))))
    
    data = numpy.reshape(data, (6, 4, 29))  # reshape
    hgt_1, hgt_2, tmp_1, tmp_2, shum_1, shum_2 = data   # unpack
    
    rhum_1 = atmo_data.convert_sh_rh(shum_1, tmp_1, pressures)
    rhum_2 = atmo_data.convert_sh_rh(shum_2, tmp_2, pressures)
    
    ght_1 = numpy.divide(hgt_1, 1000.0)   # convert m to km
    ght_2 = numpy.divide(hgt_2, 1000.0)   # convert m to km
    
    return ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
