#!/bin/bash

directory=./data/shared/modtran

home=$1
tape5_dir=$2

#  for each case in caseList: 
#  run modtran on generated tape5 files
#  run tape6parser to delete headers and parse wavelength
#  and total radiance from tape6 file

chmod 755 $tape5_dir
chmod 777 ./bin/tape6parser.bash

pushd $tape5_dir >/dev/null 2>/dev/null
ln -s /dirs/pkg/Mod4v3r1/DATA  >/dev/null 2>/dev/null
/dirs/pkg/Mod4v3r1/Mod4v3r1.exe >/dev/null 2>/dev/null
popd >/dev/null 2>/dev/null
