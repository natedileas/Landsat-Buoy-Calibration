## Nathan Dileas, RIT, 2018
## probably paths are gonna be annoying
## deal with it, future me

# get rid of stupid output
#import warnings
#warnings.filterwarnings("ignore")
import forward_model

# MODIS
# python3 -u tools/forward_model_batch_modis.py > modis_no_clouds.out 2>&1 &
scene_txt = "/cis/ugrad/nid4986/repos/Senior_Project/Landsat-Buoy-Calibration/scene_lists/modis_no_clouds.txt"
output_txt = 'modis_no_clouds_results3.txt'

with open(scene_txt, 'r') as f:
    lines = f.read().split('\n')

scenes = [line.split(' ')[0] for line in lines]
buoys = [line.split(' ')[1:] for line in lines]

#scenes = scenes[28:]
atmo = 'merra'
verbose = False
bands = [31, 32]

with open(output_txt, 'w') as f:
    f.write('# Comma Seperated Values, Nathan Dileas, RIT, 2018\n')
    f.write('# Scene_ID, Date, Buoy_ID, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa31, mod32, img_ltoa31, img32\n')
    f.flush()
    
    for i, scene_id in enumerate(scenes):
        print(scene_id, '[{0}/{1}]'.format(i+1, len(scenes)))
        try:
            ret = forward_model.modis(scene_id, buoys[i], atmo, verbose, bands)
        except Exception as e:
            print('ERROR: ', str(e))
            continue

        print(ret)
        for key in ret.keys():
            buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa, date = ret[key]

            print(scene_id, date.strftime('%Y/%m/%d'), buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa[31], mod_ltoa[32], img_ltoa[0][31], img_ltoa[0][32], file=f, sep=', ')

        f.flush()
