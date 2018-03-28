## Nathan Dileas, RIT, 2018
## probably paths are gonna be annoying
## deal with it, future me

# get rid of stupid output
import warnings
import random
warnings.filterwarnings("ignore")
import forward_model

# read scenes, 1 per line 
scene_txt = 'tools/scenes_modis_initial.txt'
scene_txt = 'tools/landsat_scenes.txt'
scene_txt = 'tools/landsat_45012_c30.txt'

with open(scene_txt, 'r') as f:
	scenes = f.read().split('\n')
	scenes = [s for s in scenes if s[0] != '#']

buoy_id = '45012'
atmo = 'merra'
verbose = False
bands = [10, 11]


#random.seed('2010')
#random.sample(scenes, 30)

with open('results.txt', 'w') as f:
	f.write('## Space Seperated Values, Nathan Dileas, RIT, 2018\n')
	f.write('scene_id mod_ltoa_31 mod_ltoa_32 img_ltoa_31 img_ltoa_2 buoy_id skin_temp buoy_lat buoy_lon\n')
	f.flush()
	for scene_id in scenes:
		print(scene_id)
		try:
			mod_ltoa, img_ltoa, buoy_id, skin_temp, buoy_lat, buoy_lon = forward_model.landsat8(scene_id, buoy_id, atmo, verbose, bands)
		except forward_model.buoy.BuoyDataException:
			print('Skiippped because of buoy')
			continue

		print(scene_id, mod_ltoa[10], mod_ltoa[11], img_ltoa[10], img_ltoa[11], buoy_id, skin_temp, buoy_lat, buoy_lon, file=f)
		f.flush()