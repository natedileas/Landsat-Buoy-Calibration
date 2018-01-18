import numpy

from . import settings


def calc_ltoa_spectral(wavelengths, upwell_rad, gnd_reflect, transmission, skin_temp, water_file=settings.WATER_TXT):
    """
    Calculate modeled radiance for band 10 and 11.

    Args:
        modtran_data: modtran output, Units: [W cm-2 sr-1 um-1]
            upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect
        skin_temp: ground truth surface temperature

    Returns:
        spectral top of atmosphere radiance: Ltoa(lambda) [W m-2 sr-1 um-1]
    """
    # calculate temperature array (input units: [m], [K] output units: [W m-2 sr-1 um-1])
    bb_rad = bb_radiance(wavelengths / 1e6, skin_temp) / 1e6

    # Load Emissivity / Reflectivity
    spec_r_wvlens, spec_r = numpy.loadtxt(water_file, unpack=True, skiprows=3)
    spec_ref = numpy.interp(wavelengths, spec_r_wvlens, spec_r)
    spec_emis = 1 - spec_ref   # calculate emissivity

    # calculate spectral top of atmosphere radiance
    # Ltoa = (Lbb(T) * tau * emis) + (gnd_ref * reflect) + pth_thermal
    # units: [W m-2 sr-1 um-1]
    ltoa_spectral = (upwell_rad * 1e4) + (bb_rad * spec_emis * transmission) + (spec_ref * gnd_reflect * 1e4)

    return ltoa_spectral


def calc_ltoa(wavelengths, ltoa, rsr_file):
    """
    Calculate radiance from spectral radiance and response curve of a sensor.

    Args:
        wavelengths: for LToa [um]
        ltoa: spectral top of atmosphere radiance [W m-2 sr-1 um-1]
        rsr_file: relative spectral response data to use

    Returns:
        radiance: L [W m-2 sr-1 um-1]
    """
    RSR_wavelengths, RSR = numpy.loadtxt(rsr_file, unpack=True)

    w = (wavelengths > RSR_wavelengths.min()) & (wavelengths < RSR_wavelengths.max())

    wvlens = wavelengths[w]
    ltoa_trimmed = ltoa[w]

    # upsample to wavelength range
    RSR = numpy.interp(wvlens, RSR_wavelengths, RSR)

    # calculate observed radiance [ W m-2 sr-1 um-1 ]
    # trapz is a trapezoidal sum
    radiance = numpy.trapz(ltoa_trimmed * RSR, wvlens) / numpy.trapz(RSR, wvlens)

    return radiance


def bb_radiance(wvlen, temp):
    """
    Calculate spectral blackbody radiance.

    Args:
        wvlen: wavelengths to calculate blackbody at [meters]
        temp: temperature to calculate blackbody at [Kelvin]

    Returns:
        rad: [W m-2 sr-1 m-1]
    """
    # define constants
    c = 3e8   # speed of light, [m s-1]
    h = 6.626e-34   # [J*s = kg m2 s-1], planck's constant
    k = 1.38064852e-23   # [m2 kg s-2 K-1], boltzmann's constant

    c1 = 2 * (c * c) * h   # units = [kg m4 s-3]
    c2 = (h * c) / k    # (h * c) / k, units = [m K]

    rad = c1 / ((wvlen**5) * (numpy.e**((c2 / (temp * wvlen))) - 1))

    return rad
