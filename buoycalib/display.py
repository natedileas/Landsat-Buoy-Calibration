from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 
import validators
import io
import urllib.request

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


def draw_latlon(image_file, new_file, corners, text=[], loc=[], r=10, color=(255, 0, 0)):
    if validators.url(image_file):
        image_file = io.BytesIO(urllib.request.urlopen(image_file).read())
    image = Image.open(image_file)
    image = image.convert('RGB')
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()#truetype("sans-serif.ttf", 16)

    for i, point in enumerate(loc):
        pr, pc = latlon_to_pixel_naive(image.size, corners, point)
        circ = [pc - r, pr - r, pc + r, pr + r]
        draw.ellipse(circ, fill=color)
        draw.text((pc + r + 5, pr + r + 5), text[i], color, font=font)

    image.save(new_file)
    return new_file


def latlon_to_pixel_naive(shape, corners, point):
    """
    assume indexing in image is from upper left (like opencv)
    """
    r, c = shape
    ur_lat, ll_lat, ur_lon, ll_lon = corners
    lat, lon = point

    row_percent = (lat - ll_lat) / (ur_lat - ll_lat)
    col_percent = (lon - ll_lon) / (ur_lon - ll_lon)

    return int(row_percent * r), int(col_percent * c)


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
