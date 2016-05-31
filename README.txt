Calculates and compares the radiance of a thermal LANSAT scene to the actual
radiance as measured by a NBDC buoy. Based on work by Frank Padula and Monica Cook.

Developed on Fedora x64. 

Proper Use:
Command Line: controller.py, in this directory.

You can also provide a single ID via the command line like so:
python controller.py ids -scene LC80130332013145LGN00 -buoy 44009

Or provide individual pieces of a single id like this:
python controller.py piece -sat 8 -WRS2 013033 -date 2013145 -buoy 44009

Output can be found in ./data/scenes/YOUR_SCENE_HERE
     
If you would like to use your own landsat images, provide the directory by using the -d option.

to_csv.py is a tool used to compile results quickly and easily.

Developed by Nathan Dileas, RIT 2015
