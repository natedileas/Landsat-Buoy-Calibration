import numpy
import linecache
import image_processing as img_proc
import modeled_processing as mod_proc
import utm
import itertools
import math
import os
import sys

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
    if metadata['CORNER_UL_LAT_PRODUCT'] > 0:
        landsatHemi = 6
    else: 
        landsatHemi = 7
    
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
            dist = distance_in_utm(eastvector[g],northvector[g],buoy_x,buoy_y)
            distances.append(dist) 
            dist_idx.append(g)
        except IndexError as e:
            print e

    narr_dict = zip(distances, latvalues, lonvalues, inLandsat)
    sorted_points = numpy.asarray(sorted(narr_dict))

    for chosen_points in itertools.combinations(sorted_points, 4):
        chosen_points = numpy.asarray(chosen_points)
        if is_square_test(chosen_points[:,1:3]) is True:
            break

    return chosen_points[:,3], chosen_points[:, 1:3]

def is_square_test(points):
    p1, p2, p3, p4 = points

    test = int(line_test(p1, p2, p3))
    test += int(line_test(p4, p1, p2))
    test += int(line_test(p3, p4, p1))
    test += int(line_test(p2, p3, p4))

    return (test == 0)
    
def line_test(p1, p2, p3):
    """ check whether the three points lie on a line. """
    # http://math.stackexchange.com/questions/441182/how-to-check-if-three-coordinates-form-a-line
    # edge condition found with test_line_test.py
    _p1 = numpy.append(p1, 1)
    _p2 = numpy.append(p2, 1)
    _p3 = numpy.append(p3, 1)

    a = numpy.matrix([_p1, _p2, _p3])
    a = a.transpose()

    return (abs(numpy.linalg.det(a)) < 0.001)
    
def read(narr_indices, lat, scene_dir):
    p = numpy.asarray([1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 725, 700, 650, 600, 550, 500, 450, 400, 350, 300, 275, 250, 225, 200, 175, 150, 125, 100])
    pressures = numpy.reshape([p]*4, (4,29))
    dirs = ['HGT_1', 'HGT_2', 'TMP_1', 'TMP_2', 'SHUM_1', 'SHUM_2']
    
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
    
    rhum_1 = convert_sh_rh(shum_1, tmp_1, pressures)
    rhum_2 = convert_sh_rh(shum_2, tmp_2, pressures)
    
    ght_1 = numpy.divide(hgt_1, 1000.0)   # convert m to km
    ght_2 = numpy.divide(hgt_2, 1000.0)   # convert m to km
    
    return ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
        
def convert_sh_rh(specHum, T_k, pressure):
    # Given array of specific humidities, temperature, and pressure, generate array of relative humidities
    # source: http://earthscience.stackexchange.com/questions/2360/how-do-i-convert-specific-humidity-to-relative-humidity
    
    T_k = numpy.asarray(T_k, dtype=numpy.float64)  #numpy.float64
    
    # convert input variables
    T_c = numpy.subtract(T_k, 273.15)   #celcius
    q = specHum   #specific humidity
    p = pressure   #pressures
    
    # compute relative humidity
    a = numpy.divide(numpy.multiply(17.67, T_c), numpy.subtract(T_k, 29.65))
    
    rh = 26.3 * p * q * (1 / numpy.exp(a))
    
    return rh
    
def dewpoint_temp(temp, relhum):
    """ get dewpoint temperature """
    # temp  - temperature in kelvin
    # relhum -  relative humidity, 0-100
    # source: http://climate.envsci.rutgers.edu/pdf/LawrenceRHdewpointBAMS.pdf
    
    return temp - ((100 - relhum) / 5)   # kelvin
        
def convert_geopotential_geometric(geopotential, lat):
    """Convert array of geopotential heightsto geometric heights.
    """
    # source: http://www.ofcm.gov/fmh3/pdf/12-app-d.pdf
    # http://gis.stackexchange.com/questions/20200/how-do-you-compute-the-earths-radius-at-a-given-geodetic-latitude
    
    # convert latitiude to radians
    radlat = (lat * math.pi) / 180.0
    
    # gravity at latitude
    grav_lat = 9.80616 * (1 - 0.002637 * numpy.cos(2 * radlat) + 0.0000059 * numpy.power(numpy.cos(2 * radlat), 2))

    # radius of earth at latitude: R(f)^2 = ( (a^2 cos(f))^2 + (b^2 sin(f))^2 ) / ( (a cos(f))^2 + (b sin(f))^2 )
    R_max = 6378.137    # km
    R_min = 6356.752    # km
    
    part1 = numpy.power((R_max ** 2) * numpy.cos(radlat), 2)
    part2 = numpy.power((R_min ** 2) * numpy.sin(radlat), 2) 
    part3 = numpy.power(R_max * numpy.cos(radlat), 2)
    part4 = numpy.power(R_min * numpy.sin(radlat), 2)
    R_lat = numpy.sqrt((part1 + part2) / (part3 + part4))
    
    # ratio of average gravity to estimated gravity
    grav_ratio = grav_lat * R_lat / 9.80665   #average gravity
    
    # calculate geometric height
    geometric_height = [[0]]*4
    for i in range(4):
        geometric_height[i] = ((R_lat[i] * geopotential[i]) / numpy.absolute(grav_ratio[i] - geopotential[i]))
    
    return numpy.asarray(geometric_height)
        
        
