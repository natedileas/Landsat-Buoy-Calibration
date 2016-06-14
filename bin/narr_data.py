import numpy
import linecache
import utm
import itertools
import os
import sys
import subprocess
import logging
from netCDF4 import Dataset, num2date

import image_processing as img_proc
import atmo_data
import misc_functions as funcs

def download(cc):
    """ download NARR Data (netCDF4 format). """
    
    narr_urls = ['ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/air.%s.nc', \
                    'ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/hgt.%s.nc',\
                    'ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/shum.%s.nc']
    
    date = cc.date.strftime('%Y%m')   # YYYYMM
    save_dir = os.path.join(cc.data_base, 'narr')
    
    for url in narr_urls:
        url = url % date
        
        if os.path.isfile(os.path.join(save_dir, url.split('/')[-1])):
            continue   # if file already downloaded
            
        subprocess.check_call('wget %s -P %s' % (url, save_dir), shell=True)

def open(cc):
    """ open NARR file (netCDF4 format). """

    data = []
    narr_files = ['air.%s.nc', 'hgt.%s.nc', 'shum.%s.nc']

    date = cc.date.strftime('%Y%m')
    save_dir = os.path.join(cc.data_base, 'narr')
    
    for data_file in narr_files:
        data_file = os.path.join(save_dir, data_file % date)
        
        if os.path.isfile(data_file) is not True:
            logging.error('NARR Data file is not at the expected path: %' % data_file)
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

    inLandsat = zip(inLandsat[0], inLandsat[1])
    narr_dict = zip(distances, latvalues, lonvalues, numpy.asarray(inLandsat, dtype=object))
    sorted_points = sorted(narr_dict)

    for chosen_points in itertools.combinations(sorted_points, 4):
        chosen_points = numpy.asarray(chosen_points)
        
        if funcs.is_square_test(chosen_points[:,1:3]) is True:
            break

    return chosen_points[:,3], chosen_points[:, 1:3]
    
def read(cc, temp, height, shum, chosen_points):
    """ pull out necesary data and return it. """

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
