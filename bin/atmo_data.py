import numpy
import os
import math

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

def offset_interp_space(buoy_coor, atmo_profiles, narr_coor):
    """ interpolate in space between the 4 profiles. """
    atmo_profiles = numpy.array(atmo_profiles)
    length = numpy.shape(atmo_profiles)[2]
    atmo_profiles = numpy.array(atmo_profiles[:,:length])
    narr_coor = numpy.asarray(narr_coor, dtype=float).round(8)

    alpha, beta = calc_interp_weights(narr_coor, buoy_coor)

    if abs(alpha) > 100 or abs(beta) > 100:
        alpha, beta = calc_interp_weights(numpy.absolute(narr_coor), numpy.absolute(buoy_coor))
        
    height = use_interp_weights(atmo_profiles[:, 0], alpha, beta)
    press = use_interp_weights(atmo_profiles[:, 1], alpha, beta)
    temp = use_interp_weights(atmo_profiles[:, 2], alpha, beta)
    relhum = use_interp_weights(atmo_profiles[:, 3], alpha, beta)

    return height, press, temp, relhum

def calc_interp_weights(interp_from, interp_to):
    """ Calculate weights for the offset bilinear interpolation  of 4 points. """
    a = -interp_from[0,0] + interp_from[2,0]
    b = -interp_from[0,0] + interp_from[1,0]
    c = interp_from[0,0] - interp_from[1,0] - interp_from[2,0] + interp_from[3,0]
    d = interp_to[0] - interp_from[0,0]

    e = -interp_from[0,1] + interp_from[2,1]
    f = -interp_from[0,1] + interp_from[1,1]
    g = interp_from[0,1] - interp_from[1,1] - interp_from[2,1] + interp_from[3,1]
    h = interp_to[1] - interp_from[0,1]

    i = math.sqrt(abs(-4*(c*e - a*g)*(d*f - b*h) + (b*e - a*f + d*g - c*h)**2))

    alpha = -(b*e - a*f + d*g - c*h + i)/(2*c*e - 2*a*g)
    beta  = -(b*e - a*f - d*g + c*h + i)/(2*c*f - 2*b*g)

    return alpha, beta

def use_interp_weights(array, alpha, beta):
    """ Calculate the offset bilinear interpolation  of 4 points. """
    return ((1 - alpha) * ((1 - beta) * array[0] + beta * array[1]) + \
            alpha * ((1 - beta) * array[2] + beta * array[3]))

def bilinear_interp_space(buoy_coor, atmo_profiles, data_coor):
    """ interpolate in space between the 4 profiles. """
    # shape of atmo profiles - 4 x 4 x X
    #                     points x data type x layers
    atmo_profiles = numpy.array(atmo_profiles)
    length = numpy.shape(atmo_profiles)[2]
    atmo_profiles = numpy.array(atmo_profiles[:,:length])
    data_coor = list(data_coor)
    
    height_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,0,:]) for i in range(4)]
    height = bilinear_interpolation(buoy_coor[0], buoy_coor[1], height_points)

    press_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,1,:]) for i in range(4)]
    press = bilinear_interpolation(buoy_coor[0], buoy_coor[1], press_points)

    temp_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,2,:]) for i in range(4)]
    temp = bilinear_interpolation(buoy_coor[0], buoy_coor[1], temp_points)

    relhum_points = [(data_coor[i][0], data_coor[i][1], atmo_profiles[i,3,:]) for i in range(4)]
    relhum = bilinear_interpolation(buoy_coor[0], buoy_coor[1], relhum_points)

    return [height, press, temp, relhum]

def bilinear_interpolation(x, y, points):
    '''Interpolate (x,y) from values associated with four points.

    The four points are a list of four triplets:  (x, y, value).
    The four points can be in any order.  They should form a rectangle.

        >>> bilinear_interpolation(12, 5.5,
        ...                        [(10, 4, 100),
        ...                         (20, 4, 200),
        ...                         (10, 6, 150),
        ...                         (20, 6, 300)])
        165.0

    '''
    # See formula at:  http://en.wikipedia.org/wiki/Bilinear_interpolation
    # credit: http://stackoverflow.com/questions/8661537/how-to-perform-bilinear-interpolation-in-python

    points = sorted(points)               # order points by x, then by y
    (x1, y1, q11), (_x1, y2, q12), (x2, _y1, q21), (_x2, _y2, q22) = points
    

    if x1 != _x1 or x2 != _x2 or y1 != _y1 or y2 != _y2:
        raise ValueError('points do not form a rectangle')
    if not x1 <= x <= x2 or not y1 <= y <= y2:
        raise ValueError('(x, y) not within the rectangle')

    return (q11 * (x2 - x) * (y2 - y) +
            q21 * (x - x1) * (y2 - y) +
            q12 * (x2 - x) * (y - y1) +
            q22 * (x - x1) * (y - y1)
           ) / ((x2 - x1) * (y2 - y1) + 0.0)

def generate_profiles(interp_atmo, stan_atmo, pressures):
    # unpack
    height, rhum, temp = interp_atmo
    stan_height, stan_press, stan_temp, stan_rhum = stan_atmo

    profiles = []
    
    for point_idx in range(4):
        
        p = pressures[0]
        t = temp[point_idx]
        hgt = height[point_idx]
        rh = rhum[point_idx]

        gdalt = hgt[0]
        
        # interpolate linearly between stan atmo and input data
        above = numpy.where(stan_height > hgt[-1])[0]
        if len(above) > 0:
            interpolateTo = above[0]
          
            newHeight = (stan_height[interpolateTo] + hgt[-1]) / 2.0

            newPressure2 = p[-1] + (newHeight - hgt[-1]) * \
            ((stan_press[interpolateTo] - p[-1]) / (stan_height[interpolateTo] - hgt[-1]))

            newTemperature2 = t[-1] + (newHeight - hgt[-1]) * \
            ((stan_temp[interpolateTo] - t[-1]) / (stan_height[interpolateTo] - hgt[-1]))

            newRelativeHumidity2 = rh[-1] + (newHeight - hgt[-1]) * \
            ((stan_rhum[interpolateTo] - rh[-1]) / (stan_height[interpolateTo] - hgt[-1]))
            
            hgt = numpy.append(numpy.append(hgt, newHeight), stan_height[interpolateTo:-1])
            p = numpy.append(numpy.append(p, newPressure2), stan_press[interpolateTo:-1])
            t = numpy.append(numpy.append(t, newTemperature2), stan_temp[interpolateTo:-1])
            rh = numpy.append(numpy.append(rh, newRelativeHumidity2), stan_rhum[interpolateTo:-1])

        profiles.append([hgt, p, t, rh])

    return profiles

def write_atmo(cc, atmo):
    dir_ = os.path.join(cc.scene_dir,'atmo')
    if not os.path.exists(dir_):
        os.makedirs(dir_)
    
    filename = os.path.join(dir_,'atmo_interp')
    
    if cc.atmo_src == 'narr':
        filename += '_narr.txt'
    elif cc.atmo_src == 'merra':
        filename += '_merra.txt'
    
    atmo = numpy.array(atmo)
    dewpoint =  dewpoint_temp(atmo[2], atmo[3])

    save_array = numpy.append(atmo, dewpoint)
    save_array = numpy.transpose(numpy.reshape(save_array, (5, numpy.shape(atmo[2])[0])))

    numpy.savetxt(filename, save_array, fmt='%f\t%f\t%f\t%f\t%f')
