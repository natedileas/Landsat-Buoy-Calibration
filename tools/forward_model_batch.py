## Nathan Dileas, RIT, 2018
## probably paths are gonna be annoying
## deal with it, future me

# get rid of stupid output
import warnings
warnings.filterwarnings("ignore")
import forward_model

# read scenes, 1 per line
#scene_txt = 'tools/scenes_modis_initial.txt'
#scene_txt = 'tools/landsat_scenes.txt'
#scene_txt = 'tools/landsat_45012_c30.txt'
# better scene lists

# LANDSAT
scene_txt = "/cis/ugrad/nid4986/repos/Senior_Project/scene_lists/landsat_scenes.txt"

with open(scene_txt, 'r') as f:
    scenes = f.read().split('\n')
    scenes = [s for s in scenes if s[0] != '#']

atmo = 'merra'
verbose = False
bands = [10, 11]

with open('results.txt', 'w') as f:
    f.write('## Space Seperated Values, Nathan Dileas, RIT, 2018\n')
    f.write('Scene_ID, Buoy_ID, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa\n')
    f.flush()
    for i, scene_id in enumerate(scenes):
        print(scene_id, '[{0}/{1}]'.format(i+1, len(scenes)))
        try:
            ret = forward_model.landsat8(scene_id, atmo, verbose, bands)
        except Exception as e:
            print(str(e))
            continue

        for key in ret.keys():
            buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa = ret[key]
            print(args.scene_id, buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, img_ltoa, file=f, sep=', ')
        f.flush()


"""
# MODIS
scene_txt = "/cis/ugrad/nid4986/repos/Senior_Project/scene_lists/modis_scenes.txt"

with open(scene_txt, 'r') as f:
    scenes = f.read().split('\n')
    scenes = [s for s in scenes if s[0] != '#']


atmo = 'merra'
verbose = False
bands = [31, 32]

with open('results.txt', 'w') as f:
    f.write('## Space Seperated Values, Nathan Dileas, RIT, 2018\n')
    f.write('scene_id mod_ltoa_31 mod_ltoa_32 img_ltoa_31 img_ltoa_2 buoy_id skin_temp buoy_lat buoy_lon\n')
    f.flush()
    for i, scene_id in enumerate(scenes):
        print(scene_id, '[{0}/{1}]'.format(i+1, len(scenes)))
        try:
            mod_ltoa, img_ltoa, buoy_id, skin_temp, buoy_lat, buoy_lon = forward_model.modis(scene_id, atmo, verbose, bands)
        except Exception as e:
            print(str(e))
            continue

        print(scene_id, mod_ltoa[10], mod_ltoa[11], img_ltoa[10], img_ltoa[11], buoy_id, skin_temp, buoy_lat, buoy_lon, file=f)
        f.flush()
"""