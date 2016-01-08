import numpy
import matplotlib.pyplot
import math

def modplot(x, uprad, dwnrad, trans, ltoa, save_name='plot', show=False):
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
    
    if show:
        matplotlib.pyplot.show()
    figure.savefig(save_name+'.png')
    
def plot_atmo(plot_list, radiosonde=None, show=False):
    xlabel = ['Pressure [mb]', 'Temperature [K]', 'Dew Point Temperature[K]']
    
    for j in range(3):
        #print i
        figure = matplotlib.pyplot.figure('TITLE', (9, 9)) #make figure
        
        axes1 = matplotlib.pyplot.subplot(1, 1, 1)
        axes1 = matplotlib.pyplot.plot(plot_list[0][j], plot_list[0][0], color='black')
        axes1 = matplotlib.pyplot.xlabel(xlabel[j-1])
        axes1 = matplotlib.pyplot.ylabel('Height (Geometric)')
        axes1 = matplotlib.pyplot.plot(plot_list[1][j], plot_list[1][0], 'r^')
        axes1 = matplotlib.pyplot.plot(plot_list[2][j], plot_list[2][0], color='blue', ls='-.')
        axes1 = matplotlib.pyplot.plot(plot_list[3][j], plot_list[3][0], color='green', ls='--')
        axes1 = matplotlib.pyplot.plot(radiosonde[j], radiosonde[0], 'b^')
        
        if show:
            matplotlib.pyplot.show()
        figure.savefig(xlabel[j-1]+'.png')
    
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
