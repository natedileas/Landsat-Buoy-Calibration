import sys
import time
import os
from os import path
import csv

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import bin.BuoyCalib as bc

import pickle_funcs
from scenes import all as scenes

def fmt_items(cc):
    """ organize elements for csv row. """
    # Each Item in items is a column in the resultant csv file
    # cc: calibration_controller object
    
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
    filename = 'output_merra.csv'
    
    # options
    a = 'merra'   # atmo data src
    v = False   # verbose
    
    with open(filename, 'wb') as f:
        w = csv.writer(f, quoting=csv.QUOTE_NONE)
        
        for s in scenes:
            try:
                #print s, '%s of %s' % (scenes.index(s) + 1, len(scenes))
                cc = bc.CalibrationController(s, verbose=v, atmo_src=a)
                cc_loaded = pickle_funcs.read_cache(cc)
                w.writerow(fmt_items(cc_loaded))
            except AttributeError:
                w.writerow([s])
            except KeyboardInterrupt:
                break
            except OSError:
                w.writerow([s])