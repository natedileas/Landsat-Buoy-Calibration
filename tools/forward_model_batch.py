## Nathan Dileas, RIT, 2018
## probably paths are gonna be annoying
## deal with it, future me
# to fix the pathing issues, run this script from the repository root 
# i.e. Landsat-Buoy-Calibratoion $ python tools/blah.py

# get rid of stupid output
#import warnings
#warnings.filterwarnings("ignore")
import forward_model

# LANDSAT
#  python3 -u tools/forward_model_batch.py > landsat_no_clouds2.out 2>&1 &
scene_txt = "/cis/ugrad/nid4986/repos/Senior_Project/Landsat-Buoy-Calibration/scene_lists/landsat_scenes_no_clouds.txt"
output_txt = 'landsat_no_clouds_results2.txt'
#scene_txt = "/cis/ugrad/nid4986/repos/Senior_Project/Landsat-Buoy-Calibration/scene_lists/landsat_scenes_clouds.txt"
#output_txt = 'landsat_clouds_results.txt'

with open(scene_txt, 'r') as f:
    scenes = f.read().split('\n')
    scenes = [s for s in scenes if s[0:2] != 'LT']

atmo = 'merra'
verbose = False
bands = [10, 11]

with open(output_txt, 'w') as f:
    f.write('# Comma Seperated Values, Nathan Dileas, RIT, 2018\n')
    f.write('Scene_ID, Date, Buoy_ID, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa10, mod11, img_ltoa10, img11\n')
    f.flush()
    for i, scene_id in enumerate(scenes):
        print(scene_id, '[{0}/{1}]'.format(i+1, len(scenes)))
        
        try:
            ret = forward_model.landsat8(scene_id, atmo, verbose, bands)
        except Exception as e:
            print(str(e))
            continue

        for key in ret.keys():
            buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa, date = ret[key]
            print(scene_id, date.strftime('%Y/%m/%d'), buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa[10], mod_ltoa[11], img_ltoa[10], img_ltoa[11], file=f, sep=', ')
        f.flush()
