def plot_points(cc, args):
    import landsatbuoycalib.image_processing as img_proc

    if cc.satelite == 'LC8':
        img_file = os.path.join(cc.scene_dir, cc.metadata['FILE_NAME_BAND_10'])
    elif cc.satelite == 'LE7':
        img_file = os.path.join(cc.scene_dir, cc.metadata['FILE_NAME_BAND_6_VCID_2'])
    elif cc.satelite == 'LT5':
        img_file = os.path.join(cc.scene_dir, cc.metadata['FILE_NAME_BAND_6'])

    image = img_proc.write_im(cc, img_file)   # PIL image object

    if args.show == True:
        image.show()
    
    save_path = os.path.join(cc.scene_dir, 'output', cc.scene_id+'_mod')
    if cc.atmo_src == 'narr':
        save_path += '_narr.png'
    elif cc.atmo_src == 'merra':
        save_path += '_merra.png'
    image.save(save_path)


def plot_atmo(cc, args):
    import landsatbuoycalib.atmo_data as atmo_data
    import landsatbuoycalib.narr_data as narr_data
    import landsatbuoycalib.merra_data as merra_data
    import matplotlib.pyplot as plt
    import numpy

    if cc.atmo_src == 'narr':
        interp_profile, data_coor = narr_data.calc_profile(cc)
    elif cc.atmo_src == 'merra':
        interp_profile, data_coor = merra_data.calc_profile(cc)
        
    # add buoy data at bottom of atmosphere
    interp_profile = numpy.insert(interp_profile, 0, [cc.buoy_height, cc.buoy_press, cc.buoy_airtemp + 273.13, cc.buoy_rh], axis=1)
    
    figure = atmo_data.plot_atmo(cc, interp_profile)

    if args.show == True:
        plt.show(figure)

    save_path = os.path.join(cc.scene_dir, 'output', cc.scene_id+'_atmo')
    if cc.atmo_src == 'narr':
        save_path += '_narr.png'
    elif cc.atmo_src == 'merra':
        save_path += '_merra.png'
    figure.savefig(save_path)

def plot_atmo(cc, atmo):
    """
    Plots interpolated atmospheric data for user.

    Args:
        cc: CalibrationController object (for save paths)
        atmo: atmospheric profile data to draw plots for

    Returns:
        figure: matplotlib.pyplot figure object, can be saved or displayed 
    """
    height, press, temp, hum = atmo
    dewpoint =  dewpoint_temp(temp, hum)

    figure = plt.figure('%s Atmospheric Profile' % cc.atmo_src, (12, 6)) #make figure  
    
    plt.subplot(131)
    a, = plt.plot(temp, height, 'r', label='Temperature')
    b, = plt.plot(dewpoint, height, 'b', label='Dewpoint')
    plt.legend(handles=[a, b])
    plt.xlabel('Temperature [K]')
    plt.ylabel('Geometric Height [km]')
    
    plt.subplot(132)
    a, plt.plot(temp, press, 'r', label='Temperature')
    plt.legend(handles=[a])
    plt.xlabel('Temperature [K]')
    plt.ylabel('Pressure [hPa]')
    plt.ylim([0,1100])
    plt.gca().invert_yaxis()
    
    plt.subplot(133)
    a, = plt.plot(hum, press, 'g', label='Humidity')
    plt.legend(handles=[a])
    plt.xlabel('Relative Humidity [%]')
    plt.ylabel('Pressure [hPa]')
    plt.ylim([0,1100])
    plt.xlim([0,100])
    plt.gca().invert_yaxis()

    return figure

