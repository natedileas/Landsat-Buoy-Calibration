if __name__=='__main__':
    import argparse
    import bin.BuoyCalib as bc
    import cProfile
    import re

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
    parser.add_argument('-r', '--reprocess', help="Verbose: Specify to reprocess Otherwise, a previous calculated version will be outputted.", action='store_true', default=False)

    args = parser.parse_args()
    
    # assemble id
    LID = None
    if args.scene_id:
        LID = args.scene_id
    else:
        sat = {7:'LE7', 8:'LC8'}
        LID = '%3s%6s%7s%3s%2s' % (sat[args.satelite], args.WRS2, args.date, args.station, args.version)
        
    x = bc.CalCon(LID, verbose=args.verbose, reprocess=args.reprocess)  # initialize
    print str(x)   # sorry, str() necesary for now. calculate and assign
    x.output()    # write out values