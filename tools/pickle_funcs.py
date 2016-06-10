import pickle
import os

def output_cache(cc):
    """ output results to a pickle serialized file. """

    out_file = os.path.join(cc.scene_dir, cc.scene_id+'_pickle')

    if cc.atmo_src == 'narr':
        out_file += '_narr'
    elif cc.atmo_src == 'merra':
        out_file += '_merra'

    with open(out_file, 'wb') as f:
        pickle.dump(cc, f)


def read_cache(cc):
    """ read in results from a pickle serialized file. """
    try:
        out_file = os.path.join(cc.scene_dir, cc.scene_id+'_pickle')
        if cc.atmo_src == 'narr':
            out_file += '_narr'
        elif cc.atmo_src == 'merra':
            out_file += '_merra'
        
        if not os.path.isfile(out_file):
            raise OSError('pickle_file is not in expected location %s' % outfile) 

        with open(out_file, 'rb') as f:
            x = pickle.load(f)
            __ = x.scene_dir
            return x

    except AttributeError:
        return cc
