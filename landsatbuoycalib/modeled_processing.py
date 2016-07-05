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
import settings

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
        interp_profile, data_coor = narr_data.calc_profile(cc)
    elif cc.atmo_src == 'merra':
        interp_profile, data_coor = merra_data.calc_profile(cc)
        
    # add buoy data at bottom of atmosphere
    interp_profile = numpy.insert(interp_profile, 0, [cc.buoy_height, cc.buoy_press, cc.buoy_airtemp + 273.13, cc.buoy_rh], axis=1)

    atmo_data.write_atmo(cc, interp_profile)   # save out to file

    point_dir = write_tape5(cc, interp_profile)

    return point_dir, data_coor

def write_tape5(cc, profile):
    """
    Write the profile to a tape5 file.
    
    Args:
        cc: CalibrationController object
        profile: atmospheric data: height, press, temp, relhum

    Returns:
        point_dir: directory in which the tape5 is written
    """
    height, press, temp, relhum = profile

    if cc.buoy_location[1] < 0:
        lonString = '%2.2f' % cc.buoy_location[1]
    else:
        lonString = '%2.3f' % (360.0 - cc.buoy_location[1])

    point_dir = os.path.join(cc.scene_dir, 'modtran_%s' % cc.buoy_id)

    try:
        os.makedirs(point_dir)
    except OSError:
        pass

    jay = datetime.datetime.strftime(cc.date, '%j')   # day of year (julian)
    nml = str(numpy.shape(height)[0])   # number of layers
    gdalt = '%1.3f' % float(height[0])   # ground altitude

    with open(settings.HEAD_FILE_TEMP, 'r') as f:
        head = f.read()
        head = head.replace('nml', nml)
        head = head.replace('gdalt', gdalt)
        head = head.replace('tmp____', '%3.3f' % cc.skin_temp)

    with open(settings.TAIL_FILE_TEMP, 'r') as f:
        tail = f.read()
        tail = tail.replace('longit', lonString)
        tail = tail.replace('latitu', '%2.3f' % cc.buoy_location[0])
        tail = tail.replace('jay', jay)

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
    d = os.getcwd()
    os.chdir(directory)

    try:
        subprocess.check_call('ln -sf %s' % settings.MODTRAN_DATA, shell=True)
        subprocess.check_call(settings.MODTRAN_EXE, shell=True)
    except subprocess.CalledProcessError:  # symlink already exists error
        pass

    os.chdir(d)

def calc_ltoa(cc, modtran_data):
    """
    Calculate modeled radiance for band 10 and 11.

    Args:
        cc: CalibrationController object
        
        modtran_data: modtran output, Units: [W cm-2 sr-1 um-1]
            upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect

    Returns:
        top of atmosphere radiance: Ltoa [W m-2 sr-1 um-1]
    """
    upwell, downwell, wavelengths, tau, gnd_ref = modtran_data

    # calculate temperature array
    Lt = calc_temperature_array(wavelengths / 1e6, cc.skin_temp) / 1e6   # w m-2 sr-1 um-1

    # Load Emissivity / Reflectivity
    water_file = os.path.join(settings.MISC_FILES, 'water.txt')
    spec_r_wvlens, spec_r = numpy.loadtxt(water_file, unpack=True, skiprows=3)
    spec_ref = numpy.interp(wavelengths, spec_r_wvlens, spec_r)
    spec_emis = 1 - spec_ref   # calculate emissivity

    # calculate top of atmosphere radiance (spectral)
    ## Ltoa = (Lbb(T) * tau * emis) + (gnd_ref * reflect) + pth_thermal  [W m-2 sr-1 um-1]
    Ltoa = (upwell * 1e4 + (Lt * spec_emis * tau) + (spec_ref * gnd_ref * 1e4))

    return Ltoa

def calc_radiance(wavelengths, ltoa, rsr_file):
    """
    Calculate modeled radiance for band 10 and 11.

    Args:
        wavelengths: for LToa [um]
        LToa: top of atmosphere radiance [W m-2 sr-1 um-1]
        rsr_file: relative spectral response data to use

    Returns:
        radiance: L [W m-2 sr-1 um-1]
    """
    RSR_wavelengths, RSR = numpy.loadtxt(rsr_file, unpack=True)

    w = numpy.where((wavelengths > RSR_wavelengths.min()) & (wavelengths < RSR_wavelengths.max()))
    
    wvlens = wavelengths[w]
    ltoa_trimmed = ltoa[w]

    # upsample to wavelength range
    RSR = numpy.interp(wvlens, RSR_wavelengths, RSR)

    # calculate observed radiance [ W m-2 sr-1 um-1 ]
    modeled_rad = numpy.trapz(ltoa_trimmed * RSR, wvlens) / numpy.trapz(RSR, wvlens)
    
    return modeled_rad

def parse_tape7scn(directory):
    """
    Parse modtran output file into needed quantities.

    Args:
        directory: where the file is located

    Returns:
        upwell_rad, downwell_rad, wvlen, trans, gnd_ref:
        Needed info for radiance calculation Units: [W cm-2 sr-1 um-1]
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

    trans[numpy.where(trans == 0)] = 0.000001
    return upwell_rad, downwell_rad, wvlen, trans, gnd_ref

def parse_tape6(directory):
    """
    Parse modtran output file into needed quantities.

    Args:
        directory: where the file is located

    Returns:
        upwell_rad, downwell_rad, wvlen, trans, gnd_ref:
        Needed info for radiance calculation
        Units: [W cm-2 sr-1 um-1]
    """
    filename = os.path.join(directory, 'tape6')

    with open(filename, 'r') as f:
        data = f.read()

    d = data.split('\n')
    a = []
    
    for idx, i in enumerate(d):
        i = i.split()
        
        try:
            if 710 <= float(i[0]) <= 1120 and len(i) == 15:
                a.append(i)
        except IndexError:
            pass
        except ValueError:
            pass
    
    data = numpy.array(a, dtype=numpy.float64)
    data = data[:, (1,3,9,12,14)]
            
    wvlen, upwell_rad, gnd_ref, total, trans = data.T

    return upwell_rad[::-1], None, wvlen[::-1], trans[::-1], gnd_ref[::-1]
    
def calc_temperature_array(wavelengths, temperature):
    """
    Calculate spectral radiance array based on blackbody temperature.

    Args:
        wavelengths: wavelengths to calculate at [meters]
        temperature: temp to use in blackbody calculation [Kelvin]

    Returns:
        Lt: spectral radiance array [W m-2 sr-1 m-1]
    """
    Lt= []

    for d_lambda in wavelengths:
        x = radiance(d_lambda, temperature)
        Lt.append(x)
        
    return numpy.asarray(Lt)
        
def radiance(wvlen, temp):
    """
    Calculate spectral blackbody radiance.

    Args:
        wvlen: wavelength to calculate blackbody at [meters]
        temp: temperature to calculate blackbody at [Kelvin]

    Returns:
        rad: [W m-2 sr-1 m-1]
    """
    # define constants
    c = 3e8   # speed of light, m s-1
    h = 6.626e-34	# J*s = kg m2 s-1
    k = 1.38064852e-23 # m2 kg s-2 K-1, boltzmann
    
    c1 = 2 * (c * c) * h   # units = kg m4 s-3
    c2 = (h * c) / k    # (h * c) / k, units = m K    
        
    rad = c1 / ((wvlen**5) * (math.e**((c2 / (temp * wvlen))) - 1))
    
    return rad
