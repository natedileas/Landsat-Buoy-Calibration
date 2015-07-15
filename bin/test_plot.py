import numpy
import matplotlib.pyplot
import math

def plot(x, y, x2=None, y2=None, x3=None, y3=None, flip=False):
    figure = matplotlib.pyplot.figure('TITLE', (9, 9)) #make figure
    
    if flip:
        axes1 = matplotlib.pyplot.subplot(1, 1, 1)
        axes1 = matplotlib.pyplot.plot(y, x, 'black')
        axes1 = matplotlib.pyplot.xlabel('Temperature')
        axes1 = matplotlib.pyplot.ylabel('Height (Geometric)')
        if y2 != None and x2 != None:  axes1 = matplotlib.pyplot.plot(y2, x2, color='red')
        if y3 != None and x3 != None: axes1 = matplotlib.pyplot.plot(y3, x3, color='blue')
    else:
        axes1 = matplotlib.pyplot.subplot(1, 1, 1)
        axes1 = matplotlib.pyplot.plot(x, y, 'ro')
        axes1 = matplotlib.pyplot.xlabel('Temperature')
        axes1 = matplotlib.pyplot.ylabel('Height (Geometric)')
        if y2 != None and x2 != None: axes1 = matplotlib.pyplot.plot(x2, y2, color='black')
        if y3 != None and x3 != None: axes1 = matplotlib.pyplot.plot(x3, y3, color='blue')

    
    #axes2 = matplotlib.pyplot.subplot(2, 2, 2) #2 rows, 1 column, 2nd plot
    
    #axes2 = matplotlib.pyplot.title('L_up: ')

    #axes3 = matplotlib.pyplot.subplot(2, 2, 3) #2 rows, 1 column, 3rd element
    #axes3 = matplotlib.pyplot.plot(wvlens, Trans, color='blue')     
    #axes3 = matplotlib.pyplot.xlabel('Wavelength (microns)')
    #axes3 = matplotlib.pyplot.ylabel('Radiance [W / m^2 / micon / sr]')
    #axes3 = matplotlib.pyplot.title('Transmission: ')

    #axes4 = matplotlib.pyplot.subplot(2, 2, 4) #2 rows, 1 column, 4th element
    #axes4 = matplotlib.pyplot.plot(wvlens, RSR, color='blue')     
    #axes4 = matplotlib.pyplot.xlabel('Wavelength (microns)')
    #axes4 = matplotlib.pyplot.ylabel('Relative Spectral Response')
    #axes4 = matplotlib.pyplot.title('Relative Spectral Response: ')

    #matplotlib.pyplot.show()
    filename = 'plot0s.png'
    figure.savefig(filename)
    
def modrad_plot(x, uprad, dwnrad, trans, ltoa):
    figure = matplotlib.pyplot.figure('TITLE', (18, 18)) #make figure

    axes1 = matplotlib.pyplot.subplot(2, 2, 1)
    axes1 = matplotlib.pyplot.plot(x, dwnrad, 'bo')
    axes1 = matplotlib.pyplot.xlabel('Wavelength [microns]')
    axes1 = matplotlib.pyplot.ylabel('Radiance [W / m^2 / micon / sr]')
    axes1 = matplotlib.pyplot.title('L_DOWN')

    axes2 = matplotlib.pyplot.subplot(2, 2, 2) #2 rows, 1 column, 2nd plot
    axes2 = matplotlib.pyplot.plot(x, uprad, 'bo')
    axes2 = matplotlib.pyplot.xlabel('Wavelength [microns]')
    axes2 = matplotlib.pyplot.ylabel('Radiance [W / m^2 / micon / sr]')
    axes2 = matplotlib.pyplot.title('L_UP')

    axes3 = matplotlib.pyplot.subplot(2, 2, 3) #2 rows, 1 column, 3rd element
    axes2 = matplotlib.pyplot.plot(x, trans, 'bo')
    axes3 = matplotlib.pyplot.xlabel('Wavelength [microns]')
    axes3 = matplotlib.pyplot.ylabel('Transmission')
    axes3 = matplotlib.pyplot.title('Transmission: ')

    axes4 = matplotlib.pyplot.subplot(2, 2, 4) #2 rows, 1 column, 4th element
    axes4 = matplotlib.pyplot.plot(x, ltoa, 'bo')
    axes4 = matplotlib.pyplot.xlabel('Wavelength [microns]')
    axes4 = matplotlib.pyplot.ylabel('Radiance [W / m^2 / micon / sr]')
    axes4 = matplotlib.pyplot.title('L_TOA')

    #matplotlib.pyplot.show()
    filename = 'plot0s.png'
    figure.savefig(filename)

def read_stan_atmo():
    filename = '../data/modtran/stanAtm.txt'
    stanAtm = []
    chars = ['\n']
    
    with open(filename, 'r') as f:
        for line in f:
            data = line.translate(None, ''.join(chars))
            data = data.split(' ')
            data = filter(None, data)
            data = [float(j) for j in data]
            stanAtm.append(data)

    stanAtm = numpy.asarray(stanAtm)
        
    #separate variables in standard atmosphere
    stanGeoHeight = stanAtm[:,0]
    stanPress = stanAtm[:,1]
    stanTemp = stanAtm[:,2]
    stanRelHum = stanAtm[:,3]
    
    return stanGeoHeight, stanPress, stanTemp, stanRelHum
    
def _radiance(wvlen):
    """calculate blackbody radiance given wavelength and temperature.
    """
        
    #define constants
    c1 = 374151000   #boltzman's const
    c2 = 14387.9
        
        #calculate radiance
    rad = c1/((math.pi*(wvlen**5))*(math.e**((c2/(300.0 * wvlen)))-1))

    return rad

def _calc_temperature_array(wavelengths):
    """make array of blackbody radiances.
    """
    Lt= []
    
    for i in wavelengths:
        x = _radiance(i)
        Lt.append(x)
            
    return Lt

    
if __name__ =='__main__':
    a = numpy.arange(8,14,.05)
    b = _calc_temperature_array(a)
    plot(a, b)
