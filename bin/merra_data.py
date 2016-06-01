import subprocess
import datetime
from netCDF4 import Dataset

def download(cc):
    """ download MERRA data. """

    urlbase = 'ftp://goldsmr5.sci.gsfc.nasa.gov/data/s4pa/MERRA2/M2I3NPASM.5.12.4/%s/%s/MERRA2_400.inst3_3d_asm_Np.%s.nc4'
    # year with century, zero padded month, then full date
    url = urlbase % (cc.date.strftime('%Y'), cc.date.stftime('%m'), cc.date.strftime('%Y%m%d'))
    subprocess.popen('wget %s -P %s' % (url, cc.scene_dir))

def open(cc):
    """ open MERRA file (netCDF4 format). """

    merra_file = os.path.join(cc.scene_dir, 'MERRA2_400.inst3_3d_asm_Np.%s.nc4' % cc.date.strftime('%Y%m%d'))
    rootgrp = Dataset(merra_file, "r", format="NETCDF4")
    return rootgrp

def read(cc, data):
    """ pull out necesary data and return it. """
    pass

