import datetime
import os
import subprocess

import numpy

from . import settings


def process(atmosphere, lat, lon, date, directory):
    """
    Make tape5, run modtran and parse tape7.scn for this instance.

    Args:
        atmosphere: list or array, in format to be expanded like this:
            height, press, temp, relhum = atmosphere
        lat: point of interest latitude
        lon: point of interest longitude
        date: python datetime object, scene date and time
        directory: directory in which to run modtran

    Returns:
        Relevant Modtran Outputs: spectral, units: [W cm-2 sr-1 um-1]
            upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect
    """
    make_tape5s(atmosphere, lat, lon, date, directory)

    run(directory)
    tape6_filename = os.path.join(directory, 'tape6')

    wavelengths, upwell_rad, gnd_reflect, total, transmission = parse_tape6(tape6_filename)

    return wavelengths, upwell_rad, gnd_reflect, transmission


def make_tape5s(profile, lat, lon, date, directory):
    """
    Write the profile to a tape5 file.

    Args:
        profile: atmosphere: list or array, in format to be expanded like this:
            height, press, temp, relhum = atmosphere
        lat: point of interest latitude
        lon: point of interest longitude
        date: python datetime object, scene date and time
        directory: directory in which to run modtran and write the tape5
    """
    height, press, temp, relhum = profile

    if lon < 0:
        lon = '%2.2f' % lon
    else:
        lon = '%2.3f' % (360.0 - lon)

    jay = datetime.datetime.strftime(date, '%j')   # Julian dAY

    with open(settings.HEAD_FILE_TEMP, 'r') as f:
        head = f.read()
    head = head.replace('nml', str(numpy.shape(height)[0]))   # NuMber of Layers
    head = head.replace('gdalt', '%1.3f' % float(height[0]))   # GrounD ALTitude
    head = head.replace('tmp____', '%3.3f' % float(temp[0]))   # TeMPerature

    atmosphere = ''
    for i, h in enumerate(height):
        atmosphere += '%10.3f%10.2E%10.2E%10.2E%10s%10s%15s\n' % \
                        (height[i], press[i], temp[i], relhum[i], \
                        '0.000E+00', '0.000E+00', 'AAH2222222222 2')

    with open(settings.TAIL_FILE_TEMP, 'r') as f:
        tail = f.read()
    tail = tail.replace('longit', lon)
    tail = tail.replace('latitu', '%2.3f' % lat)
    tail = tail.replace('jay', jay)

    if not os.path.isdir(directory):
        os.makedirs(directory)

    with open(os.path.join(directory, 'tape5'), 'w') as f:
        f.write(head)
        f.write(atmosphere)
        f.write(tail)


def run(directory):
    """
    Run modtran in the specified directory.

    Args:
        directory: location to run modtran from.
    """
    current_dir = os.getcwd()
    os.chdir(directory)

    try:
        subprocess.check_call('ln -sf %s' % settings.MODTRAN_DATA, shell=True)
        subprocess.check_call(settings.MODTRAN_EXE, shell=True)
    except subprocess.CalledProcessError:  # symlink already exists error
        pass

    os.chdir(current_dir)


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

    data = numpy.genfromtxt(filename, skip_header=11, skip_footer=1,
                            usecols=(0, 1, 2, 6, 8), unpack=True)

    wvlen, trans, pth_thm, gnd_ref, total = data

    downwell_rad = gnd_ref / trans   # calculate downwelled radiance
    upwell_rad = pth_thm   # calc upwelled radiance

    # sanity check
    check = downwell_rad - ((total - upwell_rad) / trans)
    if numpy.sum(numpy.absolute(check)) >= .05:
        raise Exception('Error in modtran module. Total Radiance minus upwelled \
        radiance is not (approximately) equal to downwelled radiance*transmission')

    trans[numpy.where(trans == 0)] = 0.000001
    return upwell_rad, downwell_rad, wvlen, trans, gnd_ref


def parse_tape6(tape6_filename):
    """
    Parse modtran output file into needed quantities.

    Args:
        directory: where the file is located

    Returns:
        wavelengths: [um]
        path_thermal: upwelling radiance [W cm-2 sr-1 um-1]
        ground_refl: reflected downwelling radiance [W cm-2 sr-1 um-1] 
        total: total radiance [W cm-2 sr-1 um-1]
        trans: atmospheric transmission [0-1, unitless]
    """

    with open(tape6_filename, 'r') as f:
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
    data = data[:, (1, 3, 9, 12, 14)]

    wvlen, path_thermal, ground_refl, total, trans = data.T

    return wvlen[::-1], path_thermal[::-1], ground_refl[::-1], total[::-1], trans[::-1]
