import datetime
from ftplib import FTP

import gdal
import numpy
import glob
import skimage.data
import utm

from .. import settings
from ..download import url_download
from . import image_processing as img
from .modis_tile import latlon_to_tile
from . import mrt_swath 

def download(granule_id, directory_=settings.MODIS_DIR):
    """ download a MODIS scene by granule ID. """
    directory = directory_ + '/' + granule_id

    url = modis_url(granule_id)
    granule_filepath = url_download(url, directory)

    # parse metadata
    ds = gdal.Open(granule_filepath)
    metadata = ds.GetMetadata()
    date = datetime.datetime.strptime(granule_id[9:22], 'A%Y%j.%H%M')

    # also download georeference MOD03
    geo_reference_MOD03 = metadata['ANCILLARYINPUTPOINTER.1']
    url = modis_url(geo_reference_MOD03)
    geo_ref_filepath = url_download(url, directory)

    return date, directory, metadata, [granule_filepath, geo_ref_filepath]


def modis_url(granule_id):
    info = parse_granule(granule_id)
    url = '/'.join([settings.MODIS_URL, info['product'], info['date'].strftime('%Y/%j'), granule_id])

    return url


def parse_granule(granule):
    # reference: https://lpdaac.usgs.gov/dataset_discovery/modis
    """
    MOD09A1 - Product Short Name
    .A2006001 - Julian Date of Acquisition (A-YYYYDDD)
    .h08v05 - Tile Identifier (horizontalXXverticalYY)
    .005 - Collection Version
    .2006012234567 - Julian Date of Production (YYYYDDDHHMMSS)
    .hdf - Data Format (HDF-EOS)
    """
    parsed = {}

    if isinstance(granule, str):
        split = granule.split('.')
        parsed['product'] = split[0]
        parsed['date'] = datetime.datetime.strptime(split[1], 'A%Y%j')
        parsed['horizontal'] = split[2][1:3]
        parsed['vertical'] = split[2][4:6]
    else:   # TODO make custom exception
        raise Exception('Received incorrect scene: {0}'.format(granule))

    return parsed


def modis_from_landsat(date, lat, lon):
    """
    parse a landsat ID and form a valid, downloadable MODIS scene out of it
    focusing on the product MOD021KM (for thermal stuff)
    """
    # transform from lat lon to MODIS tile
    tile_v, tile_h = latlon_to_tile(lat, lon)

    partial = '.'.join(['MOD021KM', date.strftime('A%Y%j'), 'h{0:2d}v{1:2d}'.format(int(tile_h), int(tile_v)), '006'])

    ftp = FTP('ladsweb.nascom.nasa.gov')     # connect to host, default port
    ftp.login()
    ftp.cwd('/allData/6/MOD021KM/{0}/'.format(date.strftime('%Y/%j')))

    list_of_files = ftp.nlst()
    # search through possibles for match
    for possible in list_of_files:
        if partial in possible:  # must be exact sub_string match
            break
    ftp.quit()

    return possible


def calc_ltoa_direct(emmissivities_MOD21KM, geo_reference_MOD03, lat_oi, lon_oi, bands=[31, 32]):

    #print(emmissivities_MOD21KM, geo_reference_MOD03, lat_oi, lon_oi)
    ds = gdal.Open(emmissivities_MOD21KM)
    
    emissive_bands = gdal.Open(ds.GetSubDatasets()[2][0])
    
    #import pprint
    #print('\n'.join([d[1] for d in ds.GetSubDatasets()]))

    band_names = emissive_bands.GetMetadata()['band_names'].split(',')
    radiance_scales = emissive_bands.GetMetadata()['radiance_scales']
    radiance_scales = {int(band_names[i]):float(f) for i, f in enumerate(radiance_scales.split(', '))}
    radiance_offsets = emissive_bands.GetMetadata()['radiance_offsets']
    radiance_offsets = {int(band_names[i]):float(f) for i, f in enumerate(radiance_offsets.split(', '))}
    radiance_units = emissive_bands.GetMetadata()['radiance_units']

    #print(radiance_scales, radiance_offsets)

    # read data in to numpy array form
    emissive_data = emissive_bands.ReadAsArray()
    #print(emissive_data.dtype)

    # geo reference file (matching MOD03 product)       
    geo_reference_ds = gdal.Open(geo_reference_MOD03)
    geo_reference_sds = geo_reference_ds.GetSubDatasets()

    lat_ds = gdal.Open(geo_reference_sds[12][0])
    lon_ds = gdal.Open(geo_reference_sds[13][0])

    lat = lat_ds.ReadAsArray()
    lon = lon_ds.ReadAsArray()

    #print('Shapes: ', lat.shape, lon.shape, emissive_data.shape)

    # find closest point
    distances = (lat - lat_oi)**2 + (lon - lon_oi)**2
    poi_r, poi_c = numpy.unravel_index(numpy.argmin(distances), lat.shape)

    #print('poi: ', poi_r, poi_c)

    radiance = {}
    for b in bands:
        radiance[b] = radiance_scales[b] * (emissive_data[b-21, poi_r, poi_c] - radiance_offsets[b])
        #print('band: ', b, emissive_data[b-21, poi_r, poi_c], radiance_scales[b], radiance_offsets[b], radiance[b])

    return radiance, radiance_units


# function to load in an RSR from the MODIS format
# formatted like this because it's a 1 line function
load_rsr = lambda fname: numpy.genfromtxt(fname, skip_header=9, usecols=(2, 3), unpack=True)


def calc_ltoa(emmissivities_MOD21KM, geo_reference_MOD03, lat_oi, lon_oi, bands=[31, 32]):
    
    # make a parameter file to use with mrt_swath
    directory = '/'.join(emmissivities_MOD21KM.split('/')[:-1])
    prm_out = mrt_swath.make_param_file(emmissivities_MOD21KM, geo_reference_MOD03, lat_oi, lon_oi, directory + '/swath.prm')

    # run swath2grid
    directory = mrt_swath.run_swath2grid(prm_out)

    # then read it out of the geotiff
    # and offset and scale it
    ds = gdal.Open(emmissivities_MOD21KM)
    
    emissive_bands = gdal.Open(ds.GetSubDatasets()[2][0])
    
    band_names = emissive_bands.GetMetadata()['band_names'].split(',')
    radiance_scales = emissive_bands.GetMetadata()['radiance_scales']
    radiance_scales = {float(band_names[i]):float(f) for i, f in enumerate(radiance_scales.split(', '))}
    radiance_offsets = emissive_bands.GetMetadata()['radiance_offsets']
    radiance_offsets = {float(band_names[i]):float(f) for i, f in enumerate(radiance_offsets.split(', '))}
    radiance_units = emissive_bands.GetMetadata()['radiance_units']

    __, __, zone, __ = utm.from_latlon(lat_oi, lon_oi)

    radiance = {}
    for b in bands:
        filename = glob.glob(directory+'/blah*{0}*.tif'.format(b-20))[0]
        poi_r, poi_c = img.find_roi(filename, lat_oi, lon_oi, zone)

        image = skimage.data.load(filename)

        radiance[b] = radiance_scales[b] * (image[poi_r, poi_c] - radiance_offsets[b])
        print('band: ', b, image[poi_r, poi_c], radiance_scales[b], radiance_offsets[b], radiance[b], filename)


    return radiance, radiance_units