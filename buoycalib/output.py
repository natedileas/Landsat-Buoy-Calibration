def write_atmo(cc, atmo):
    """
    Writes the interpolated atmosphere data to a file. 

    Args:
        cc: CalibrationController object (for save paths)
        atmo: atmospheric profile data to save
    """
    dir_ = os.path.join(cc.scene_dir,'atmo')
    if not os.path.exists(dir_):
        os.makedirs(dir_)
    
    filename = os.path.join(dir_,'atmo_interp')
    
    if cc.atmo_src == 'narr':
        filename += '_narr.txt'
    elif cc.atmo_src == 'merra':
        filename += '_merra.txt'
    
    atmo = numpy.array(atmo)
    dewpoint =  dewpoint_temp(atmo[2], atmo[3])

    save_array = numpy.append(atmo, dewpoint)
    save_array = numpy.transpose(numpy.reshape(save_array, (5, numpy.shape(atmo[2])[0])))

    numpy.savetxt(filename, save_array, fmt='%f\t%f\t%f\t%f\t%f')
