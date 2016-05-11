import datetime
import os
import math
import numpy
import subprocess
import sys
import logging
import narr_data

### POST MODTRAN FUNCTIONS ###

def read_tape6(case):
    """ parse tape6 files and return values. """

    wavelengths = numpy.zeros(0)
    radiance_up = numpy.zeros(0)
    radiance_dn = numpy.zeros(0)
    transission = numpy.zeros(0)
    
    filename = os.path.join(case, 'parsed')
    
    wavelength = []
    upwelled_radiance = []
    gnd_reflected_radiance = []
    transmission_parsed = []
    total = []

    # read data from file     
    with open(filename, 'r') as f:
        for line in f:
            w, ur, grr, tot, t = line.split(' ')
            wavelength.append(float(w))
            upwelled_radiance.append(float(ur))
            gnd_reflected_radiance.append(float(grr))
            total.append(float(tot))
            transmission_parsed.append(float(t))
    
    # calculate upwelled radiance and transmission
    transission = numpy.asarray(transmission_parsed)
    radiance_up = numpy.asarray(upwelled_radiance)
        
    # calculate downwelled radiance
    transission[numpy.where(transission==0.0000)[0]] = 0.00001
    gnd_reflected_radiance = numpy.asarray(gnd_reflected_radiance)
    radiance_dn = numpy.divide(gnd_reflected_radiance, transission)
    
    # sanity check
    total = numpy.asarray(total)
    radiance_dn_check = numpy.divide(numpy.subtract(total, radiance_up), transission)
    check = numpy.subtract(radiance_dn, radiance_dn_check)
    
    if numpy.sum(numpy.absolute(check)) >= .05:
       logging.error('Error in modtran module. Total Radiance minus upwelled radiance is not (approximately) equal to downwelled radiance*transmission')
       sys.exit(-1)

    wavelength = numpy.asarray(wavelength)
    
    # flip wavelength, radiance, and transmission arrays...
    # Tape6parser returns them backwards
    wavelength = numpy.tile(wavelength,(1,1))
    wavelength = numpy.fliplr(wavelength)
    wavelength = wavelength[0]
    
    radiance_up = numpy.tile(radiance_up,(1,1))
    radiance_up = numpy.fliplr(radiance_up)
    radiance_up = radiance_up[0]
    
    radiance_dn = numpy.tile(radiance_dn,(1,1))
    radiance_dn = numpy.fliplr(radiance_dn)
    radiance_dn = radiance_dn[0]
    
    transission = numpy.tile(transission,(1,1))
    transission = numpy.fliplr(transission)
    transission = transission[0]
    
    gnd_reflected_radiance = numpy.tile(gnd_reflected_radiance,(1,1))
    gnd_reflected_radiance = numpy.fliplr(gnd_reflected_radiance)
    gnd_reflected_radiance = gnd_reflected_radiance[0]
    
    return radiance_up, radiance_dn, wavelength, transission, gnd_reflected_radiance
        
def offset_bilinear_interp(array, narr_coor, buoy_coors):
    """ interpolate to buoy location. """

    a = -narr_coor[0,0] + narr_coor[2,0]
    b = -narr_coor[0,0] + narr_coor[1,0]
    c = narr_coor[0,0] - narr_coor[1,0] - narr_coor[2,0] + narr_coor[3,0]
    d = buoy_coors[0] - narr_coor[0,0]
    
    e = -narr_coor[0,1] + narr_coor[2,1]
    f = -narr_coor[0,1] + narr_coor[1,1]
    g = narr_coor[0,1] - narr_coor[1,1] - narr_coor[2,1] + narr_coor[3,1]
    h = buoy_coors[1] - narr_coor[0,1]
    
    i = math.sqrt(abs(-4*(c*e - a*g)*(d*f - b*h) + (b*e - a*f + d*g - c*h)**2))
    
    alpha = -(b*e - a*f + d*g - c*h + i)/(2*c*e - 2*a*g)    
    beta  = -(b*e - a*f - d*g + c*h + i)/(2*c*f - 2*b*g)
    
    return ((1 - alpha) * ((1 - beta) * array[0] + beta * array[1]) + alpha * ((1 - beta) * array[2] + beta * array[3]))
        
def read_RSR(rsr_file):
    """ read in RSR data and return it to the caller. """
    wavelength_RSR = []
    RSR = []
    trans_RSR = []
    data = []
    
    with open(rsr_file, 'r') as f:
        for line in f:    
            data = line.split()
            data = filter(None, data)
            wavelength_RSR.append(float(data[0]))
            RSR.append(float(data[1]))
    
    return RSR, wavelength_RSR
    
