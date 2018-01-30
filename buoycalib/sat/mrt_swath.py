import utm
import os
import subprocess

from .. import settings


def make_param_file(ds, georef, lat, lon, prm_out, prefix='blah'):
    with open(settings.SWATH2GRID_PRM, 'r') as fin:
        template = fin.read()

    # put relevant data in the template
    template = template.replace('{INPUT_FILENAME}', ds)
    template = template.replace('{OUTPUT_FILENAME}', prefix)
    template = template.replace('{GEOLOCATION_FILENAME}', georef)

    # convert poi to utm coordinates
    x, y, zone, letter = utm.from_latlon(lat, lon)

    # then make the output 400,000 m square centered on the poi
    template = template.replace('{OUTPUT_SPACE_UPPER_LEFT_CORNER}', '{0} {1}'.format(x-200000, y+200000))
    template = template.replace('{OUTPUT_SPACE_LOWER_RIGHT_CORNER}', '{0} {1}'.format(x+200000, y-200000))
    template = template.replace('{OUTPUT_PROJECTION_ZONE}', str(zone))

    with open(prm_out, 'w') as fout:
        fout.write(template)

    return prm_out


def run_swath2grid(param_file):

    # move to directory
    cwd = os.getcwd()
    d = '/'.join(param_file.split('/')[:-1])
    os.chdir(d)

    # run subprocess
    subprocess.call('/cis/ugrad/nid4986/repos/Senior_Project/MRTSwath/bin/swath2grid -pf={0}'.format(param_file), shell=True)

    # move back to working directory
    os.chdir(cwd)

    # return directory where images are stored
    return d
