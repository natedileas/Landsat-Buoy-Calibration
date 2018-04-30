## Nathan Dileas, RIT, 2018
## probably paths are gonna be annoying
## deal with it, future me
# to fix the pathing issues, run this script from the repository root 
# i.e. Landsat-Buoy-Calibration $ python tools/blah.py
import forward_model


def batch_forward_model(scenes, output_txt, atmo='merra', verbose=False):

    with open(output_txt, 'w') as f:
        f.write('# Comma Seperated Values, Nathan Dileas, RIT, 2018\n')
        f.write('Scene_ID, Date, Buoy_ID, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod1, mod2, img1, img2, error1, error2\n')
        f.flush()

        for i, scene_id in enumerate(scenes):
            print(scene_id, '[{0}/{1}]'.format(i+1, len(scenes)))
            
            try:
                if scene_id[0:3] in ('LC8', 'LC0'):   # Landsat 8
                    ret = forward_model.landsat8(scene_id, atmo)

                elif scene_id[0:3] == 'MOD':   # Modis
                    ret = forward_model.modis(scene_id, atmo)

            except Exception as e:
                print('ERROR: ', str(e))
                continue

            print(ret)

            for key in ret.keys():
                buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, mod_ltoa, error, img_ltoa, date = ret[key]
                print(scene_id, date.strftime('%Y/%m/%d'), buoy_id, bulk_temp, skin_temp, buoy_lat, buoy_lon, \
                    *mod_ltoa.values(), *img_ltoa.values(), *error.values(), file=f, sep=', ')
            
            f.flush()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('scene_txt')
    parser.add_argument('-a', '--atmo', default='merra', choices=['merra', 'narr'], help='Choose atmospheric data source, choices:[narr, merra].')
    parser.add_argument('-s', '--save', default='results.txt')

    args = parser.parse_args()

    with open(args.scene_txt, 'r') as f:
        scenes = f.read().split('\n')
        #scenes = [s for s in scenes]
        scenes = list(set(scenes))

    batch_forward_model(scenes, args.save, args.atmo)
