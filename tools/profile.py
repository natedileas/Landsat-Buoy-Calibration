import cProfile, pstats
import bin.BuoyCalib as bc

def do_buoycalib_things():
    LID = 'LC80130332013145LGN00'
    x = bc.CalCon(LID, verbose=False, reprocess=True)  # initialize
    print str(x)   # sorry, str() necesary for now. calculate and assign
    x.output()    # write out values
    
if __name__ == '__main__':
    cProfile.run('do_buoycalib_things()', 'profileresults')
    p = pstats.Stats('profileresults')
    
    p.sort_stats('cumulative').print_stats(20)
    