def calc_temperature_array(wavelengths, temperature):
    """ make array of blackbody radiances. """
    Lt= []

    for d_lambda in wavelengths:
        x = radiance(d_lambda, temperature)
        Lt.append(x)
        
    return Lt
        
def radiance(wvlen, temp, units='microns'):
    """calculate blackbody radiance given wavelength (in meters) and temperature. """
    
    # define constants
    c = 3e8   # speed of light, m s-1
    h = 6.626e-34	# J*s = kg m2 s-1
    k = 1.38064852e-23 # m2 kg s-2 K-1, boltzmann
    
    c1 = 2 * (c * c) * h   # units = kg m4 s-3
    c2 = (h * c) / k    # (h * c) / k, units = m K    
        
    # calculate radiance
    rad = c1 / (((wvlen**5)) * (math.e**((c2 / (temp * wvlen))) - 1))
    
    # UNITS
    # (W / m^2 * sr) * <wavelength unit>
    return rad
        
def integrate(x, y, method='trap'):
    """approximate integration given two arrays.
    """
    total = 0
    
    if method == 'trap':
        for i in xrange(len(x)):
            try:
                # calculate area of trapezoid and add to total
                area = .5*(x[i+1]-x[i])*(y[i]+y[i+1])
                total += area
            except IndexError:
                break
                
    if method == 'rect':
        for i in xrange(0, len(x)):
            try:
                # calculate area of rectangle and add to total
                area = (x[i+1]-x[i])*(y[i])
                total += abs(area)
            except IndexError:
                break
                
    return total

### PRE MODTRAN FUNCTIONS ###

def make_tape5s(cc):
    """ Reads narr data and generates tape5 files for modtran runs. """

    if os.path.exists(os.path.join(cc.scene_dir, 'narr/HGT_1/1000.txt')):
        logging.info('NARR Data Successful Download')
    else:
        logging.error('NARR data not downloaded, no wgrib?')
        sys.exit(-1)
        
    # choose narr points
    filename = os.path.join(cc.filepath_base, './data/shared/narr/coordinates.txt')
    narr_indices, lat, lon = narr_data.get_points(filename, cc.metadata)
    narr_indices, narr_coor = narr_data.choose_points(narr_indices, lat, lon, cc.buoy_location)

    # read in NARR data
    data = narr_data.read(narr_indices, lat, cc.scene_dir)
    #ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures = data   # unpack
    
    interp_time = narr_data.interpolate_time(cc.metadata, *data)   # interplolate in time
    stan_atmo = narr_data.read_stan_atmo()   # load standard atmo
    atmo_profiles = generate_profiles(interp_time, stan_atmo, data[6])
    
    interp_profile = narr_data.interp_space(cc, atmo_profiles, narr_coor)
    point_dir = generate_tape5(cc, interp_profile)

    return point_dir, narr_coor
    
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
        
        # interpolate linearly between stan atmo and narr data
        above = numpy.where(stan_height > hgt[-1])[0]
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

def generate_tape5(cc, profile):
    """ write the tape5 file """

    height, press, temp, relhum = profile
    latString = '%2.3f' % (cc.buoy_location[0])
    
    if cc.buoy_location[1] < 0:
        lonString = '%2.2f' % cc.buoy_location[1]
    else:
        lonString = '%2.3f' % (360.0 - cc.buoy_location[1])

    point_dir = os.path.join(cc.scene_dir, 'points/%s_%s' % (latString, lonString))
        
    try:
        os.makedirs(point_dir)
    except OSError:
        pass

    modtran_directory = os.path.join(cc.filepath_base, 'data/shared/modtran')
    filename = os.path.join(modtran_directory, 'tempLayers.txt')

    with open(filename, 'w') as f:
        for k in range(numpy.shape(height)[0]):
            line = '%10.3f%10.3e%10.3e%10.3e%10s%10s%15s\n' % \
            (height[k], press[k], temp[k], relhum[k] ,'0.000E+00','0.000E+00', 'AAH2222222222 2')
            
            line = line.replace('e', 'E')
            f.write(line)
    
    jay = datetime.datetime.strftime(cc.date, '%j')
    nml = str(numpy.shape(height)[0])
    gdalt = '%1.3f' % float(height[0])
    
    # write header and footer parts of tape5 and concatenate
    command = './bin/write_tape5.bash %s %s %s %s %s %s %s %s' % \
    (modtran_directory, point_dir, latString, lonString, jay, nml, gdalt, '%3.3f' % cc.skin_temp)
    subprocess.check_call(command, shell=True)

    return point_dir
