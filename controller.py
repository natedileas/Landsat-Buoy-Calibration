import bin.BuoyCalib as bc
import tools.pickle_funcs as pickle
import os

if __name__=='__main__':
    import argparse
    import bin.image_processing as img_proc

    parser = argparse.ArgumentParser(description='Compute and compare the radiance values of \
     a landsat image to the propogated radiance of a NOAA buoy, using NARR data and MODTRAN. \
     Works with landsat 5, 7, and 8. \nIf atmospheric data or landsat images need to be downloaded,\
     it will take between 5-7 minutes for NARR, and 2-3 for MERRA. If nothing need to be downloaded,\
     it will usually take less than 2 minutes for a single scene.')
    
    parser.add_argument('scene_id', help='LANDSAT scene ID. Examples: LC80330412013145LGN00, LE70160382012348EDC00, LT50410372011144PAC01')
    
    parser.add_argument('-b','--buoy_id', help='NOAA Buoy ID. Example: 44009',default=None)
    parser.add_argument('-i','--image', help="draw NARR points and Buoy location on landsat image.", action='store_true', default=False)
    parser.add_argument('-o','--Nooutput', help="Don't serialize, useful for testing.", action='store_true', default=False)
    parser.add_argument('-m','--merra', help='Use MERRA-2 Data instead of NARR Data.', action='store_true', default=False)
    parser.add_argument('-v', '--verbose', help="Verbose: Specify to see command line output.", action='store_true', default=False)
    parser.add_argument('-r', '--reprocess', help="Add to explicitly reprocess.", action='store_true', default=False)
    #parser.add_argument('-n', '--narr', help='Use NARR Atmospheric Data.', action='store_false', default=True)
    #parser.add_argument('-d', '--directory', help="Directory to search for landsat images.", default='')
    #parser.add_argument('-c', '--cloud' , help="Maximum desired cloud coverage in percent", type=int, default=100)

    args = parser.parse_args()
    
    # assemble id
    LID = args.scene_id
    
    atmo_data_src='narr'
    if args.merra:
        atmo_data_src='merra'
 
    cc = bc.CalibrationController(LID, BID=args.buoy_id, verbose=args.verbose, atmo_src=atmo_data_src)  # initialize

    if args.reprocess:
        cc.calc_all()
    else:
        try:
            cc = pickle.read_cache(cc)   # try to read in from pickle
        except OSError:
            cc.calc_all()
        except AttributeError:
            cc.calc_all()

    print cc   # show values on screen

    if args.Nooutput is False:
        pickle.output_cache(cc)    # write out values to pickle

    if args.image:
        if cc.satelite == 'LC8':
            img_file = os.path.join(cc.scene_dir, cc.metadata['FILE_NAME_BAND_10'])
        elif cc.satelite == 'LE7':
            img_file = os.path.join(cc.scene_dir, cc.metadata['FILE_NAME_BAND_6_VCID_2'])
        elif cc.satelite == 'LT5':
            img_file = os.path.join(cc.scene_dir, cc.metadata['FILE_NAME_BAND_6'])

        img_proc.write_im(cc, img_file)
        
        save_path = os.path.join(cc.scene_dir, 'output', cc.scene_id+'_mod')
        if cc.atmo_src == 'narr':
            save_path += '_narr.png'
        elif cc.atmo_src == 'merra':
            save_path += '_merra.png'
        print 'Image with NARR points and buoy written to %s' % save_path
