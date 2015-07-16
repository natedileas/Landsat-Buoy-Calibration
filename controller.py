if __name__=='__main__':
    import argparse
    import bin.BuoyCalib
    import time
    import sys
    
    try:
        if len(sys.argv) == 1:
            sys.exit()
    
        parser = argparse.ArgumentParser(description='Compute and compare the radiance values of \
         a landsat image to the radiance of a NOAA buoy. ')
        
        parser.add_argument('input', help='Choose one of the options. "ids" \
        indicates you will provide landsat and buoy ids in this file. "file" indicates you \
        will provide a file containing a list of ids.to all be processed. \
        "piece" indicates you will provide the options -satelite, -WRS2, and -date.\
        ', choices = ['ids','file','piece'])
        
        #file
        parser.add_argument('--file', help="file path to list of ids and buoy ids. Format in README")
        
        #ids
        parser.add_argument('-scene_id', help='LANDSAT scene ID. Example: LC80330412013145LGN00')
        parser.add_argument('-buoy_id', help='NOAA Buoy ID. Example: 44009')
        
        #piece
        parser.add_argument('-satelite', help="LANDSAT version (Options: 8 OR 7)",choices=[7,8], type=int)
        parser.add_argument('-WRS2', help="WRS2 coordinates of landsat scene: (Ex. 032041)")
        parser.add_argument('-date', help="Date (Year, Day of Year):   YYYYDDD")
        
        #true optionals
        parser.add_argument('-c', '--cloud' , help="Maximum desired cloud coverage in percent", type=int, default=100)
        parser.add_argument('-v', '--verbose', help="Verbose: Specify to see command line output. Otherwise, view it in ./logs", action='store_true')
    
        args = parser.parse_args()
        
        scene_IDs = []
        buoy_IDs = []
    
        if args.input == 'file':
            # read from file #TODO decide standard file
            filename = args.f
            with open(filename, 'r') as f:
                for line in f:
                    pass
                    # do something w/ line
            
            scene_IDs = []   #TODO assign from file
            buoy_IDs = []
                
            #start runs
            for i in range(len(scene_IDs)):
                cc = bin.BuoyCalib.CalibrationController()
                
                #optionals
                if args.cloud:
                    cc.cloud_cover = args.cloud
                if args.verbose:
                    cc.verbose = args.verbose
                    
                cc.scene_id = scene_IDs[i]
                cc.buoy_id = buoy_IDs[i]
            
                __=cc.download_img_data()
                __=cc.calculate_buoy_information()
                __=cc.calc_img_radiance()
                
                __=cc.download_mod_data()
                __=cc.calc_mod_radiance()
                __=cc.calc_brightness_temperature()
                
                __=cc.cleanup(True)
                __=cc.output()
        else:
            cc = bin.BuoyCalib.CalibrationController()
            
            if args.input == 'ids':
                cc.scene_id = args.scene_id
                
            elif args.input == 'piece':
                cc.satelite = args.satelite
                cc.WRS2_path = args.WRS2[0:3]
                cc.WRS2_row = args.WRS2[3:6]
                cc.year = args.date[0:4]
                cc.julian_date = args.date[4:7]
    
            #optionals
            if args.cloud:
                cc.cloud_cover = args.cloud
            if args.verbose:
                cc.verbose = args.verbose
            if args.buoy_id:
                cc.buoy_id = args.buoy_id
        
            __=cc.download_img_data()
            __=cc.calculate_buoy_information()
            __=cc.calc_img_radiance()
            
            __=cc.download_mod_data()
            __=cc.calc_mod_radiance()
            __=cc.calc_brightness_temperature()
            
            __=cc.cleanup(True)
            __=cc.output()
    except KeyboardInterrupt:
        __cc.cleanup(True)