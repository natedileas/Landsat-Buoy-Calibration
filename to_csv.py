import bin.BuoyCalib as bc
import sys
import time
import os
import pickle
import csv

scenes = ["LC80130332013145LGN00",
"LC80140332013104LGN01",
"LC80140332013200LGN00",
"LC80140332014299LGN00",
"LC80150402013175LGN00",
"LC80150402013207LGN00",
"LC80150402013239LGN00",
"LC80150402014002LGN00",
"LC80150402014018LGN00",
"LC80150402014114LGN00",
"LC80150402014210LGN00",
"LC80150402014258LGN00",
"LC80150402014290LGN00",
"LC80160382013134LGN03",
"LC80160382013150LGN00",
"LC80160382013166LGN04",
"LC80160382013246LGN00",
"LC80160382013278LGN00",
"LC80160382014089LGN00",
"LC80160382014137LGN00",
"LC80160382014185LGN00",
"LC80160382014233LGN00",
"LC80160382014265LGN00",
"LC80160392013134LGN03",
"LC80160392013198LGN00",
"LC80160392014041LGN00",
"LC80240272013158LGN00",
"LC80240272014225LGN00",
"LC80240402013110LGN01",
"LC80240402013142LGN01",
"LC80240402013158LGN00",
"LC80240402013190LGN00",
"LC80240402013302LGN00",
"LC80240402014017LGN00",
"LC80240402014113LGN00",
"LC80240402014289LGN00",
"LC80410372013101LGN01",
"LC80410372013133LGN01",
"LC80410372013149LGN00",
"LC80410372013181LGN00",
"LC80410372014072LGN00",
"LC80410372014104LGN00",
"LC80410372014136LGN00",
"LC80160302013166LGN04",
"LC80160302013262LGN00",
"LC80160302014153LGN00",
"LC80160302014185LGN00",
"LC80170302013237LGN00",
"LC80170302013285LGN00",
"LC80170302014144LGN00",
"LC80170302014192LGN00",
"LC80170302014272LGN00",
"LC80200292013226LGN00"]

def read_cache(cc):
    """ read in results from the file. """

    out_file = os.path.join(cc.scene_dir, cc.scene_id+'_pickle_narr')

    if not os.path.isfile(out_file):
        print 'No cached data at %s' % out_file
        return

    with open(out_file, 'rb') as f:
        return pickle.load(f)

def to_csv(cc, f):
    """ write results to csv format. """
    
    w = csv.writer(f, quoting=csv.QUOTE_NONE, )
    w.writerow(fmt_items(cc))
    
    
def fmt_items(cc, delim=', '):
    """ helper function for cc.to_csv. """
    
    items = [cc.scene_id]
    
    if cc._buoy_id:
        items.append(str(cc.buoy_location[0]))   # lat
        items.append(str(cc.buoy_location[1]))   # lon
            
    items.append(cc.date.strftime('%m/%d/%Y'))   # year
    items.append(cc.date.strftime('%j'))   # doy
    items.append(cc.wrs2[0:3])   # path
    items.append(cc.wrs2[3:6])   # row
    items.append(' ')   # day/ night
    items.append(cc.buoy_id)   # buoy id
    items.append(' ')   # sca
    items.append(' ')   # detector
    items.append(' ')   # temp difference band 10
    items.append(' ')   # temp difference band 11
    
    if cc.modeled_radiance and cc.image_radiance:
        items.append(str(cc.image_radiance[0]))  # band 10
        items.append(str(cc.modeled_radiance[0]))   # band 10
        items.append(str(cc.image_radiance[1]))   # band 11
        items.append(str(cc.modeled_radiance[1]))   # band 11
        items.append(str(cc.skin_temp))   # buoy (skin) temp

    return items
        

if __name__ == '__main__':
    filename = 'output_narr.csv'
    d = '/dirs/home/ugrad/nid4986/Landsat_Buoy_Calibration/data/scenes/'
    v = True
    
    with open(filename, 'wb') as f:
        start_time = time.time()
        for s in scenes:
            try:
                print s, '%s of %s' % (scenes.index(s) + 1, len(scenes))
                cc = bc.CalibrationController(s, None, d, verbose=v)
                cc_loaded = read_cache(cc)
                to_csv(cc_loaded, f)
            except AttributeError:
                pass
            except KeyboardInterrupt:
                break
