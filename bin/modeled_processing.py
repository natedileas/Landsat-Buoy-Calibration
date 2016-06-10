import datetime
import os
import math
import numpy
import subprocess
import sys
import logging
import warnings

import narr_data
import merra_data
import atmo_data

### PRE MODTRAN FUNCTIONS ###

def make_tape5s(cc):
    """ Reads atmospheric data and generates tape5 files for modtran runs. """

    if cc.atmo_src == 'narr':
        data, data_coor = get_narr_data(cc)
    elif cc.atmo_src == 'merra':
        data, data_coor = get_merra_data(cc)

    stan_atmo = atmo_data.read_stan_atmo()   # load standard atmo
    interp_time = atmo_data.interpolate_time(cc.metadata, *data)   # interplolate in time
    atmo_profiles = atmo_data.generate_profiles(interp_time, stan_atmo, data[6])

    interp_profile = None
    with warnings.catch_warnings():
        warnings.filterwarnings('error')
        try:
            interp_profile = atmo_data.offset_interp_space(cc.buoy_location, atmo_profiles, data_coor)
        except RuntimeWarning:
            interp_profile = atmo_data.bilinear_interp_space(cc.buoy_location, atmo_profiles, data_coor)

            if interp_profile[0][0] > 50:
                interp_profile = list(numpy.asarray(interp_profile)[:, 1:])

    # TODO better handling of interpolation
    atmo_data.write_atmo(cc, interp_profile)   # save out to file
    # TODO write out uninterpolated atmosphere
    
    point_dir = generate_tape5(cc, interp_profile)

    return point_dir, data_coor

def get_narr_data(cc):
    """ choose points and retreive narr data from file. """

    # check if downloaded
    temp, height, shum = narr_data.open(cc)

    # choose narr points
    narr_indices, lat, lon = narr_data.get_points(cc.metadata, temp)
    chosen_idxs, narr_coor = narr_data.choose_points(narr_indices, lat, lon, cc.buoy_location)

    # read in NARR data
    data = narr_data.read(cc, temp, height, shum, chosen_idxs)
    #ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures = data   # unpack

    return data, narr_coor

def get_merra_data(cc):
    """ choose points and retreive merra data from file. """ 

    # check if downloaded
    data = merra_data.open(cc)

    # choose points
    points_in_scene, points_in_scene_idx = merra_data.get_points(cc.metadata, data)
    chosen_points_idxs, chosen_points_lat_lon = merra_data.choose_points(points_in_scene, points_in_scene_idx, cc.buoy_location)

    # retrieve data
    data = merra_data.read(cc, data, chosen_points_idxs)

    return data, chosen_points_lat_lon

def generate_tape5(cc, profile):
    """ write the tape5 file """

    height, press, temp, relhum = profile

    # TODO streamline
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
    head_file = os.path.join(modtran_directory, 'head.txt')
    tail_file = os.path.join(modtran_directory, 'tail.txt')
    head = ''
    tail = ''

    jay = datetime.datetime.strftime(cc.date, '%j')
    nml = str(numpy.shape(height)[0])
    gdalt = '%1.3f' % float(height[0])

    with open(head_file,'r') as f:
        head = f.read()
        head = head.replace('nml', nml)
        head = head.replace('gdalt', gdalt)
        head = head.replace('tmp____', '%3.3f' % cc.skin_temp)

    with open(tail_file,'r') as f:
        tail = f.read()
        tail = tail.replace('longit',lonString)
        tail = tail.replace('latitu',latString)
        tail = tail.replace('jay',jay)

    tape5_file = os.path.join(point_dir, 'tape5')

    with open(tape5_file, 'w') as f:
        f.write(head)
        
        for k in range(numpy.shape(height)[0]):
            line = '%10.3f%10.2E%10.2E%10.2E%10s%10s%15s\n' % \
            (height[k], press[k], temp[k], relhum[k] ,'0.000E+00','0.000E+00', 'AAH2222222222 2')
            
            f.write(line)
            
        f.write(tail)

    return point_dir

### MODTRAN FUNCTION ###

def run_modtran(directory):
    exe = '/dirs/pkg/Mod4v3r1/Mod4v3r1.exe'
    d = os.getcwd()
    os.chdir(directory)

    try:
        subprocess.check_call('ln -s /dirs/pkg/Mod4v3r1/DATA', shell=True)
        subprocess.check_call(exe, shell=True)
    except subprocess.CalledProcessError:  # symlink already exits error
        pass

    os.chdir(d)

### POST MODTRAN FUNCTIONS ###

def parse_tape7scn(directory):
    filename = os.path.join(directory, 'tape7.scn')
    
    data = numpy.genfromtxt(filename,  skip_header=11, skip_footer=1, \
    usecols=(0,1,2,6,8), unpack=True)   
    
    wvlen, trans, pth_thm, gnd_ref, total = data
    
    downwell_rad = gnd_ref / trans   # calculate downwelled radiance
    upwell_rad = pth_thm   # calc upwelled radiance
    
    # sanity check
    check = downwell_rad - ((total - upwell_rad) / trans)
    if numpy.sum(numpy.absolute(check)) >= .05:
       logging.error('Error in modtran module. Total Radiance minus upwelled \
       radiance is not (approximately) equal to downwelled radiance*transmission')
       sys.exit(-1)

    return upwell_rad, downwell_rad, wvlen, trans, gnd_ref
    
def calc_temperature_array(wavelengths, temperature):
    """ make array of blackbody radiances. """
    Lt= []

    # TODO try yield keyword
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
