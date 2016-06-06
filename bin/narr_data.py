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
    """ download NARR Data. """
    if os.path.exists(os.path.join(cc.scene_dir, 'narr/HGT_1/1000.txt')):
        return 0

    # begin download of NARR data
    os.chmod('./bin/NARR_py.bash', 0755)
      
    ret_val = subprocess.call('./bin/NARR_py.bash %s %s %s' % (cc.scene_dir, cc.scene_id, int(cc.verbose)), shell=True)
    if ret_val == 1:
        logging.error('missing wgrib error')
        sys.exit(-1)

def get_coordinates(coordinate_file):
    """ read narr coordinates from file """
    coordinates = []

    with open(coordinate_file, 'r') as f:
        for line in f:
            line.replace('\n', '')
            coordinates.append(line.split())

    return numpy.asarray(coordinates)

def get_points(coordinate_file, metadata):
    """ Read in coordinates.txt, choose points within scene corners. """
    
    # read narr coordinates from file
    coordinates = get_coordinates(coordinate_file)
    
    # pull out lat, lon and reform to 277x349 grids
    narrLat = [c[2] for c in coordinates]
    lat = numpy.reshape(narrLat,(277,349)).astype(float)
    lat[numpy.where(lat > 84)] = 84

    narrLon = numpy.asarray([c[3] for c in coordinates]).astype(float)
    lon = numpy.reshape(narrLon,(277,349)).astype(float)
    east = numpy.where(lon >= 180)
    west = numpy.where(lon < 180)
    lon[east] = 360 - lon[east]
    lon[west] = (-1) * lon[west]

    # define corners
    UL_X = metadata['CORNER_UL_LAT_PRODUCT'] + 0.5
    UL_Y = metadata['CORNER_UL_LON_PRODUCT'] - 0.5
    LR_X = metadata['CORNER_LR_LAT_PRODUCT'] - 0.5
    LR_Y = metadata['CORNER_LR_LON_PRODUCT'] + 0.5
    
    # pull out points that lie within the corners
    inLandsat = numpy.asarray([[None,None],[None,None]])
    x_iter = numpy.arange(277)
    
    for k in numpy.arange(277):
        for l in numpy.arange(349):
            X, Y, zone_num, zone_let = utm.from_latlon(lat[k,l], lon[k,l])
            
            if zone_num <= metadata['UTM_ZONE'] + 1 and zone_num >= metadata['UTM_ZONE'] - 1:
                X, Y = img_proc.convert_utm_zones(lat[k,l], lon[k,l], zone_num, metadata['UTM_ZONE'])
            
            if X < UL_X and X > LR_X:
               if Y > UL_Y and Y < LR_Y:
                   inLandsat = numpy.append(inLandsat, [[k,l]], axis=0)
            
    inLandsat = numpy.delete(inLandsat, 0, 0)
    inLandsat = numpy.delete(inLandsat, 0, 0)
    num_points = numpy.shape(inLandsat)[0]
    
    if num_points == 0:
        print 'No NARR points in landsat scene. Fatal.'
        sys.exit(-1)
    
    return inLandsat, lat, lon
    

def choose_points(inLandsat, lat, lon, buoy_coors, num_points=4):
    latvalues = []
    lonvalues = []
    
    for i in range(len(inLandsat)):
        latvalues.append(lat[inLandsat[i,0],inLandsat[i,1]])
        lonvalues.append(lon[inLandsat[i,0],inLandsat[i,1]])

    eastvector = []
    northvector = []
    
    for i in range(len(inLandsat)): 
        narr_utm_ret = utm.from_latlon(latvalues[i],lonvalues[i])
        eastvector.append(narr_utm_ret[0])
        northvector.append(narr_utm_ret[1])
        
    eastvector = numpy.asarray(eastvector)
    northvector = numpy.asarray(northvector)

    buoy_x, buoy_y, buoy_zone_num, buoy_zone_let = utm.from_latlon(*buoy_coors)

    distances = []
    dist_idx = []

    for g in range(len(inLandsat)):
        try:
            dist = atmo_data.distance_in_utm(eastvector[g],northvector[g],buoy_x,buoy_y)
            distances.append(dist) 
            dist_idx.append(g)
        except IndexError as e:
            print e

    narr_dict = zip(distances, latvalues, lonvalues, inLandsat)
    sorted_points = numpy.asarray(sorted(narr_dict))

    for chosen_points in itertools.combinations(sorted_points, 4):
        chosen_points = numpy.asarray(chosen_points)
        if funcs.is_square_test(chosen_points[:,1:3]) is True:
            break

    return chosen_points[:,3], chosen_points[:, 1:3]
    
def read(narr_indices, lat, scene_dir):
    p = numpy.asarray([1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 725, 700, 650, 600, 550, 500, 450, 400, 350, 300, 275, 250, 225, 200, 175, 150, 125, 100])
    pressures = numpy.reshape([p]*4, (4,29))
    dirs = ['HGT_1', 'HGT_2', 'TMP_1', 'TMP_2', 'SHUM_1', 'SHUM_2']
    import misc_functions as funcs
    shape = [277,349]
    indices = [numpy.ravel_multi_index(idx, shape) for idx in narr_indices]
    
    data = [[] for i in range(6)]
    
    for d in dirs:
        for i in indices:
            for press in p:
                filename = os.path.join(scene_dir, 'narr', d, str(press)+'.txt')
                data[dirs.index(d)].append(float(linecache.getline(filename, i+2)))
    
    data = numpy.reshape(data, (6, 4, 29))  # reshape
    hgt_1, hgt_2, tmp_1, tmp_2, shum_1, shum_2 = data   # unpack
    
    rhum_1 = atmo_data.convert_sh_rh(shum_1, tmp_1, pressures)
    rhum_2 = atmo_data.convert_sh_rh(shum_2, tmp_2, pressures)
    
    ght_1 = numpy.divide(hgt_1, 1000.0)   # convert m to km
    ght_2 = numpy.divide(hgt_2, 1000.0)   # convert m to km
    
    return ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
