import numpy
from netCDF4 import num2date

from . import data
from .. import settings
from ..download import url_download


def download(date):
    """
    Download NARR Data (netCDF4 format) via ftp.

    Args:
        scene
    """
    # TODO fix narr urls to include new format strings

    date = date.strftime('%Y%m')   # YYYYMM
    narr_files = []

    for url in settings.NARR_URLS:
        url = url % date

        filename = url_download(url, settings.NARR_DIR)
        narr_files.append(filename)

    return narr_files


def read(date, temp, height, shum, chosen_points):
    """
    Pull out chosen data from netcdf4 object and interpoalte in time.

    Args:
        cc: CalibrationController object
        temp, height, shum: netcdf4 objects
        chosen_points: idices to 4 chosen points

    Returns:
        data: shape=(7, 4, 29), units=[km, K, %, torr]
            ght_1, ght_2, tmp_1, tmp_2, rhum_1, rhum_2, pressures
    """

    chosen_points = numpy.array(list(chosen_points))
    latidx = tuple(chosen_points[:, 0])
    lonidx = tuple(chosen_points[:, 1])

    t1, t2 = data.closest_hours(temp.variables['time'][:],
                                temp.variables['time'].units, date)

    t1_dt = num2date(temp.variables['time'][t1], temp.variables['time'].units)
    t2_dt = num2date(temp.variables['time'][t2], temp.variables['time'].units)

    p = numpy.array(temp.variables['level'][:])
    pressure = numpy.reshape([p]*4, (4, len(p)))

    # the .T on the end is a transpose
    tmp_1 = numpy.diagonal(temp.variables['air'][t1, :, latidx, lonidx], axis1=1, axis2=2).T
    tmp_2 = numpy.diagonal(temp.variables['air'][t2, :, latidx, lonidx], axis1=1, axis2=2).T
    temp = data.interp_time(date, tmp_1, tmp_2, t1_dt, t2_dt)

    ght_1 = numpy.diagonal(height.variables['hgt'][t1, :, latidx, lonidx], axis1=1, axis2=2).T / 1000.0   # convert m to km
    ght_2 = numpy.diagonal(height.variables['hgt'][t2, :, latidx, lonidx], axis1=1, axis2=2).T / 1000.0
    height = data.interp_time(date, ght_1, ght_2, t1_dt, t2_dt)

    shum_1 = numpy.diagonal(shum.variables['shum'][t1, :, latidx, lonidx], axis1=1, axis2=2).T
    shum_2 = numpy.diagonal(shum.variables['shum'][t2, :, latidx, lonidx], axis1=1, axis2=2).T
    rhum_1 = data.convert_sh_rh(shum_1, tmp_1, pressure)
    rhum_2 = data.convert_sh_rh(shum_2, tmp_2, pressure)
    rel_hum = data.interp_time(date, rhum_1, rhum_2, t1_dt, t2_dt)

    return height, temp, rel_hum, pressure


def calc_profile(scene, buoy):
    """
    Choose points and retreive narr data from file.

    Args:
        scene: Scene object
        buoy: Buoy object

    Returns:
        data: atmospheric data, shape = (4, 29)
            height, temp, relhum, pressure
        data_coor: coordinates of the atmospheric data points
    """
    temp_file, height_file, shum_file = download(scene.date)

    temp_netcdf = data.open_netcdf4(temp_file)
    height_netcdf = data.open_netcdf4(height_file)
    shum_netcdf = data.open_netcdf4(shum_file)

    # choose points
    indices, lat, lon = data.points_in_scene(scene, temp_netcdf)
    chosen_idxs, data_coor = data.choose_points(indices, lat, lon, buoy.lat, buoy.lon)

    # read in NARR data, each is shape (4, N)
    h, t, rh, p = read(scene.date, temp_netcdf, height_netcdf, shum_netcdf, chosen_idxs)

    # load standard atmosphere for mid-lat summer
    # TODO evaluate standard atmo validity, add different ones for different TOY?
    stan_atmo = numpy.loadtxt(settings.STAN_ATMO, unpack=True)
    h, t, rh, p = data.generate_profiles((h, t, rh, p), stan_atmo)

    # TODO add buoy stuff to bottom of atmosphere

    # interpolate in space, now they are shape (1, N)
    # total is (4, N)
    alpha, beta = data.calc_interp_weights(data_coor, [buoy.lat, buoy.lon])
    height = data.use_interp_weights(h, alpha, beta)
    temp = data.use_interp_weights(t, alpha, beta)
    relhum = data.use_interp_weights(rh, alpha, beta)
    press = data.use_interp_weights(p, alpha, beta)

    return height, temp, relhum, press
