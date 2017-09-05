# Landsat Buoy Calibration
Calculates and compares the radiance of a thermal LANSAT scene to the "ground truth"
radiance as measured by a NOAA buoy. Based on work by Frank Padula and Monica Cook at RIT.

If you want to use this code, you should have a basic knowledge of python and/or basic coding. No warranty. Use it on armstrong or related servers for best results. Developed on Fedora x64 by Nathan Dileas. 
Copyright RIT 2015-2017

## OVERVIEW:
This code essentially has two funtions: calculating the radiance from the landsat image 
provided, and calculating the corresponding ground truth radiance from outside data,
atmospheric (NARR or MERRA-2), NOAA buoy data, and MODTRAN. Use the file buoy-calib.py as
a convinient command line interface:

```
$ python buoy-calib.py -h
usage: buoy-calib.py [-h] [-b BUOY_ID] [-a {merra,narr}]
                     scene_id [scene_id ...]

Compute and compare the radiance values of a landsat image to the propogated
radiance of a NOAA buoy, using atmospheric data and MODTRAN. If atmospheric
data or landsat images need to be downloaded, it will take between 5-7 minutes
for NARR, and 2-3 for MERRA. If nothing need to be downloaded, it will usually
take less than 30 seconds for a single scene.

positional arguments:
  scene_id              LANDSAT scene ID. Examples: LC80330412013145LGN00,
                        LE70160382012348EDC00, LT50410372011144PAC01

optional arguments:
  -h, --help            show this help message and exit
  -b BUOY_ID, --buoy_id BUOY_ID
                        NOAA Buoy ID. Example: 44009
  -a {merra,narr}, --atmo {merra,narr}
                        Choose atmospheric data source, choices:[narr, merra].
```

### Sources:
 - http://scholarworks.rit.edu/theses/2961/ - Padula 08 Thesis
 - http://scholarworks.rit.edu/theses/8513/ - Cook 14 Thesis

### Tools:
 - tools/to_csv.py: used to compile results quickly and easily.
 - tools/generate_atmo_figure.py : generate a figure using information from a already processed scene.
 - test/functional/run_all_scenes.bash: run a batch of scenes. Move it to this directory before use.

