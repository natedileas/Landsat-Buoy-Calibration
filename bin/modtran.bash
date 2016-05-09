#!/bin/bash

directory=./data/shared/modtran

home=`pwd`
verbose=$1
tape5_dir=$2
log=$dir2/modtran.log

#  for each case in caseList: 
#  run modtran on generated tape5 files
#  run tape6parser to delete headers and parse wavelength
#  and total radiance from tape6 file

chmod 755 $cseLst
chmod 777 ./bin/tape6parser.bash

if [ ${verbose} -eq 1 ]; then echo -ne 'MODTRAN RUNNING\n'; fi
pushd $tape5_dir >>$log 2>>$log
ln -s /dirs/pkg/Mod4v3r1/DATA >>$log 2>>$log
/dirs/pkg/Mod4v3r1/Mod4v3r1.exe >>$log 2>>$log
popd >>$log 2>>$log

ln -fs $home/$directory/elim2.sed "${tape5_dir}"
./bin/tape6parser.bash ${case} >>$log 2>>$log
