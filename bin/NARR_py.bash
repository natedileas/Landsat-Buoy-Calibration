#!/bin/bash 

#NARR_py.bash

home=`pwd`
imageBase=$1
verbose=$2

#  define Landsat metadata file
metaFile=$home/data/landsat/$imageBase/$imageBase'_MTL.txt'

destination=$home/data/narr
grib_dest=$home/data/narr/GRIB

cat $metaFile | grep -a = | sed s/\ =\ /=/g > ./data/landsat/${imageBase}/${imageBase}'_meta.txt'
source ./data/landsat/${imageBase}/${imageBase}'_meta.txt'

#  parse date and hour of acquisition from Landsat metadata
year=`echo ${DATE_ACQUIRED} | awk -F'-' '{print $1}'`
month=`echo ${DATE_ACQUIRED} | awk -F'-' '{print $2}'`
day=`echo ${DATE_ACQUIRED} | awk -F'-' '{print $3}'` 
hour=`echo ${SCENE_CENTER_TIME} | awk -F':' '{print $1}'`

if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [0 / 12] \r'; fi


#  determine three hour increment before and after acquisition time
rem1=$(($hour % 3))
rem2=$((3 - $rem1))
hour1=$(($hour - $rem1))
hour2=$(($hour + $rem2))
if [ ${hour1} -lt 10 ]
then
	hour1=0${hour1}
fi
if [ ${hour2} -lt 10 ]
then
	hour2=0${hour2}
fi

#  define variables for scripts to obtain NARR GRIB files
yearmo=$year$month
date=$year$month$day

#  define files for scripts to obtain NARR GRIB files containing the geopotential height variable
fileHGT1='script_HGT_'$hour1
fileHGT2='script_HGT_'$hour2

#  modify generic scripts with acquisition dates and hours to obtain NARR GRIB files containing the geopotential height variable
cat $destination/script_HGT_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour1'/' > $destination/$fileHGT1
cat $destination/script_HGT_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour2'/' > $destination/$fileHGT2

#  define files for scripts to obtain NARR GRIB files containing the specific humidity variable
fileSHUM1='script_SHUM_'$hour1
fileSHUM2='script_SHUM_'$hour2

#  modify generic scripts with acquisition dates and hours to obtain NARR GRIB files containing the specific humidity variable
cat $destination/script_SHUM_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour1'/' > $destination/$fileSHUM1
cat $destination/script_SHUM_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour2'/' > $destination/$fileSHUM2

#  define files for scripts to obtain NARR GRIB files containing the temperature variable
fileTMP1='script_TMP_'$hour1
fileTMP2='script_TMP_'$hour2

#  modify generic scripts with acquisition dates and hours to obtain NARR GRIB files containing the temperature variable
cat $destination/script_TMP_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour1'/' > $destination/$fileTMP1
cat $destination/script_TMP_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour2'/' > $destination/$fileTMP2

if [ ! $grib_dest ]; then
mkdir $grib_dest
fi

#  change permissions on script files
chmod 755 $destination/$fileHGT1
chmod 755 $destination/$fileTMP1
chmod 755 $destination/$fileSHUM1
chmod 755 $grib_dest/get_inv.pl 
chmod 755 $grib_dest/get_grib.pl
chmod 755 $grib_dest/HGT_grb2txt
chmod 755 $grib_dest/SHUM_grb2txt
chmod 755 $grib_dest/TMP_grb2txt
chmod 755 $grib_dest/a.out

#  copy script files for time before to appropriate GRIB directory
mv $destination/$fileHGT1 $grib_dest/script_HGT
mv $destination/$fileTMP1 $grib_dest/script_TMP
mv $destination/$fileSHUM1 $grib_dest/script_SHUM

#  change to appropriate GRIB directory and run scripts
cd $grib_dest

./script_HGT >/dev/null 2>>$home/logs/CalibrationController.log
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [1 / 12] \r'; fi
./script_SHUM >/dev/null 2>>$home/logs/CalibrationController.log
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [2 / 12] \r'; fi
./script_TMP >/dev/null 2>>$home/logs/CalibrationController.log
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [3 / 12] \r'; fi
./HGT_grb2txt >/dev/null 2>/dev/null
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [4 / 12] \r'; fi
./SHUM_grb2txt >/dev/null 2>/dev/null
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [5 / 12] \r'; fi
./TMP_grb2txt >/dev/null 2>/dev/null
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [6 / 12] \r'; fi

#  change back to home directory
cd $destination

# make directories to contain results for this specific landsat image
if [ ! -d  $destination/HGT_1 ]; then
mkdir $destination/HGT_1
mkdir $destination/TMP_1
mkdir $destination/SHUM_1
fi


# 'move results from GRIB directory to directory for this specific Landsat image'
mv $grib_dest/HGT/* $destination/HGT_1
mv $grib_dest/TMP/* $destination/TMP_1
mv $grib_dest/SHUM/* $destination/SHUM_1

#  change permissions on script files
chmod 755 $destination/$fileHGT2
chmod 755 $destination/$fileTMP2
chmod 755 $destination/$fileSHUM2

#  copy script files for time after to appropriate GRIB directory
mv $destination/$fileHGT2 $grib_dest/script_HGT
mv $destination/$fileTMP2 $grib_dest/script_TMP
mv $destination/$fileSHUM2 $grib_dest/script_SHUM

#  change to appropriate GRIB directory and run scripts
cd $grib_dest
./script_HGT >/dev/null 2>>$home/logs/CalibrationController.log
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [7 / 12] \r'; fi
./script_SHUM >/dev/null 2>>$home/logs/CalibrationController.log
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [8 / 12] \r'; fi
./script_TMP >/dev/null 2>>$home/logs/CalibrationController.log
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [9 / 12] \r'; fi
./HGT_grb2txt >/dev/null 2>/dev/null
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [10 / 12] \r'; fi
./SHUM_grb2txt >/dev/null 2>/dev/null
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [11 / 12] \r'; fi
./TMP_grb2txt >/dev/null 2>/dev/null
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [12 / 12] \r'; fi

#  change back to home directory
cd $home

# make directories to contain results for this specific landsat image
if [ ! -d $destination/HGT_2 ]; then
mkdir $destination/HGT_2
mkdir $destination/TMP_2
mkdir $destination/SHUM_2
fi

#  move results from GRIB directory to directory for this specific Landsat image
mv $grib_dest/HGT/* $destination/HGT_2
mv $grib_dest/TMP/* $destination/TMP_2
mv $grib_dest/SHUM/* $destination/SHUM_2

if [ ${verbose} -gt -1 ]; then echo -ne '\n'; fi
