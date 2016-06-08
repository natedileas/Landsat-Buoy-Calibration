import subprocess
import datetime
import sys
import logging
import itertools
import os
import utm
import numpy

from netCDF4 import Dataset
import image_processing as img_proc
import atmo_data
import misc_functions as funcs

def download(cc):
    """ download MERRA data. """

    urlbase = 'ftp://goldsmr5.sci.gsfc.nasa.gov/data/s4pa/MERRA2/M2I3NPASM.5.12.4/%s/%s/MERRA2_400.inst3_3d_asm_Np.%s.nc4'
    # year with century, zero padded month, then full date
    url = urlbase % (cc.date.strftime('%Y'), cc.date.strftime('%m'), cc.date.strftime('%Y%m%d'))

    if os.path.isfile(os.path.join(cc.scene_dir, url.split('/')[-1])):   # if file already downloaded
        return
    
    subprocess.check_call('wget %s -P %s' % (url, cc.scene_dir), shell=True)

def open(cc):
    """ open MERRA file (netCDF4 format). """

    merra_file = os.path.join(cc.scene_dir, 'MERRA2_400.inst3_3d_asm_Np.%s.nc4' % cc.date.strftime('%Y%m%d'))

    if os.path.isfile(merra_file) is not True:
        logging.error('MERRA Data file does not exist at the expected path: %' % merra_file)
        sys.exit(1)

    rootgrp = Dataset(merra_file, "r", format="NETCDF4")
    return rootgrp


def get_points(metadata, data):
    lat = data.variables['lat'][:]
    lon = data.variables['lon'][:]

    # define corners
    UL_lat = metadata['CORNER_UL_LAT_PRODUCT'] + 0.5
    UL_lon = metadata['CORNER_UL_LON_PRODUCT'] - 0.5
    LR_lat = metadata['CORNER_LR_LAT_PRODUCT'] - 0.5
    LR_lon = metadata['CORNER_LR_LON_PRODUCT'] + 0.5

    # pull out points that lie within the corners
    lat_in_image = lat[numpy.where((lat<UL_lat) & (lat>LR_lat))]
    lon_in_image = lon[numpy.where((lon>UL_lon) & (lon<LR_lon))]

    in_image_lat_lon = []
    in_image_idx = []

    for lt in lat_in_image:
        for ln in lon_in_image:
           in_image_lat_lon.append([lt, ln])
           in_image_idx.append([numpy.where(lat==lt)[0][0], numpy.where(lon==ln)[0][0]])

    return in_image_lat_lon, in_image_idx

def choose_points(points_in_image, points_in_image_idx, buoy_coors):
    
    points_in_image = numpy.asarray(points_in_image)
    latvalues = points_in_image[:, 0]
    lonvalues = points_in_image[:, 1]

    eastvector = []
    northvector = []
    
    for i in range(len(points_in_image)): 
        narr_utm_ret = utm.from_latlon(latvalues[i],lonvalues[i])
        eastvector.append(narr_utm_ret[0])
        northvector.append(narr_utm_ret[1])
        
    eastvector = numpy.asarray(eastvector)
    northvector = numpy.asarray(northvector)

    buoy_x, buoy_y, buoy_zone_num, buoy_zone_let = utm.from_latlon(*buoy_coors)

    distances = []
    dist_idx = []

    for g in range(len(points_in_image)):
        try:
            dist = atmo_data.distance_in_utm(eastvector[g],northvector[g],buoy_x,buoy_y)
            distances.append(dist)
            dist_idx.append(g)
        except IndexError as e:
            print e

    narr_dict = zip(distances, latvalues, lonvalues, numpy.asarray(points_in_image_idx, dtype=object))
    sorted_points = numpy.asarray(sorted(narr_dict))

    for chosen_points in itertools.combinations(sorted_points, 4):
        chosen_points = numpy.asarray(chosen_points)
        
        if funcs.is_square_test(chosen_points[:,1:3]) is True:
            break

    return chosen_points[:,3], chosen_points[:, 1:3]

def read(cc, data, chosen_points):
    """ pull out necesary data and return it. """

    chosen_points = numpy.array(list(chosen_points))

    latidx = tuple(chosen_points[:, 0])
    lonidx = tuple(chosen_points[:, 1])

    date = datetime.datetime.strptime(cc.metadata['SCENE_CENTER_TIME'].replace('"', '')[0:7], '%H:%M:%S')
    hour = date.hour
    rem1 = hour % 3
    rem2 = 3 - rem1
    hour1 = 60 * (hour - rem1)
    hour2 = 60 * (hour + rem2)

    idx1 = numpy.where(data.variables['time'][:] == hour1)[0][0]
    idx2 = numpy.where(data.variables['time'][:] == hour2)[0][0]
 
    p = numpy.array(data.variables['lev'][:])
    pressure = numpy.reshape([p]*4, (4, len(p)))

    temp1 = numpy.asarray(data.variables['T'])[idx1, :, latidx, lonidx]   # temp
    temp2 = numpy.asarray(data.variables['T'])[idx2, :, latidx, lonidx]   

    rh1 = numpy.asarray(data.variables['RH'])[idx1, :, latidx, lonidx]   # relative humidity
    rh2 = numpy.asarray(data.variables['RH'])[idx2, :, latidx, lonidx]

    height1 = numpy.asarray(data.variables['H'])[idx1, :, latidx, lonidx]   # height
    height2 = numpy.asarray(data.variables['H'])[idx2, :, latidx, lonidx]

    # convert m to km
    return height1 / 1000.0, height2 / 1000.0, temp1, temp2, rh1, rh2, pressure
