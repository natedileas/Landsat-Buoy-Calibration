def calc_ltoa(cc, modtran_data):
    """
    Calculate modeled radiance for band 10 and 11.

    Args:
        cc: CalibrationController object
        
        modtran_data: modtran output, Units: [W cm-2 sr-1 um-1]
            upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect

    Returns:
        top of atmosphere radiance: Ltoa [W m-2 sr-1 um-1]
    """
    upwell, downwell, wavelengths, tau, gnd_ref = modtran_data

    # calculate temperature array
    Lt = calc_temperature_array(wavelengths / 1e6, cc.skin_temp) / 1e6   # w m-2 sr-1 um-1

    # Load Emissivity / Reflectivity
    water_file = os.path.join(settings.MISC_FILES, 'water.txt')
    spec_r_wvlens, spec_r = numpy.loadtxt(water_file, unpack=True, skiprows=3)
    spec_ref = numpy.interp(wavelengths, spec_r_wvlens, spec_r)
    spec_emis = 1 - spec_ref   # calculate emissivity

    # calculate top of atmosphere radiance (spectral)
    ## Ltoa = (Lbb(T) * tau * emis) + (gnd_ref * reflect) + pth_thermal  [W m-2 sr-1 um-1]
    Ltoa = (upwell * 1e4 + (Lt * spec_emis * tau) + (spec_ref * gnd_ref * 1e4))

    return Ltoa

def calc_radiance(wavelengths, ltoa, rsr_file):
    """
    Calculate modeled radiance for band 10 and 11.

    Args:
        wavelengths: for LToa [um]
        LToa: top of atmosphere radiance [W m-2 sr-1 um-1]
        rsr_file: relative spectral response data to use

    Returns:
        radiance: L [W m-2 sr-1 um-1]
    """
    RSR_wavelengths, RSR = numpy.loadtxt(rsr_file, unpack=True)

    w = numpy.where((wavelengths > RSR_wavelengths.min()) & (wavelengths < RSR_wavelengths.max()))
    
    wvlens = wavelengths[w]
    ltoa_trimmed = ltoa[w]

    # upsample to wavelength range
    RSR = numpy.interp(wvlens, RSR_wavelengths, RSR)

    # calculate observed radiance [ W m-2 sr-1 um-1 ]
    modeled_rad = numpy.trapz(ltoa_trimmed * RSR, wvlens) / numpy.trapz(RSR, wvlens)
    
    return modeled_rad

    
def calc_temperature_array(wavelengths, temperature):
    """
    Calculate spectral radiance array based on blackbody temperature.

    Args:
        wavelengths: wavelengths to calculate at [meters]
        temperature: temp to use in blackbody calculation [Kelvin]

    Returns:
        Lt: spectral radiance array [W m-2 sr-1 m-1]
    """
    Lt= []

    for d_lambda in wavelengths:
        x = radiance(d_lambda, temperature)
        Lt.append(x)
        
    return numpy.asarray(Lt)
        
def radiance(wvlen, temp):
    """
    Calculate spectral blackbody radiance.

    Args:
        wvlen: wavelength to calculate blackbody at [meters]
        temp: temperature to calculate blackbody at [Kelvin]

    Returns:
        rad: [W m-2 sr-1 m-1]
    """
    # define constants
    c = 3e8   # speed of light, m s-1
    h = 6.626e-34	# J*s = kg m2 s-1
    k = 1.38064852e-23 # m2 kg s-2 K-1, boltzmann
    
    c1 = 2 * (c * c) * h   # units = kg m4 s-3
    c2 = (h * c) / k    # (h * c) / k, units = m K    
        
    rad = c1 / ((wvlen**5) * (math.e**((c2 / (temp * wvlen))) - 1))
    
    return rad
