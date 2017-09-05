import cProfile, pstats
import os, sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import bin.BuoyCalib as bc

def do_buoycalib_things():
    LID = 'LC80130332013145LGN00'
    x = bc.CalibrationController(LID, None, '/dirs/home/ugrad/nid4986/Landsat_Buoy_Calibration/data/scenes',verbose=False)  # initialize
    x.calc_all()
    print str(x)   # sorry, str() necesary for now. calculate and assign
    
if __name__ == '__main__':
    cProfile.run('do_buoycalib_things()', 'profileresults')
    p = pstats.Stats('profileresults')
    
    p.sort_stats('cumulative').print_stats(50)
    
