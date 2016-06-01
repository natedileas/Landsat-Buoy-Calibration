import pickle
import os

def output(cc):
    """ output results to a file. """

    out_file = os.path.join(cc.scene_dir, cc.scene_id+'_pickle')

    with open(out_file, 'wb') as f:
        pickle.dump(cc, f)


def read_cache(cc):
    """ read in results from the file. """
    try:
        out_file = os.path.join(cc.scene_dir, cc.scene_id+'_pickle')
    except AttributeError:
        return cc
        
    if not os.path.isfile(out_file):
        return cc

    with open(out_file, 'rb') as f:
        return pickle.load(f)


if __name__=='__main__':
    import argparse
    import bin.BuoyCalib as bc
    import bin.image_processing as img_proc

    parser = argparse.ArgumentParser(description='Compute and compare the radiance values of \
     a landsat image to the radiance of a NOAA buoy. ')
    
    #ids
    parser.add_argument('-scene_id', help='LANDSAT scene ID. Example: LC80330412013145LGN00')
    parser.add_argument('-buoy_id', help='NOAA Buoy ID. Example: 44009')
    
    #piece
    parser.add_argument('-satelite', help="LANDSAT version (Options: 8 OR 7)",choices=[7,8])
    parser.add_argument('-WRS2', help="WRS2 coordinates of landsat scene: (Ex. 032041)")
    parser.add_argument('-date', help="Date (Year, Day of Year):   YYYYDDD")
    parser.add_argument('-station', help="Processing Station; ", default='LGN')
    parser.add_argument('-ver', '--version', help="version of landsat image ex: 00, 01 ... ,04", choices=['01', '02', '03', '04', '05'], default='00')
    
    #true optionals
    parser.add_argument('-c', '--cloud' , help="Maximum desired cloud coverage in percent", type=int, default=100)
    parser.add_argument('-v', '--verbose', help="Verbose: Specify to see command line output. Otherwise, view it in ./logs", action='store_true', default=False)
    parser.add_argument('-r', '--reprocess', help="Add to explicitly reprocess. Otherwise, a previous calculated version will be outputted.", action='store_true', default=False)
    parser.add_argument('-d', '--directory', help="Directory to search for landsat images.", default='./data/scenes/')
    parser.add_argument('-i','--image', help="draw NARR points and Buoy location on landsat image.", action='store_true')
    parser.add_argument('-o','--No_output', help="Serialize class, happens by default.", action='store_false', default=True)
    parser.add_argument('-m','--merra', help='Use MERRA-2 Data instead of NARR Data.', action='store_true', default=False)
    parser.add_argument('-n', '--narr', help='Use NARR Atmospheric Data.', action='store_false', default=True)

    args = parser.parse_args()
    
    # assemble id
    LID = None
    if args.scene_id:
        LID = args.scene_id
    else:
        sat = {7:'LE7', 8:'LC8'}
        LID = '%3s%6s%7s%3s%2s' % (sat[args.satelite], args.WRS2, args.date, args.station, args.version)
    
    atmo_data_src='narr'
    if args.merra:
        atmo_data_src='merra'
 
    x = bc.CalibrationController(LID, args.buoy_id, args.directory, verbose=args.verbose, atmo_src=atmo_data_src)  # initialize

    if not args.reprocess:
        x = read_cache(x)   # try to read in from pickle
    else:
        x.calc_all()

    print x   # show values on screen
    
    if args.output:
        output(x)    # write out values to pickle

    if args.image:
        img_proc.write_im(x)
        print 'Image with NARR points and buoy written to %s' % (x.scene_dir + '/' + x.scene_id + '_mod.jpg')