def distance_in_utm(e1, n1, e2, n2):
    """Calculate distances between UTM coordinates.
    """
    
    s = 0.9996    # scale factor 
    r = 6378137.0    # Earth radius
    
    SR1 = s / (math.cos(e1 / r))
    SR2 = s / (math.cos(((e2 - e1) / 6) / r))
    SR3 = s / (math.cos(e2 / r))
    
    Edist = ((e2 - e1) / 6) * (SR1 + 4 * SR2 + SR3)
    
    d = math.sqrt(Edist**2 + (n2 - n1)**2)
    
    return d

def interpolate_time(metadata, h1, h2, t1, t2, r1, r2, p):
    # determine three hour-increment before and after scene center scan time
    time = metadata['SCENE_CENTER_TIME'].replace('"', '')
    hour = int(time[0:2])
    minute = int(time[3:5])
    second = int(time[6:8])
    
    date = metadata['DATE_ACQUIRED']
    year = int(date[0:4])
    month = int(date[5:7])
    day = int(date[8:10])

    rem1 = hour % 3
    rem2 = 3 - rem1
    hour1 = hour - rem1
    hour2 = hour + rem2

    # round to nearest minute
    if second > 30: minute = minute + 100

    # convert hour-min acquisition time to decimal time
    time = hour + minute / 60.0

    # interpolate in time
    height = h1 + (time-hour1) * ((h2 - h1)/(hour2 - hour1))
    rhum = r1 + (time-hour1) * ((r2 - r1)/(hour2 - hour1))
    temp = t1 + (time-hour1) * ((t2 - t1)/(hour2 - hour1))

    return height, rhum, temp

def interp_space(buoy_coor, atmo_profiles, narr_coor):
    """ interpolate in space between the 4 profiles. """
    atmo_profiles = numpy.array(atmo_profiles)
    length = numpy.shape(atmo_profiles)[2]
    atmo_profiles = atmo_profiles[:,:length]
    narr_coor = numpy.asarray(narr_coor, dtype=float).round(8)

    height = mod_proc.offset_bilinear_interp(atmo_profiles[:, 0], narr_coor, buoy_coor)
    press = mod_proc.offset_bilinear_interp(atmo_profiles[:, 1], narr_coor, buoy_coor)
    temp = mod_proc.offset_bilinear_interp(atmo_profiles[:, 2], narr_coor, buoy_coor)
    relhum = mod_proc.offset_bilinear_interp(atmo_profiles[:, 3], narr_coor, buoy_coor)
    
    return height, press, temp, relhum
    
def read_stan_atmo(filename='./data/shared/modtran/stanAtm.txt'):
    # read in file containing standard mid lat summer atmosphere information 
    # to be used for upper layers of atmo profile
    stan_atmo = []
    chars = ['\n']

    with open(filename, 'r') as f:
        for line in f:
            data = line.translate(None, ''.join(chars))
            data = data.split()
            data = filter(None, data)
            data = [float(j) for j in data]
            stan_atmo.append(data)

    stan_atmo = numpy.asarray(stan_atmo)
    
    return stan_atmo[:,0], stan_atmo[:,1], stan_atmo[:,2], stan_atmo[:,3]

def write_atmo(cc, atmo):
    filename = os.path.join(cc.scene_dir, 'atmo_interp.txt')
    
    atmo = numpy.array(atmo)
    dewpoint =  dewpoint_temp(atmo[2], atmo[3])

    save_array = numpy.append(atmo, dewpoint)
    save_array = numpy.transpose(numpy.reshape(save_array, (5, numpy.shape(atmo[2])[0])))

    numpy.savetxt(filename, save_array, fmt='%f\t%f\t%f\t%f\t%f')
