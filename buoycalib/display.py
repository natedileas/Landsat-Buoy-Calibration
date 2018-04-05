import cv2
import io
import urllib.request
import base64

import numpy
from osgeo import gdal, osr
import utm

from . import (sat, atmo, buoy, settings)
img = sat.image_processing

def landsat_preview(scene_id, buoy_id, source='merra', preview_file='landsat_preview.jpg'):
    # get scene visible image

    
    if len(scene_id) == 21:
        path = scene_id[3:6]
        row = scene_id[6:9]
        year = scene_id[9:13]
    elif len(scene_id) == 40:
        path = scene_id[10:13]
        row = scene_id[13:16]
        year = scene_id[17:21]
    """
    image_file = 'https://earthexplorer.usgs.gov/browse/landsat_8/{year}/{path}/{row}/{0}.jpg'.format(scene_id, year=year, path=path, row=row)
    
    #if validators.url(image_file):
    print(image_file)
    image_file = io.BytesIO(urllib.request.urlopen(image_file).read())
    """
    date, directory, metadata = sat.landsat.download(scene_id, ['10'])
    image_file = './{0}/{1}_B10.TIF'.format(directory, scene_id)
    #print(image_file)

    # TODO narr or merra

    merra_points = numpy.load(settings.MERRA_PTS)
    lat = merra_points['merra_lat']
    lon = merra_points['merra_lon']
    loc = list(zip(lat.flatten(), lon.flatten()))

    corners = sat.wrs2.wrs2_to_corners(int(path), int(row))
    points_to_draw = [p for p in loc if point_in_corners(corners, p)]
    buoys = buoy.datasets_in_corners(corners)
    #print(corners, buoys)
    #ds = buoy.all_datasets()[buoy_id]

    dataset = gdal.Open(image_file)
    geotransform = dataset.GetGeoTransform()   # get data transform
    merra_pixels = [latlon_to_pizel(geotransform, *p, metadata['UTM_ZONE']) for p in points_to_draw]

    #print(corners)
    buoy_pixels = [latlon_to_pizel(geotransform, buoy.all_datasets()[ds].lat, buoy.all_datasets()[ds].lon, metadata['UTM_ZONE']) for ds in buoys]
    buoy_ids = [ds for ds in buoys]
    image = cv2.imread(image_file, 0)
    image[image==0] = image[image!=0].mean()
    image = cv2.equalizeHist(image)
    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    image = draw_points(image, [None]*len(merra_pixels), merra_pixels)
    image = draw_points(image, buoy_ids, buoy_pixels, color=(0,0,255))
    image = cv2.resize(image, (512,512))

    return image
    

def web_draw_latlon(image_file, corners, text=[], loc=[], r=5, color=(255, 0, 0), size=(300,300)):
    if validators.url(image_file):
        image_file = io.BytesIO(urllib.request.urlopen(image_file).read())
    
    image = draw_latlon(image_file, corners, text, loc, r, color, size)

    _buffer = io.BytesIO()
    image.save(_buffer, format="JPEG")
    img_str = base64.b64encode(_buffer.getvalue()).decode('ascii')
    return 'data:image/jpg;base64, '+str(img_str)


def draw_points(image, text=[], loc=[], r=100, color=(255, 0, 0), size=None):

    for i, point in enumerate(loc):
        pr, pc = point
        cv2.circle(image, point, r, color, -1)
        
        if text[i]:
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(image, text[i], point, font, r/12,(255,255,255), 20, cv2.LINE_AA)

    return image


def latlon_to_pixel_naive(shape, corners, point):
    """
    assume indexing in image is from upper left (like opencv)
    """
    c, r = shape
    ur_lat, ll_lat, ur_lon, ll_lon = corners
    lat, lon = point


    row_percent = (lat - ll_lat) / (ur_lat - ll_lat)
    col_percent = (lon - ll_lon) / (ur_lon - ll_lon)

    return c - int(col_percent * c), int(row_percent * r)


def latlon_to_pizel(geotransform, lat, lon, zone):

    # change lat_lon to same projection
    l_x, l_y, l_zone, l_zone_let = utm.from_latlon(lat, lon)

    if zone != l_zone:
        l_x, l_y = img.convert_utm_zones(l_x, l_y, l_zone, zone)

    # calculate pixel locations: http://www.gdal.org/gdal_datamodel.html
    row = int((l_x - geotransform[0]) / geotransform[1])   # latitude
    column = int((l_y - geotransform[3]) / geotransform[5])   # longitude

    return row, column


def point_in_corners(corners, point):
    ur_lat, ll_lat, ur_lon, ll_lon = corners
    lat, lon = point

    if ur_lat > 0 and not (ll_lat < lat < ur_lat):
        return False
    elif ur_lat <= 0 and not (ll_lat > lat > ur_lat):
        return False

    if ur_lon > 0 and not (ll_lon > lon > ur_lon):
        return False
    elif ur_lon <= 0 and not (ll_lon < lon < ur_lon):
        return False

    return True

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


def write_im(cc, img_file):
    """
    Write buoy and atmo data point locations on image for human inspection.

    Args:
        cc: CalibrationController object
        img_file: path/file to write on

    Returns:
        None
    """
    zone = cc.metadata['UTM_ZONE']
    narr_pix = []

    # get narr point locations
    for lat, lon in cc.narr_coor:
        narr_pix.append(find_roi(img_file, lat, lon, zone))

    # draw circle on top of image to signify narr points
    image = Image.open(img_file)

    # convert to proper format
    if image.mode == 'L':
        image = image.convert('RGB')
    elif 'I;16' in image.mode:
        image = image.point(lambda i:i*(1./256.0)).convert('RGB')

    img = numpy.asarray(image)
    gray_image = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=6.0, tileGridSize=(8,8))
    cl1 = clahe.apply(gray_image)

    img_corrected = Image.fromarray(cl1)
    img_corrected = img_corrected.convert('RGBA')

    draw = ImageDraw.Draw(img_corrected)
    r = 80

    for x, y in narr_pix:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0))

    # draw buoy onto image
    x = cc.poi[0]
    y = cc.poi[1]
    draw.ellipse((x - r, y - r, x + r, y + r), fill=(0, 255, 0))

    # downsample
    new_size = (int(image.size[0] / 15), int(image.size[1] / 15))
    image = img_corrected.resize(new_size, Image.ANTIALIAS)

    # put alpha mask in
    data = image.getdata()
    newData = []

    for item in data:
        #print item
        if item[0] < 5 and item[1] < 5 and item[2] < 5:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)

    image.putdata(newData)

    return image
