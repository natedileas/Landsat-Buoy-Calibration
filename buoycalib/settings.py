from os.path import join, normpath

# directories and files
#PACKAGE_BASE = normpath(join(__file__, '../..'))
DATA_BASE = '/dirs/home/ugrad/nid4986/landsat_data/'

MERRA_DIR = join(DATA_BASE, 'merra')
NARR_DIR = join(DATA_BASE, 'narr')
NOAA_DIR = join(DATA_BASE, 'noaa')
LANDSAT_DIR = join(DATA_BASE, 'landsat_scenes')

MODTRAN_DATA = '/dirs/pkg/Mod4v3r1/DATA'
MODTRAN_EXE = '/dirs/pkg/Mod4v3r1/Mod4v3r1.exe'

MISC_FILES = join(DATA_BASE, 'misc')
HEAD_FILE_TEMP = join(MISC_FILES, 'head.txt')  # tape5 templates
TAIL_FILE_TEMP = join(MISC_FILES, 'tail.txt')
STAN_ATMO = join(MISC_FILES, 'stanAtm.txt')

# urls
MERRA_URL = 'ftp://goldsmr5.sci.gsfc.nasa.gov/data/s4pa/MERRA2/M2I3NPASM.5.12.4/%s/%s/MERRA2_400.inst3_3d_asm_Np.%s.nc4'
NARR_URLS = ['ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/air.%s.nc', 
            'ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/hgt.%s.nc',
            'ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/shum.%s.nc']
NOAA_URLS = ['http://www.ndbc.noaa.gov/data/historical/stdmet/%sh%s.txt.gz',
            'http://www.ndbc.noaa.gov/data/stdmet/%s%s%s2015.txt.gz']
LANDSAT_URL = 'http://earthexplorer.usgs.gov/download/%s/%s/STANDARD/EE'

# usgs login
USERNAME = 'nid4986'
PASSWORD = 'Carlson89'
USGS_LOGIN = {'username':USERNAME, 'password':PASSWORD}


if self.satelite == 'LC8':   # L8
    rsr_files = [[10, os.path.join(settings.DATA_BASE, 'misc', 'L8_B10.rsp')], \
                [11, os.path.join(settings.DATA_BASE, 'misc', 'L8_B11.rsp')]]
    img_files = [[10, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_10'])], \
                [11, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_11'])]]
elif self.satelite == 'LE7':   # L7
    rsr_files = [[6, os.path.join(settings.DATA_BASE, 'misc', 'L7_B6_2.rsp')]]
    img_files = [[6, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_6_VCID_2'])]]
elif self.satelite == 'LT5':   # L5
    rsr_files = [[6, os.path.join(settings.DATA_BASE, 'misc', 'L5_B6.rsp')]]
    img_files = [[6, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_6'])]]