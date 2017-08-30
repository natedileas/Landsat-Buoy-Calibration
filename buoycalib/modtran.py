def run_modtran(self):
    """
    Make tape5, run modtran and parse tape7.scn for this instance.

    Args: None

    Returns: 
        Relevant Modtran Outputs: spectral, units=[] TODO
            upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect
    """
    logging.info('Generating tape5 files.')
    # read in narr data and generate tape5 files and caseList
    point_dir, self.narr_coor = mod_proc.make_tape5s(self)
    
    logging.info('Running modtran.')
    mod_proc.run_modtran(point_dir)
    
    logging.info('Parsing modtran output.')
    upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect = mod_proc.parse_tape6(point_dir)
    return upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect

def make_tape5s(cc):
    """
    Read atmospheric data and generates tape5 files for modtran runs. 

    Args:
        cc: CalibrationController object

    Returns:
        point_dir, data_coor: directory where modtran needs to be run, and the
        coordinates of the points where the atmospheric data was taken from.
    """

    if cc.atmo_src == 'narr':
        interp_profile, data_coor = narr_data.calc_profile(cc)
    elif cc.atmo_src == 'merra':
        interp_profile, data_coor = merra_data.calc_profile(cc)
        
    # add buoy data at bottom of atmosphere
    interp_profile = numpy.insert(interp_profile, 0, [cc.buoy_height, cc.buoy_press, cc.buoy_airtemp + 273.13, cc.buoy_rh], axis=1)

    atmo_data.write_atmo(cc, interp_profile)   # save out to file

    point_dir = write_tape5(cc, interp_profile)

    return point_dir, data_coor

def write_tape5(cc, profile):
    """
    Write the profile to a tape5 file.
    
    Args:
        cc: CalibrationController object
        profile: atmospheric data: height, press, temp, relhum

    Returns:
        point_dir: directory in which the tape5 is written
    """
    height, press, temp, relhum = profile

    if cc.buoy_location[1] < 0:
        lonString = '%2.2f' % cc.buoy_location[1]
    else:
        lonString = '%2.3f' % (360.0 - cc.buoy_location[1])

    point_dir = os.path.join(cc.scene_dir, 'modtran_%s' % cc.buoy_id)

    try:
        os.makedirs(point_dir)
    except OSError:
        pass

    jay = datetime.datetime.strftime(cc.date, '%j')   # day of year (julian)
    nml = str(numpy.shape(height)[0])   # number of layers
    gdalt = '%1.3f' % float(height[0])   # ground altitude

    with open(settings.HEAD_FILE_TEMP, 'r') as f:
        head = f.read()
        head = head.replace('nml', nml)
        head = head.replace('gdalt', gdalt)
        head = head.replace('tmp____', '%3.3f' % cc.skin_temp)

    with open(settings.TAIL_FILE_TEMP, 'r') as f:
        tail = f.read()
        tail = tail.replace('longit', lonString)
        tail = tail.replace('latitu', '%2.3f' % cc.buoy_location[0])
        tail = tail.replace('jay', jay)

    tape5_file = os.path.join(point_dir, 'tape5')

    with open(tape5_file, 'w') as f:
        f.write(head)
        
        for k in range(numpy.shape(height)[0]):
            line = '%10.3f%10.2E%10.2E%10.2E%10s%10s%15s\n' % \
            (height[k], press[k], temp[k], relhum[k] ,'0.000E+00','0.000E+00', 'AAH2222222222 2')
            
            f.write(line)
            
        f.write(tail)

    return point_dir

def run_modtran(directory):
    """
    Run modtran in the specified directory.

    Args:
        directory: location to run modtran from.

    Returns:
        None
    """
    d = os.getcwd()
    os.chdir(directory)

    try:
        subprocess.check_call('ln -sf %s' % settings.MODTRAN_DATA, shell=True)
        subprocess.check_call(settings.MODTRAN_EXE, shell=True)
    except subprocess.CalledProcessError:  # symlink already exists error
        pass

    os.chdir(d)
    
def parse_tape7scn(directory):
    """
    Parse modtran output file into needed quantities.

    Args:
        directory: where the file is located

    Returns:
        upwell_rad, downwell_rad, wvlen, trans, gnd_ref:
        Needed info for radiance calculation Units: [W cm-2 sr-1 um-1]
    """
    filename = os.path.join(directory, 'tape7.scn')
    
    data = numpy.genfromtxt(filename,  skip_header=11, skip_footer=1, \
    usecols=(0,1,2,6,8), unpack=True)   
    
    wvlen, trans, pth_thm, gnd_ref, total = data
    
    downwell_rad = gnd_ref / trans   # calculate downwelled radiance
    upwell_rad = pth_thm   # calc upwelled radiance
    
    # sanity check
    check = downwell_rad - ((total - upwell_rad) / trans)
    if numpy.sum(numpy.absolute(check)) >= .05:
       logging.error('Error in modtran module. Total Radiance minus upwelled \
       radiance is not (approximately) equal to downwelled radiance*transmission')
       sys.exit(-1)

    trans[numpy.where(trans == 0)] = 0.000001
    return upwell_rad, downwell_rad, wvlen, trans, gnd_ref

def parse_tape6(directory):
    """
    Parse modtran output file into needed quantities.

    Args:
        directory: where the file is located

    Returns:
        upwell_rad, downwell_rad, wvlen, trans, gnd_ref:
        Needed info for radiance calculation
        Units: [W cm-2 sr-1 um-1]
    """
    filename = os.path.join(directory, 'tape6')

    with open(filename, 'r') as f:
        data = f.read()

    d = data.split('\n')
    a = []
    
    for idx, i in enumerate(d):
        i = i.split()
        
        try:
            if 710 <= float(i[0]) <= 1120 and len(i) == 15:
                a.append(i)
        except IndexError:
            pass
        except ValueError:
            pass
    
    data = numpy.array(a, dtype=numpy.float64)
    data = data[:, (1,3,9,12,14)]
            
    wvlen, upwell_rad, gnd_ref, total, trans = data.T

    return upwell_rad[::-1], None, wvlen[::-1], trans[::-1], gnd_ref[::-1]
