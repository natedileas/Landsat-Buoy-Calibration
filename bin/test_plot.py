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

def compare_narr(scene1, scene2):
    figure = matplotlib.pyplot.figure('TITLE', (18, 18)) #make figure

    axes1 = matplotlib.pyplot.subplot(2, 2, 1)
    axes1 = matplotlib.pyplot.plot(scene1[1], scene1[0], 'b')
    axes1 = matplotlib.pyplot.plot(scene2[1], scene2[0], 'r')

    axes2 = matplotlib.pyplot.subplot(2, 2, 2) #2 rows, 1 column, 2nd plot
    axes2 = matplotlib.pyplot.plot(scene1[2], scene1[0], 'b')
    axes2 = matplotlib.pyplot.plot(scene2[2], scene2[0], 'r')

    axes3 = matplotlib.pyplot.subplot(2, 2, 3) #2 rows, 1 column, 3rd element
    axes3 = matplotlib.pyplot.plot(scene1[3], scene1[0], 'b')
    axes3 = matplotlib.pyplot.plot(scene2[3], scene2[0], 'r')

    axes4 = matplotlib.pyplot.subplot(2, 2, 4) #2 rows, 1 column, 4th element
    #axes4 = matplotlib.pyplot.plot(scene1[0], scene1[4], 'b')
    #axes4 = matplotlib.pyplot.plot(scene2[0], scene2[4], 'r')
    
    matplotlib.pyplot.show()
    
if __name__ =='__main__':
    
    scene1 = numpy.loadtxt("/cis/ugrad/nid4986/summer_2015/BuoyCalib_Cmd/data/scenes/LC80130332013145LGN00/atmo_interp_1.txt")
    scene2 = numpy.loadtxt("/cis/ugrad/nid4986/summer_2015/BuoyCalib_Cmd/data/scenes/LC80410372013101LGN01/atmo_interp_1.txt")
    #print scene1
    compare_narr(scene1, scene2)
