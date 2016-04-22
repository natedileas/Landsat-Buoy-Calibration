#!/bin/bash

directory=./data/shared/modtran

home=`pwd`
verbose=$1
dir2=$2
log=$dir2/modtran.log
a=0

echo 'MODTRAN runs' > $log

#  for each case in caseList: 
#  run modtran on generated tape5 files
#  run tape6parser to delete headers and parse wavelength
#  and total radiance from tape6 file

#define and change permissions on files
cseLst=${dir2}/caseList

chmod 755 $cseLst
chmod 777 ./bin/tape6parser.bash

for case in `cat $cseLst`
do
  a=$((a + 1))
  #perform modtran run
  pushd $case >>$log 2>>$log
  ln -s /dirs/pkg/Mod4v3r1/DATA >>$log 2>>$log
  /dirs/pkg/Mod4v3r1/Mod4v3r1.exe >>$log 2>>$log
  popd >>$log 2>>$log
  
	#Create link
	ln -fs $home/$directory/elim2.sed "${case}"
 
   echo $case >>$log 2>>$log
	./bin/tape6parser.bash ${case} >>$log 2>>$log
 
  if [ ${verbose} -eq 1 ]; then echo -ne '\tMODTRAN RUNS ['$a' / 4] \r'; fi
done

if [ ${verbose} -eq 1 ]; then echo -ne '\tMODTRAN RUNS [4 / 4]\r\n'; fi
