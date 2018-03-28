# Landsat Buoy Calibration
Calculates and compares the radiance of a thermal LANSAT scene to the "ground truth"
radiance as measured by a NOAA buoy. Based on work by Frank Padula and Monica Cook at RIT.

If you want to use this code, you should have a basic knowledge of python and/or basic coding. No warranty. Use it on armstrong or related servers for best results. Developed on Fedora x64 by Nathan Dileas (nid4986@g.rit.edu).
Copyright RIT 2015-2018

## OVERVIEW:
This code essentially has two funtions: calculating the radiance from the landsat image 
provided, and calculating the corresponding ground truth radiance from outside data,
atmospheric (NARR or MERRA-2), NOAA buoy data, and MODTRAN. If atmospheric
data or landsat images need to be downloaded, it will take between 5-7 minutes
for NARR, and 2-3 for MERRA. Use the file forward_model.py as a convinient command line interface:

```
$ python forward_model.py -h
usage: forward_model.py [-h] [-a {merra,narr}] [-v] [-b BANDS [BANDS ...]]
                        scene_id buoy_id

Compute and compare the radiance values of a landsat image to the propogated
radiance of a NOAA buoy, using atmospheric data and MODTRAN.

positional arguments:
  scene_id              LANDSAT or MODIS scene ID. Examples:
                        LC08_L1TP_017030_20170703_20170715_01_T1,
                        MOD021KM.A2011154.1650.006.2014224075807.hdf
  buoy_id               NOAA Buoy ID. Example: 45012

optional arguments:
  -h, --help            show this help message and exit
  -a {merra,narr}, --atmo {merra,narr}
                        Choose atmospheric data source, choices:[narr, merra].
  -v, --verbose
  -b BANDS [BANDS ...], --bands BANDS [BANDS ...]
```

### Installing
See INSTALL.txt

### Test Scenes
- landsat test scene `python forward_model.py LC08_L1TP_017030_20170703_20170715_01_T1 45012`
- modis test scene `python forward_model.py MOD021KM.A2011154.1650.006.2014224075807.hdf 45012`

### Notes
- all the downloaded data will be in a directory: buoy_calib/Landsat-Buoy-Calibration/downloaded_data/
- the settings and paths can be changed in: buoy_calib/Landsat-Buoy-Calibration/buoycalib/settings.py
- these websites will help you search to find your own scenes / buoys
  - for buoys: http://www.ndbc.noaa.gov/
  - for landsat scenes: https://earthexplorer.usgs.gov/,  Collection 1 Level 1 - Landsat 8 OLI/TIRS C1 Level 1
  - for modis scenes: https://ladsweb.modaps.eosdis.nasa.gov/search/, look for Terra-MODIS, then MOD021KM
- landsat scenes before 2017 do not work currently

### Sources:
 - http://scholarworks.rit.edu/theses/2961/ - Padula 08 Thesis
 - http://scholarworks.rit.edu/theses/8513/ - Cook 14 Thesis

### Tools:
 - tools/to_csv.py: used to compile results quickly and easily.
 - tools/generate_atmo_figure.py : generate a figure using information from a already processed scene.
 - test/functional/run_all_scenes.bash: run a batch of scenes. Move it to this directory before use.

