#!/bin/bash
i=$1

echo $i
echo 'no flags'
python controller.py -scene_id $i -d /dirs/home/ugrad/nid4986/Landsat_Buoy_Calibration/data/scenes/
echo '-ri'
python controller.py -scene_id $i -ri -d /dirs/home/ugrad/nid4986/Landsat_Buoy_Calibration/data/scenes/
echo '-rim'
python controller.py -scene_id $i -rim -d /dirs/home/ugrad/nid4986/Landsat_Buoy_Calibration/data/scenes/

