if __name__=='__main__':
    #run one instance of the program
    import bin.BuoyCalib
    import time
    
    scene_IDs = ['LC80130332013145LGN00', 'LC80150402014114LGN00', \
                 'LC80150402014210LGN00', 'LC80160382014137LGN00', \
                 'LC80160382014185LGN00']
    buoy_IDs = ['44009', '41009', '41009', '41008', '41008']

    start_all = time.time()
    
    for i in range(len(scene_IDs)):
        start_time = time.time()
        cc = bin.BuoyCalib.CalibrationController()
    
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
        
        print 'RUNS: [%s / %s] completed - Time: %s' % (i+1, len(scene_IDs), abs(time.time() - start_time) / 60.0)

    print 'Total time: %s' % (abs(time.time() - start_all) / 60.0)
