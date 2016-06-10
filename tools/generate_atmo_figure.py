import numpy
import matplotlib.pyplot as plt
import math
import sys
import os
import cv2

def get_narr_atmo(base):
    atmo_file = os.path.join(base, 'atmo_interp_narr.txt')
    height, press, temp, hum, dewpoint = numpy.loadtxt(atmo_file, unpack=True)
    
    return  height, press, temp, hum, dewpoint
    
def get_merra_atmo(base):
    atmo_file = os.path.join(base, 'atmo_interp_merra.txt')
    height, press, temp, hum, dewpoint = numpy.loadtxt(atmo_file, unpack=True)
    
    return  height, press, temp, hum, dewpoint
    
    
def plot(base, scene_id, filename):
    figure = plt.figure('TITLE', (15, 9)) #make figure
    plt.figtext(1,1,'dd text to figure at location x, y (relative 0-1 coords). See text() for the meaning of the other arguments.')
    
    ### NARR STUFF
    
    height, press, temp, hum, dewpoint = get_narr_atmo(base)
    
    narr_points_file = os.path.join(base, scene_id+'_mod_narr.jpg')
    narr_points = cv2.imread(narr_points_file)
    b,g,r = cv2.split(narr_points)
    narr_points = cv2.merge([r,g,b])
    
    plt.subplot(241)
    plt.title('NARR data points')
    plt.imshow(narr_points)
    plt.axis('off')
    
    plt.subplot(242)
    a, = plt.plot(temp, height, 'r', label='Temperature')
    b, = plt.plot(dewpoint, height, 'b', label='Dewpoint')
    plt.legend(handles=[a, b])
    plt.xlabel('Degrees [c]')
    plt.ylabel('Geometric Height [km]')
    
    plt.subplot(243)
    a, plt.plot(temp, press, 'r', label='Temperature')
    plt.legend(handles=[a])
    plt.xlabel('Temperature')
    plt.ylabel('Pressure')
    plt.gca().invert_yaxis()
    
    plt.subplot(244)
    a, = plt.plot(hum, press, 'g', label='Humidity')
    plt.legend(handles=[a])
    plt.xlabel('Relative Humidity')
    plt.ylabel('Pressure')
    plt.xlim([0,100])
    plt.gca().invert_yaxis()
    
    ### MERRA STUFF
    
    merra_points_file = os.path.join(base, scene_id+'_mod_merra.jpg')
    merra_points = cv2.imread(merra_points_file)
    b,g,r = cv2.split(merra_points)
    merra_points = cv2.merge([r,g,b])
    
    plt.subplot(245)
    plt.title('MERRA-2 data points')
    plt.imshow(merra_points)
    plt.axis('off')
    
    height, press, temp, hum, dewpoint = get_merra_atmo(base)
    
    plt.subplot(246)
    a, = plt.plot(temp, height, 'r', label='Temperature')
    b, = plt.plot(dewpoint, height, 'b', label='Dewpoint')
    plt.legend(handles=[a, b])
    plt.xlabel('Degrees [c]')
    plt.ylabel('Geometric Height [km]')
    
    plt.subplot(247)
    a, plt.plot(temp, press, 'r', label='Temperature')
    plt.legend(handles=[a])
    plt.xlabel('Temperature')
    plt.ylabel('Pressure')
    plt.gca().invert_yaxis()
    
    plt.subplot(248)
    a, = plt.plot(hum, press, 'g', label='Humidity')
    plt.legend(handles=[a])
    plt.xlabel('Relative Humidity')
    plt.ylabel('Pressure')
    plt.xlim([0,100])
    plt.gca().invert_yaxis()
    
    
    ### SAVE OR SHOW
    plt.subplots_adjust(left=0.05, bottom=0.1, right=0.95, top=0.95, wspace=0.3, hspace=None)
    #plt.show()
    
    figure.savefig(filename)
    
    
if __name__ =='__main__':
    scene_id = sys.argv[1]
    directory = '/dirs/home/ugrad/nid4986/Landsat_Buoy_Calibration/data/scenes/'
    base = os.path.join(directory, scene_id)
    filename = scene_id+'_atmo.png'
    
    plot(base, scene_id, filename)
