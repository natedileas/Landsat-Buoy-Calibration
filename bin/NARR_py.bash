#!/bin/bash
#NARR_py.bash

home=`pwd`
imageBase=$1
verbose=$2

#  define Landsat metadata file
metaFile=$home/data/scenes/$imageBase/$imageBase'_MTL.txt'

narr=$home/data/shared/narr
grib=$home/data/shared/narr/GRIB

scene_dir=$home/data/scenes/$imageBase/narr

if [ ! -d  $scene_dir ]; then
mkdir $scene_dir
fi

cat $metaFile | grep -a = | sed s/\ =\ /=/g > ./data/scenes/${imageBase}/${imageBase}'_meta.txt'
source ./data/scenes/${imageBase}/${imageBase}'_meta.txt'

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
cat $narr/script_HGT_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour1'/' > $scene_dir/$fileHGT1
cat $narr/script_HGT_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour2'/' > $scene_dir/$fileHGT2

#  define files for scripts to obtain NARR GRIB files containing the specific humidity variable
fileSHUM1='script_SHUM_'$hour1
fileSHUM2='script_SHUM_'$hour2

#  modify generic scripts with acquisition dates and hours to obtain NARR GRIB files containing the specific humidity variable
cat $narr/script_SHUM_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour1'/' > $scene_dir/$fileSHUM1
cat $narr/script_SHUM_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour2'/' > $scene_dir/$fileSHUM2

#  define files for scripts to obtain NARR GRIB files containing the temperature variable
fileTMP1='script_TMP_'$hour1
fileTMP2='script_TMP_'$hour2

#  modify generic scripts with acquisition dates and hours to obtain NARR GRIB files containing the temperature variable
cat $narr/script_TMP_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour1'/' > $scene_dir/$fileTMP1
cat $narr/script_TMP_generic | sed 's/year/'$year'/' | sed 's/mo/'$month'/' | sed 's/dy/'$day'/' | sed 's/rh/'$hour2'/' > $scene_dir/$fileTMP2

#  change permissions on script files
chmod 755 $scene_dir/$fileHGT1
chmod 755 $scene_dir/$fileTMP1
chmod 755 $scene_dir/$fileSHUM1

chmod 755 $grib/get_inv.pl 
chmod 755 $grib/get_grib.pl
chmod 755 $grib/HGT_grb2txt
chmod 755 $grib/SHUM_grb2txt
chmod 755 $grib/TMP_grb2txt
chmod 755 $grib/a.out

#  copy script files for time one to appropriate GRIB directory
mv $scene_dir/$fileHGT1 $grib/script_HGT
mv $scene_dir/$fileTMP1 $grib/script_TMP
mv $scene_dir/$fileSHUM1 $grib/script_SHUM

#  change to appropriate GRIB directory and run scripts
cd $grib

./script_HGT >/dev/null 2>>$scene_dir/log.txt
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [1 / 12] \r'; fi

#check if 'missing wgrib inventory' is in log file
if grep -q "missing wgrib inventory" $scene_dir/log.txt; then
    exit 1
fi

./script_SHUM >/dev/null 2>>$scene_dir/log.txt
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [2 / 12] \r'; fi
./script_TMP >/dev/null 2>>$scene_dir/log.txt
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [3 / 12] \r'; fi
./HGT_grb2txt >/dev/null 2>/dev/null
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [4 / 12] \r'; fi
./SHUM_grb2txt >/dev/null 2>/dev/null
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [5 / 12] \r'; fi
./TMP_grb2txt >/dev/null 2>/dev/null
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [6 / 12] \r'; fi

#  change back to home directory
cd $home

# make directories to contain results for this specific landsat image
if [ ! -d  $scene_dir/HGT_1 ]; then
    mkdir $scene_dir/HGT_1
    mkdir $scene_dir/TMP_1
    mkdir $scene_dir/SHUM_1
fi

# 'move results from GRIB directory to directory for this specific Landsat image'
if [ -d  $scene_dir/HGT_1 ]; then
    mv $grib/HGT/* $scene_dir/HGT_1
    mv $grib/TMP/* $scene_dir/TMP_1
    mv $grib/SHUM/* $scene_dir/SHUM_1
fi

#  change permissions on script files
chmod 755 $scene_dir/$fileHGT2
chmod 755 $scene_dir/$fileTMP2
chmod 755 $scene_dir/$fileSHUM2

#  copy script files for time after to appropriate GRIB directory
mv $scene_dir/$fileHGT2 $grib/script_HGT
mv $scene_dir/$fileTMP2 $grib/script_TMP
mv $scene_dir/$fileSHUM2 $grib/script_SHUM

#  change to appropriate GRIB directory and run scripts
cd $grib
./script_HGT >/dev/null 2>>$scene_dir/log.txt
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [7 / 12] \r'; fi
./script_SHUM >/dev/null 2>>$scene_dir/log.txt
if [ ${verbose} -gt -1 ]; then echo -ne '        DOWNLOADING NARR DATA: [8 / 12] \r'; fi
./script_TMP >/dev/null 2>>$scene_dir/log.txt
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
if [ ! -d $scene_dir/HGT_2 ]; then
mkdir $scene_dir/HGT_2
mkdir $scene_dir/TMP_2
mkdir $scene_dir/SHUM_2
fi

#  move results from GRIB directory to directory for this specific Landsat image
mv $grib/HGT/* $scene_dir/HGT_2
mv $grib/TMP/* $scene_dir/TMP_2
mv $grib/SHUM/* $scene_dir/SHUM_2

rm ./data/scenes/${imageBase}/${imageBase}'_meta.txt'

if [ ${verbose} -gt -1 ]; then echo -ne '\n'; fi