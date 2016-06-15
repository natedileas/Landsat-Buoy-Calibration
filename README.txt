Calculates and compares the radiance of a thermal LANSAT scene to the "ground truth"
radiance as measured by a NBDC buoy. Based on work by Frank Padula and Monica Cook.

This code essentially has two funtions: calculating the radiance from the landsat image 
provided, and calculating the corresponding ground truth radiance from outside data,
atmospheric (NARR or MERRA-2), and NOAA buoy data.

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

Developed on Fedora x64 by Nathan Dileas. RIT 2015-2016

Usage: controller.py, in this directory.

python controller.py [options] <Landsat_ID>




to_csv.py is a tool used to compile results quickly and easily.