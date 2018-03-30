
if __name__ == '__main__':	
    import buoycalib.display
    import argparse
    import cv2

    parser = argparse.ArgumentParser(description='Preview a LANDSAT scene with the buoy drawn on it.')
    parser.add_argument('scene_id', help='LANDSAT scene ID. Examples: LC08_L1TP_017030_20170703_20170715_01_T1')
    parser.add_argument('-b', '--buoy_id', help='NOAA Buoy ID. Example: 45012', default=None)
    parser.add_argument('-s', '--save', help='save an image out', default=False, action='store_true')
    # TODO NARR or MERRA
    # TODO add MODIS
    # TODO add band choice
    args = parser.parse_args()

    image = buoycalib.display.landsat_preview(args.scene_id, args.buoy_id)
    
    cv2.imshow('Landsat Preview', image)
    cv2.waitKey(0)
    
    if args.save:
        cv2.imwrite('landsat_preview.jpg', image)
