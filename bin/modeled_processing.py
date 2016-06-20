import datetime
import os
import math
import subprocess
import sys
import logging
import warnings

import numpy

import narr_data
import merra_data
import atmo_data
import misc_functions as funcs

def make_tape5s(cc):
    """
    Read atmospheric data and generates tape5 files for modtran runs. 

    Args:
        cc: CalibrationController object

    Returns:
        point_dir, data_coor: directory where modtran needs to be run, and the
        coordinates of the points where the atmospheric data was taken from.
    """

    if cc.atmo_src == 'narr':
        data, data_coor = get_narr_data(cc)
    elif cc.atmo_src == 'merra':
        data, data_coor = get_merra_data(cc)

    # load standard atmosphere for mid-lat summer
    filename = os.path.join(cc.data_base, 'misc', 'stanAtm.txt')
    stan_atmo = numpy.loadtxt(filename, unpack=True)
    
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
    """
    Choose points and retreive narr data from file.

    Args:
        cc: CalibrationController object

    Returns:
        data: atmospheric data, shape = (7, 4, 29)
            ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
        narr_coor: coordinates of the atmospheric data points
    """

    temp, height, shum = narr_data.open(cc)

    # choose narr points
    narr_indices, lat, lon = narr_data.get_points(cc.metadata, temp)
    chosen_idxs, narr_coor = narr_data.choose_points(narr_indices, lat, lon, cc.buoy_location)

    # read in NARR data
    data = narr_data.read(cc, temp, height, shum, chosen_idxs)

    return data, narr_coor

def get_merra_data(cc):
    """ choose points and retreive merra data from file. """ 
    """

    Args:
        cc: CalibrationController object

    Returns:
        data: atmospheric data, shape = (7, 4, 42)
            ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
        chosen_points_lat_lon: coordinates of the atmospheric data points
    """

    data = merra_data.open(cc)

    # choose points
    points_in_scene, points_in_scene_idx = merra_data.get_points(cc.metadata, data)
    chosen_points_idxs, chosen_points_lat_lon = merra_data.choose_points(points_in_scene, points_in_scene_idx, cc.buoy_location)

    # retrieve data
    data = merra_data.read(cc, data, chosen_points_idxs)

    return data, chosen_points_lat_lon

def generate_tape5(cc, profile):
    """
    Write the profile to a tape5 file.
    
    Args:
        cc: CalibrationController object
        profile: atmospheric data: height, press, temp, relhum

    Returns:
        point_dir: directory in which the tape5 is written
    """
    height, press, temp, relhum = profile

    # TODO streamline
    latString = '%2.3f' % (cc.buoy_location[0])

    if cc.buoy_location[1] < 0:
        lonString = '%2.2f' % cc.buoy_location[1]
    else:
        lonString = '%2.3f' % (360.0 - cc.buoy_location[1])

    point_dir = os.path.join(cc.scene_dir, 'modtran_%s_%s' % (latString, lonString))

    try:
        os.makedirs(point_dir)
    except OSError:
        pass

    modtran_directory = os.path.join(cc.data_base, 'misc')
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

def run_modtran(directory):
    """
    Run modtran in the specified directory.

    Args:
        directory: location to run modtran from.

    Returns:
        None
    """
    exe = '/dirs/pkg/Mod4v3r1/Mod4v3r1.exe'
    d = os.getcwd()
    os.chdir(directory)

    try:
        subprocess.check_call('ln -s /dirs/pkg/Mod4v3r1/DATA', shell=True)
        subprocess.check_call(exe, shell=True)
    except subprocess.CalledProcessError:  # symlink already exists error
        pass

    os.chdir(d)

def calc_radiance(cc, rsr_file, modtran_data):
    """
    Calculate modeled radiance for band 10 and 11.

    Args:
        cc: CalibrationController object
        rsr_file: relative spectral response data to use
        modtran_data: modtran output
            upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect

    Returns:
        radiance: L [W m-2 sr-1 um-1]
    """
    upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect = modtran_data

    RSR_wavelengths, RSR = numpy.loadtxt(rsr_file, unpack=True)
    
    # Load Emissivity / Reflectivity
    water_file = os.path.join(cc.data_base, 'misc', 'water.txt')
    spec_r_wvlens, spec_r = numpy.loadtxt(water_file, unpack=True, skiprows=3)
    
    # resample to rsr wavelength range
    upwell = numpy.interp(RSR_wavelengths, wavelengths, upwell_rad)
    downwell = numpy.interp(RSR_wavelengths, wavelengths, downwell_rad)
    tau = numpy.interp(RSR_wavelengths, wavelengths, transmission)
    gnd_ref = numpy.interp(RSR_wavelengths, wavelengths, gnd_reflect)
    spec_ref = numpy.interp(RSR_wavelengths, spec_r_wvlens, spec_r)
    
    spec_emis = 1 - spec_ref   # calculate emissivity

    RSR_wavelengths = RSR_wavelengths / 1e6   # convert to meters
    
    # calculate temperature array
    Lt = calc_temperature_array(RSR_wavelengths, cc.skin_temp)  # w m-2 sr-1 m-1
    
    # calculate top of atmosphere radiance (spectral)
    ## Ltoa = (Lbb(T) * tau * emis) + (gnd_ref * reflect) + pth_thermal
    term1 = Lt * spec_emis * tau # W m-2 sr-1 m-1
    term2 = spec_ref * gnd_ref * 1e10 # W m-2 sr-1 m-1
    Ltoa = (upwell * 1e10) + term1 + term2   # W m-2 sr-1 m-1
    
    # calculate observed radiance
    numerator = funcs.integrate(RSR_wavelengths, Ltoa * RSR)
    denominator = funcs.integrate(RSR_wavelengths, RSR)
    
    modeled_rad = (numerator / denominator) / 1e6  # W m-2 sr-1 um-1
    return modeled_rad

def parse_tape7scn(directory):
    """
    Parse modtran output file into needed quantities.

    Args:
        directory: where the file is located

    Returns:
        upwell_rad, downwell_rad, wvlen, trans, gnd_ref:
        Needed info for radiance calculation
    """
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
    """
    Calculate spectral radiance array based on blackbody temperature.

    Args:
        wavelengths: wavelengths to calculate at
        temperature: temp to use in blackbody calculation

    Returns:
        Lt: spectral radiance array
    """
    Lt= []

    for d_lambda in wavelengths:
        x = radiance(d_lambda, temperature)
        Lt.append(x)
        
    return Lt
        
def radiance(wvlen, temp):
    """
    Calculate spectral blackbody radiance.

    Args:
        wvlen: wavelength to calculate blackbody at [<wvlen_unit>]
        temp: temperature to calculate blackbody at [Kelvin]

    Returns:
        rad: [W m-2 sr-1 <wvlen_unit>-1]
    """
    # define constants
    c = 3e8   # speed of light, m s-1
    h = 6.626e-34	# J*s = kg m2 s-1
    k = 1.38064852e-23 # m2 kg s-2 K-1, boltzmann
    
    c1 = 2 * (c * c) * h   # units = kg m4 s-3
    c2 = (h * c) / k    # (h * c) / k, units = m K    
        
    # calculate radiance
    rad = c1 / (((wvlen**5)) * (math.e**((c2 / (temp * wvlen))) - 1))
    
    return rad
