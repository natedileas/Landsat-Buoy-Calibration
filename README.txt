RIT 2015

Calculates and compares the radiance of a thermal LANSAT scene to the actual
radiance as measured by a NBDC buoy. Based on work by Frank Padula and Monica Cook.

Developed on Fedora x64. 

Use:
Command Line: controller.py, in this directory. 
Easiest Usage is via the list method, provided by editing the id_list.py file and then calling: 
python controller.py list

You can also provide a single ID via the command line like so:
python controller.py ids -scene LC80130332013145LGN00 -buoy 44009

Or provide individual pieces of a single id like this:
python controller.py piece -sat 8 -WRS2 013033 -date 2013145 -buoy 44009

Output can be found in ./logs/output.txt
     
Notes:
Log information can be found in ./logs/calibrationController.log, ./logs/modtran.log

Developed by Nathan Dileas
Bugs: nid4986@rit.edu, subject line: "Landsat Vic. Calib. Bug"
