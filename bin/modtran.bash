#!/bin/bash

directory=./data/shared/modtran
log=./logs/modtran.log

home=`pwd`
verbose=$1
dir2=$2
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
  pushd $case >>$home/$log 2>>$home/$log
  ln -s /dirs/pkg/Mod4v3r1/DATA >>$home/$log 2>>$home/$log
  /dirs/pkg/Mod4v3r1/Mod4v3r1.exe >>$home/$log 2>>$home/$log
  popd >>$home/$log 2>>$home/$log
  
	#Create link
	ln -f $home/$directory/elim2.sed "${case}"
 
   echo $case >>$home/$log 2>>$home/$log
	./bin/tape6parser.bash ${case} >>$home/$log 2>>$home/$log
 
  if [ ${verbose} -gt -1 ]; then echo -ne '\tMODTRAN RUNS ['$a' / 4] \r'; fi
done

if [ ${verbose} -gt -1 ]; then echo -ne '\tMODTRAN RUNS [4 / 4]\r\n'; fi
