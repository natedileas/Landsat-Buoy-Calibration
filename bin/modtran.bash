#!/bin/bash

directory=./data/modtran

home=`pwd`
verbose=$1
a=0

echo 'MODTRAN runs' > ./logs/modtran.log

#  for each case in caseList: 
#  run modtran on generated tape5 files
#  run tape6parser to delete headers and parse wavelength
#  and total radiance from tape6 file

#define and change permissions on files
cseLst=${directory}/caseList

chmod 755 $cseLst
chmod 777 ./bin/tape6parser.bash

for case in `cat $cseLst`
do
  a=$((a + 1))
  #perform modtran run
  pushd $case >>$home/logs/modtran.log 2>>$home/logs/modtran.log
  ln -s /dirs/pkg/Mod4v3r1/DATA >>$home/logs/modtran.log 2>>$home/logs/modtran.log
  /dirs/pkg/Mod4v3r1/Mod4v3r1.exe >>$home/logs/modtran.log 2>>$home/logs/modtran.log
  popd >>$home/logs/modtran.log 2>>$home/logs/modtran.log
  
	#Create link.  If create fails, loop and sleep until successful
	ln $home/data/modtran/elim2.sed "${case}" || while [ ! -e "${case}/elim2.sed" ] ; do logger "LINK CREATE FAILED, case=${case} pwd=`pwd`" ; sleep 5 ; ln $home/data/elim2.sed "${case}" ; done >>$home/logs/modtran.log 2>>$home/logs/modtran.log
 
   echo $case >>$home/logs/modtran.log 2>>$home/logs/modtran.log
	./bin/tape6parser.bash ${case} >>$home/logs/modtran.log 2>>$home/logs/modtran.log
 
  if [ ${verbose} -gt -1 ]; then echo -ne '\tMODTRAN RUNS ['$a' / 4] \r'; fi
done

if [ ${verbose} -gt -1 ]; then echo -ne '\tMODTRAN RUNS [4 / 4]\r\n'; fi
