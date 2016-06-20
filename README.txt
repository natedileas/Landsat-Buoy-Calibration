Calculates and compares the radiance of a thermal LANSAT scene to the "ground truth"
radiance as measured by a NOAA buoy. Based on work by Frank Padula and Monica Cook.

If you want to use this code, you should have a basic knowledge of python and/or basic coding.
No warranty. Use it on armstrong or related servers, or not at all. Developed on Fedora x64 by Nathan Dileas. 
Copyright RIT 2015-2016

OVERVIEW:
    This code essentially has two funtions: calculating the radiance from the landsat image 
    provided, and calculating the corresponding ground truth radiance from outside data,
    atmospheric (NARR or MERRA-2), NOAA buoy data, and MODTRAN. Use the file controller.py as
    a convinient command line interface or the underying class itself, in bin/BuoyCalib.py.

    Sources:
        http://scholarworks.rit.edu/theses/2961/ - Padula 08 Thesis
        http://scholarworks.rit.edu/theses/8513/ - Cook 14 Thesis

    NARR: 
        This is the primary atmospheric data source for the project. Height, Temperature, 
        Humidity as a funtion of Pressure. NCEP Reanalysis data provided by the NOAA/OAR/ESRL
        PSD, Boulder, Colorado, USA, from their Web site at http://www.esrl.noaa.gov/psd/

        Website: http://www.esrl.noaa.gov/psd/data/gridded/data.narr.html
        FTP: ftp://ftp.cdc.noaa.gov/Datasets/NARR/pressure/
    MERRA-2:
        This is the secondary atmospheric data source for the project. Height, Temperature, 
        Humidity as a funtion of Pressure. It was instituted as a result of the NARR dataset 
        not being up to date. Until late 2016, the NARR archive only reaches to late 2014.

        Website: http://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/
        FTP: ftp://goldsmr5.sci.gsfc.nasa.gov/data/s4pa/MERRA2/M2I3NPASM.5.12.4/
    NOAA:
        This is the only source of water temperature information for the project.

        Website: http://www.ndbc.noaa.gov/
        Data: http://www.ndbc.noaa.gov/data/stations/station_table.txt
            http://www.ndbc.noaa.gov/data/stdmet/
            http://www.ndbc.noaa.gov/data/historical/stdmet/

USAGE: 
    ./buoy-calib, in this directory. Use the -h option for more information 
    on flags and options that are available.

    ./buoy-calib [options] <Landsat_ID>

    Examples:
        ./buoy-calib -i LC80130332013145LGN00 : Output an image with the location 
                                                 of the buoy and narr points drawn on it
        ./buoy-calib -m LE70160382012268EDC00 : Use MERRA data instaed of NARR
        ./buoy-calib -b 44009 LT50410372011048PAC01 : use a specific NOAA buoy
        ./buoy-calib -imvr LC80130332013145LGN00 : Output an image, verbose, reprocesss, with MERRA data


    The Landsat ID can be any valid ID from landsat 5 or 8 with a level 1 product available.
    If there is an error, check earth explorer first. It is frequently down for maitenance.
    In future, there may be a tool included with this package to check if the ID is valid before 
    trying to download. Stay tuned.

TOOLS:
    tools/to_csv.py: used to compile results quickly and easily.
    tools/generate_atmo_figure.py : generate a figure using information from a already processed scene.
    test/functional/run_all_scenes.bash: run a batch of scenes. Move it to this directory before use.

