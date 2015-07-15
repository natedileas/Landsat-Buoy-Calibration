RIT 2015

Calculates and compares the radiance of a thermal LANSAT scene to the actual
radiance as measured by a NBDC buoy. Based on work by Frank Padula and Monica LastName?

Developed on Fedora x64. 

Use:
Python script, in this directory.

Minimum Necesary:
if __name__=='__main__':
    import bin.BuoyCalib

    cc = bin.BuoyCalib.CalibrationController()
    
    cc.scene_id = 'LC80130332013145LGN00'
    cc.buoy_id = '44009'
    
    __=cc.download_img_data()
    __=cc.calculate_buoy_information()
    __=cc.calc_img_radiance()
        
    __=cc.download_mod_data()
    __=cc.calc_mod_radiance()
    __=cc.cleanup(True)
    __=cc.output()


Output is in ./logs/output.txt
     
Notes:
Log information can be found in ./logs/calibrationController.log, ./logs/modtran.log

Developed by Nathan Dileas
