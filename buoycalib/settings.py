from os.path import join, abspath

# directories and files
PACKAGE_BASE = abspath(join(__file__, '..'))
STATIC = join(PACKAGE_BASE, 'data')
DATA_BASE = '/dirs/home/ugrad/nid4986/landsat_data/'

MERRA_DIR = join(DATA_BASE, 'merra')
NARR_DIR = join(DATA_BASE, 'narr')
NOAA_DIR = join(DATA_BASE, 'noaa')
LANDSAT_DIR = join(DATA_BASE, 'landsat_scenes')

MODTRAN_DATA = '/dirs/pkg/Mod4v3r1/DATA'
MODTRAN_EXE = '/dirs/pkg/Mod4v3r1/Mod4v3r1.exe'

MISC_FILES = join(STATIC, 'modtran')
HEAD_FILE_TEMP = join(MISC_FILES, 'head.txt')  # tape5 templates
TAIL_FILE_TEMP = join(MISC_FILES, 'tail.txt')
STAN_ATMO = join(MISC_FILES, 'stanAtm.txt')
WATER_TXT = join(MISC_FILES, 'water.txt')

BUOY_TXT = join(STATIC, 'noaa', 'buoy_height.txt')
STATION_TXT = join(STATIC, 'noaa', 'station_table.txt')

# urls
MERRA_URL = 'ftp://goldsmr5.sci.gsfc.nasa.gov/data/s4pa/MERRA2/M2I3NPASM.5.12.4/%s/%s/MERRA2_400.inst3_3d_asm_Np.%s.nc4'
NARR_URLS = ['ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/air.%s.nc',
             'ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/hgt.%s.nc',
             'ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/shum.%s.nc']
NOAA_URLS = ['http://www.ndbc.noaa.gov/data/historical/stdmet/%sh%s.txt.gz',
             'http://www.ndbc.noaa.gov/data/stdmet/%s%s%s2015.txt.gz']
LANDSAT_S3_URL = 'https://landsat-pds.s3.amazonaws.com'
MODIS_S3_URL = 'https://modis-pds.s3.amazonaws.com'

# relative spectral responses

RSR_L8_B10 = join(MISC_FILES, 'L8_B10.rsp')
RSR_L8_B11 = join(MISC_FILES, 'L8_B11.rsp')
RSR_L8 = {
    10: RSR_L8_B10,
    11: RSR_L8_B11,
}

WRS2 = join(STATIC, 'wrs2', 'wrs2_descending.shp')
