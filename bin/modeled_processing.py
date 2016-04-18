import datetime
import os
import math
import numpy
import re
import subprocess
import sys
import utm
import linecache

def read_tape6(case):
    """read in tape6 files and return values
    
    read in parsed files, parse relative spectral response files, etc.
    
    Args:
        caselist: sliced version of caselist, contains values for a narr point
        which_landsat: which landsat band is calculated for currently, list
    
    Returns:
        radiance_up: upwelled radiance, list
        radiance_dn: downwelled radiance, list
        wavelength: wavelengths from parsed tape6, list
        transission_up: upwelled transmission, list
        transission_dn: downwelled transmission, list
        RSR: relative spectral response of appropriate band
        wavelength_RSR: relative spectral response wavelengths
    """

    wavelengths = numpy.zeros(0)
    radiance_up = numpy.zeros(0)
    radiance_dn = numpy.zeros(0)
    transission = numpy.zeros(0)
    
    filename = os.path.join(case, 'parsed')
    
    wavelength = []
    upwelled_radiance = []
    gnd_reflected_radiance = []
    transmission_parsed = []
    total = []

    # read data from file     
    with open(filename, 'r') as f:
        for line in f:
            w, ur, grr, tot, t = line.split(' ')
            wavelength.append(float(w))
            upwelled_radiance.append(float(ur))
            gnd_reflected_radiance.append(float(grr))
            total.append(float(tot))
            transmission_parsed.append(float(t))
    
    # calculate upwelled radiance and transmission
    transission = numpy.asarray(transmission_parsed)
    radiance_up = numpy.asarray(upwelled_radiance)
        
    # calculate downwelled radiance
    transission[numpy.where(transission==0.0000)[0]] = 0.00001
    gnd_reflected_radiance = numpy.asarray(gnd_reflected_radiance)
    radiance_dn = numpy.divide(gnd_reflected_radiance, transission)
    
    # sanity check
    total = numpy.asarray(total)
    radiance_dn_check = numpy.divide(numpy.subtract(total, radiance_up), transission)
    check = numpy.subtract(radiance_dn, radiance_dn_check)
    
    if numpy.sum(numpy.absolute(check)) >= .05:
       print 'Error in modtran module. Total Radiance minus upwelled radianc \
       e is not (approximately) equal to downwelled radiance*transmission'
       sys.exit(-1)

    wavelength = numpy.asarray(wavelength)
    
    # flip wavelength, radiance, and transmission arrays...
    # Tape6parser returns them backwards
    wavelength = numpy.tile(wavelength,(1,1))
    wavelength = numpy.fliplr(wavelength)
    wavelength = wavelength[0]
    
    radiance_up = numpy.tile(radiance_up,(1,1))
    radiance_up = numpy.fliplr(radiance_up)
    radiance_up = radiance_up[0]
    
    radiance_dn = numpy.tile(radiance_dn,(1,1))
    radiance_dn = numpy.fliplr(radiance_dn)
    radiance_dn = radiance_dn[0]
    
    transission = numpy.tile(transission,(1,1))
    transission = numpy.fliplr(transission)
    transission = transission[0]
    
    gnd_reflected_radiance = numpy.tile(gnd_reflected_radiance,(1,1))
    gnd_reflected_radiance = numpy.fliplr(gnd_reflected_radiance)
    gnd_reflected_radiance = gnd_reflected_radiance[0]
    
    return radiance_up, radiance_dn, wavelength, transission, gnd_reflected_radiance
        
def offset_bilinear_interp(array, narr_cor, buoy_coors):
    narr_coor = numpy.absolute(narr_cor)   # 1, 2 , 3, 4
    buoy_coors = numpy.absolute(buoy_coors)
    array = numpy.reshape(array, (4, numpy.shape(array)[0]/4))
    
    a = -narr_coor[0,0] + narr_coor[2,0]
    b = -narr_coor[0,0] + narr_coor[1,0]
    c = narr_coor[0,0] - narr_coor[1,0] - narr_coor[2,0] + narr_coor[3,0]
    d = buoy_coors[0] - narr_coor[0,0]
    e = -narr_coor[0,1] + narr_coor[2,1]
    f = -narr_coor[0,1] + narr_coor[1,1]
    g = narr_coor[0,1] - narr_coor[1,1] - narr_coor[2,1] + narr_coor[3,1]
    h = buoy_coors[1] - narr_coor[0,1]
    
    i = math.sqrt(abs(-4*(c*e - a*g)*(d*f - b*h) + (b*e - a*f + d*g - c*h)**2))
    # i = math.sqrt(abs(-4*(c*e - a*g)*(d*f - b*h) + (b*e - a*f + d*g - c*h)**2))
    
    alpha = -(b*e - a*f + d*g - c*h + i)/(2*c*e - 2*a*g)    
    beta  = -(b*e - a*f - d*g + c*h + i)/(2*c*f - 2*b*g)
    
    return ((1 - alpha) * ((1 - beta) * array[0] + beta * array[1]) + alpha * ((1 - beta) * array[2] + beta * array[3]))
        
def read_RSR(rsr_file):
    """ read in RSR data and return it to the caller. """
    wavelength_RSR = []
    RSR = []
    trans_RSR = []
    data = []
    
    with open(rsr_file, 'r') as f:
        for line in f:    
            data = line.split()
            data = filter(None, data)
            wavelength_RSR.append(float(data[0]))
            RSR.append(float(data[1]))
    
    return RSR, wavelength_RSR
    
def calc_temperature_array(wavelengths, temperature):
    """ make array of blackbody radiances. """
    Lt= []

    for d_lambda in wavelengths:
        x = radiance(d_lambda, temperature)
        Lt.append(x)
        
    return Lt
        
def radiance(wvlen, temp, units='microns'):
    """calculate blackbody radiance given wavelength (in meters) and temperature. """
    
    # define constants
    c = 3e8   # speed of light, m s-1
    h = 6.626e-34	# J*s = kg m2 s-1
    k = 1.38064852e-23 # m2 kg s-2 K-1, boltzmann
    
    c1 = 2 * (c * c) * h   # units = kg m4 s-3
    c2 = (h * c) / k    # (h * c) / k, units = m K    
        
    # calculate radiance
    rad = c1 / (((wvlen**5)) * (math.e**((c2 / (temp * wvlen))) - 1))
    
    # UNITS
    # (W / m^2 * sr) * <wavelength unit>
    return rad
        
def integrate(x, y, method='trap'):
    """approximate integration given two arrays.
    """
    total = 0
    
    if method == 'trap':
        for i in xrange(len(x)):
            try:
                # calculate area of trapezoid and add to total
                area = .5*(x[i+1]-x[i])*(y[i]+y[i+1])
                total += area
            except IndexError:
                break
                
    if method == 'rect':
        for i in xrange(0, len(x)):
            try:
                # calculate area of rectangle and add to total
                area = (x[i+1]-x[i])*(y[i])
                total += abs(area)
            except IndexError:
                break
                
    return total


class MakeTape5s(object):

    geometricHeight_1 = None
    geometricHeight_2 = None
    relativeHumidity_1 = None
    relativeHumidity_2 = None
    temperature_1 = None
    temperature_2 = None
    geometricHeight = None
    relativeHumidity = None
    temperature = None
    stanGeoHeight = None
    stanPress = None
    stanTemp = None
    stanRelHum = None
    date = None
        
    def __init__(self, other):
        self.filepath_base = other.filepath_base
        
        self.metadata = other.metadata
        self.buoy_coors = other.buoy_location
        self.skin_temp = '%3.3f' % (other.skin_temp)
        self.directory = os.path.join(other.filepath_base, 'data/shared/modtran')
        self.home = os.path.join(self.filepath_base, 'data')
        self.buoy_params = [other.buoy_press, other.buoy_airtemp, other.buoy_dewpnt]
        self.verbose = other.verbose
        self.point_dir = os.path.join(other.scene_dir, 'points')
        self.scene_dir = other.scene_dir
        
    def main(self):
        """Reads narr data and generates tape5 files for modtran runs.
       
        Reads narr data, chooses relvant points, generates tape5 files for modtran
        runs, generates caselist(used for parsing files) and command list (used for
        running modtran).
       
        Args:
            self
    
        Returns:
            caseList: list of modtran run cases, list
        """
    
        # choose narr points
        narr_indices, num_points, lat, lon = self.__choose_points()
                
        narr_coor = []
        for i in range(4):
            narr_coor.append([lat[narr_indices[i,0], narr_indices[i,1]],lon[narr_indices[i,0], narr_indices[i,1]]])
            
        # read in NARR data
        # read in NARR data
        if os.path.exists(os.path.join(self.scene_dir, 'narr/HGT_1/1000.txt')):
            print 'NARR Data Successful Download'
            
        else:
            print 'NARR data not downloaded, no wgrib?'
            sys.exit(-1)
            
        pressures = self.__narr_read(narr_indices, lat)
        
        # interplolate in time and load standard atmo
        self.__interpolate_time()
        
        # actually generate tape5 files
        case_list = self.__generate_tape5s(num_points, narr_indices, lat, lon, pressures)
    
        return case_list, narr_coor
        
    def __narr_read(self, narr_indices, lat):
        p = numpy.asarray([1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 725, 700, 650, 600, 550, 500, 450, 400, 350, 300, 275, 250, 225, 200, 175, 150, 125, 100])
        pressures = numpy.reshape([p]*4, (4,29))
        dirs = ['HGT_1', 'HGT_2', 'TMP_1', 'TMP_2', 'SHUM_1', 'SHUM_2']
        
        shape = [277,349]
        indices = [numpy.ravel_multi_index(idx, shape) for idx in narr_indices]
        
        data = [[] for i in range(6)]
        
        for d in dirs:
            for i in indices:
                for press in p:
                    filename = os.path.join(self.scene_dir, 'narr', d, str(press)+'.txt')
                    data[dirs.index(d)].append(float(linecache.getline(filename, i+2)))
        
        data = numpy.reshape(data, (6, 4, 29))  # reshape
        hgt_1, hgt_2, self.temperature_1, self.temperature_2, shum_1, shum_2 = data   # unpack
        
        self.relativeHumidity_1 = self.__convert_sh_rh(shum_1, self.temperature_1, pressures)
        self.relativeHumidity_2 = self.__convert_sh_rh(shum_2, self.temperature_2, pressures)
        
        self.geometricHeight_1 = numpy.divide(hgt_1, 1000.0)   # convert m to km
        self.geometricHeight_2 = numpy.divide(hgt_2, 1000.0)   # convert m to km
        
        return pressures
        
    def __convert_sh_rh(self, specHum, T_k, pressure):
        # Given array of specific humidities, temperature, and pressure, generate array of relative humidities
        # source: http://earthscience.stackexchange.com/questions/2360/how-do-i-convert-specific-humidity-to-relative-humidity
        #print numpy.shape(specHum)
        #print numpy.shape(pressure)
        #print specHum.dtype
        
        T_k = numpy.asarray(T_k, dtype=numpy.float64)  #numpy.float64
        
        # convert input variables
        T_c = numpy.subtract(T_k, 273.15)   #celcius
        q = specHum   #specific humidity
        p = pressure   #pressures
        
        # compute relative humidity
        a = numpy.divide(numpy.multiply(17.67, T_c), numpy.subtract(T_k, 29.65))
        RH = 26.3 * p
        RH = RH * q 
        RH = RH * numpy.power(numpy.exp(a), -1)   #orginally .263, *100 for units
        
        return RH
        
    def __convert_geopotential_geometric(self, geopotential, lat):
        """Convert array of geopotential heightsto geometric heights.
        """
        # source: http://www.ofcm.gov/fmh3/pdf/12-app-d.pdf
        # http://gis.stackexchange.com/questions/20200/how-do-you-compute-the-earths-radius-at-a-given-geodetic-latitude
        
        # convert latitiude to radians
        radlat = (lat * math.pi) / 180.0
        
        # gravity at latitude
        grav_lat = 9.80616 * (1 - 0.002637 * numpy.cos(2 * radlat) + 0.0000059 * numpy.power(numpy.cos(2 * radlat), 2))

        # radius of earth at latitude: R(f)^2 = ( (a^2 cos(f))^2 + (b^2 sin(f))^2 ) / ( (a cos(f))^2 + (b sin(f))^2 )
        R_max = 6378.137    # km
        R_min = 6356.752    # km
        
        part1 = numpy.power((R_max ** 2) * numpy.cos(radlat), 2)
        part2 = numpy.power((R_min ** 2) * numpy.sin(radlat), 2) 
        part3 = numpy.power(R_max * numpy.cos(radlat), 2)
        part4 = numpy.power(R_min * numpy.sin(radlat), 2)
        R_lat = numpy.sqrt((part1 + part2) / (part3 + part4))
        
        # ratio of average gravity to estimated gravity
        grav_ratio = grav_lat * R_lat / 9.80665   #average gravity
        
        # calculate geometric height
        geometric_height = [[0]]*4
        for i in range(4):
            geometric_height[i] = ((R_lat[i] * geopotential[i]) / numpy.absolute(grav_ratio[i] - geopotential[i]))
        
        return numpy.asarray(geometric_height)
    
    def __choose_points(self):
        """Read in coordinates.txt, choose points within scene corners.
        
        Args:
            self
        
        Returns:
            NarrIndices: list of indices of chosen points
            num_points: number of points chosen
            lat: Latitude of all points
            lon: longitude of all points
            
        Helper Functions:
            distance_in_utm: exactly what it sounds like
        """
        # open coordinates.txt
        filename = os.path.join(self.filepath_base, './data/shared/narr/coordinates.txt')
        coordinates = []
        data = ' '
        i = 0
    
        with open(filename, 'r') as f:
            while data != '':
                data = f.readline()
                coordinates.append(data.split(' '))
                while '' in coordinates[i]:
                    coordinates[i].remove('')
                while '\n' in coordinates[i]:
                    coordinates[i].remove('\n')
                i += 1
    
        # pull out i,j,lat, lon and reform to 277x349 grids
        coordinates = numpy.asarray(coordinates)
        i_coor = numpy.empty((len(coordinates)))
        j_coor = numpy.empty((len(coordinates)))
      
        i_coor = [coordinates[x][0] for x in range(len(coordinates)-1)]
        i_coor = numpy.reshape(i_coor,(277,349)).astype(float)
    
        j_coor = [coordinates[x][1] for x in range(len(coordinates)-1)]
        j_coor = numpy.reshape(j_coor,(277,349)).astype(float)
         
        narrLat = [coordinates[x][2] for x in range(len(coordinates)-1)]
        lat = numpy.reshape(narrLat,(277,349)).astype(float)
    
        narrLon= [coordinates[x][3] for x in range(len(coordinates)-1)]
        east = numpy.where(narrLon > 180.0)
        for x in range(len(east[0])):
            narrLon[east[0][x]] = 360.0 - float(narrLon[east[0][x]])
        west = numpy.where(narrLon < 180.0)
        for x in range(len(west[0])):
            narrLon[west[0][x]] = (-1)*float(narrLon[west[0][x]])
        lon = numpy.reshape(narrLon,(277,349)).astype(float)
    
        if self.metadata['CORNER_UL_LAT_PRODUCT'] > 0: 
            landsatHemi = 6
        else: 
            landsatHemi = 7
        
        UL_X = self.metadata['CORNER_UL_LAT_PRODUCT'] + 0.5
        UL_Y = self.metadata['CORNER_UL_LON_PRODUCT'] - 0.5
        LR_X = self.metadata['CORNER_LR_LAT_PRODUCT'] - 0.5
        LR_Y = self.metadata['CORNER_LR_LON_PRODUCT'] + 0.5
        
    
        inLandsat = numpy.asarray([[None,None],[None,None]])
        x_iter = numpy.arange(277)
        
        for k in x_iter:
            try:
            
                for l in xrange(len(lat[1])-1):
                    if lon[k,l] > 180:
                        lon[k,l] = 360 - lon[k,l]
                    else: 
                        lon[k,l] = (-1)*lon[k,l]
                    if lat[k,l] > 84:
                        lat[k,l] = 84
                        
                    curr_utm_point = utm.from_latlon(lat[k,l], lon[k,l])
                    
                    if curr_utm_point[2] <= float(self.metadata['UTM_ZONE']) + 1 and curr_utm_point[2] >= float(self.metadata['UTM_ZONE']) - 1:
                        curr_utm_point = self.__convert_utm_zones(lat[k,l], lon[k,l], curr_utm_point[2], self.metadata['UTM_ZONE'])
                    
                        if curr_utm_point[0] < UL_X:
                            if curr_utm_point[0] > LR_X:
                               if curr_utm_point[1] > UL_Y:
                                   if curr_utm_point[1] < LR_Y:
                                       inLandsat = numpy.append(inLandsat, [[k,l]], axis=0)
                    
            except IndexError:
                print 'IndexError', i
                
        inLandsat = numpy.delete(inLandsat, 0, 0)
        inLandsat = numpy.delete(inLandsat, 0, 0)
        
        num_points = numpy.shape(inLandsat)[0]
        
        if num_points == 0:
            print 'No NARR points in landsat scene. Fatal.'
            sys.exit(-1)
        
        latvalues = []
        lonvalues = []
        ivalues = []
        jvalues = []
        
        for i in range(num_points):
            latvalues.append(lat[inLandsat[i,0],inLandsat[i,1]])
            lonvalues.append(lon[inLandsat[i,0],inLandsat[i,1]])
            ivalues.append(i_coor[inLandsat[i,0],inLandsat[i,1]])
            jvalues.append(j_coor[inLandsat[i,0],inLandsat[i,1]])
        
        pixelSize = self.metadata['GRID_CELL_SIZE_THERMAL']
    
        eastvector = []
        northvector = []
        
        for i in range(num_points): 
            narr_utm_ret = utm.from_latlon(latvalues[i],lonvalues[i])
            eastvector.append(narr_utm_ret[0])
            northvector.append(narr_utm_ret[1])
            
        eastvector = numpy.asarray(eastvector)
        northvector = numpy.asarray(northvector)
    
        buoy_x = utm.from_latlon(self.buoy_coors[0], self.buoy_coors[1])[0]
        buoy_y = utm.from_latlon(self.buoy_coors[0], self.buoy_coors[1])[1]
    
        distances = []
        dist_idx = []
    
        for g in range(num_points):
            try:
                dist = self.__distance_in_utm(eastvector[g],northvector[g],buoy_x,buoy_y)
                if dist > 0:
                    distances.append(dist) 
                    dist_idx.append(g)
            except IndexError as e:
                print e
    
        narr_dict = dict(zip(distances, dist_idx))
        idx = []
    
        closest = sorted(narr_dict)
        
        for m in range(4):
            idx.append(narr_dict[closest[m]])
        
        NARRindices = []
        for n in idx:
            NARRindices.append(list(inLandsat[n]))
        
        NARRindices = numpy.asarray(NARRindices)
        num_points = 4    # do not remove, important
        
        return NARRindices, num_points, lat, lon
        
    def __convert_utm_zones(self, x, y, zone_from, zone_to):
        import ogr, osr
    
        # Spatial Reference System
        inputEPSG = int(float('326' + str(zone_from)))
        outputEPSG = int(float('326' + str(zone_to)))
    
        # create a geometry from coordinates
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(x, y)
    
        # create coordinate transformation
        inSpatialRef = osr.SpatialReference()
        inSpatialRef.ImportFromEPSG(inputEPSG)
    
        outSpatialRef = osr.SpatialReference()
        outSpatialRef.ImportFromEPSG(outputEPSG)
    
        coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
    
        # transform point
        point.Transform(coordTransform)
    
        return point.GetX(), point.GetY()
        
    def __distance_in_utm(self, e1, n1, e2, n2):
        """Calculate distances between UTM coordinates.
        """
        
        s = 0.9996    # scale factor 
        r = 6378137.0    # Earth radius
        
        SR1 = s / (math.cos(e1 / r))
        SR2 = s / (math.cos(((e2 - e1) / 6) / r))
        SR3 = s / (math.cos(e2 / r))
        
        Edist = ((e2 - e1) / 6) * (SR1 + 4 * SR2 + SR3)
        
        d = math.sqrt(Edist**2 + (n2 - n1)**2)
        
        return d
    
    def __interpolate_time(self):
        # determine three hour-increment before and after scene center scan time
        chars = ['"']
        time = self.metadata['SCENE_CENTER_TIME'].replace('"', '')
        hour = int(time[0:2])
        minute = int(time[3:5])
        second = int(time[6:8])
        
        date = self.metadata['DATE_ACQUIRED']
        year = int(date[0:4])
        month = int(date[5:7])
        day = int(date[8:10])
    
        self.date = datetime.datetime.strptime('%s/%s/%s' % (year, month, day), '%Y/%m/%d')
        rem1 = hour % 3
        rem2 = 3 - rem1
        hour1 = hour - rem1
        hour2 = hour + rem2
    
        # round to nearest minute
        if second > 30: minute = minute + 100
    
        # convert hour-min acquisition time to decimal time
        time = hour + minute / 60.0
    
        # interpolate in time
        self.geometricHeight = self.geometricHeight_1 + (time-hour1) * ((self.geometricHeight_2 - self.geometricHeight_1)/(hour2 - hour1))
        self.relativeHumidity = self.relativeHumidity_1 + (time-hour1) * ((self.relativeHumidity_2 - self.relativeHumidity_1)/(hour2 - hour1))
        self.temperature = self.temperature_1 + (time-hour1) * ((self.temperature_2 - self.temperature_1)/(hour2 - hour1))

        # read in file containing standard mid lat summer atmosphere information 
        # to be used for upper layers of atmo profile
        filename = os.path.join(self.filepath_base, 'data/shared/modtran/stanAtm.txt')
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
        
        # separate variables in standard atmosphere
        self.stanGeoHeight = stanAtm[:,0]
        self.stanPress = stanAtm[:,1]
        self.stanTemp = stanAtm[:,2]
        self.stanRelHum = stanAtm[:,3]

        return 0
    
    def __generate_tape5s(self, num_points, NARRindices, lat, lon, pressures):
        """do the messy work of generating the tape5 files and caselist. """
        
        # initialize arrays
        case_list = [''] * num_points
    
        plot_list = [0] * num_points
        for point_idx in range(num_points):
            latString = '%2.3f' % (lat[NARRindices[point_idx,0], NARRindices[point_idx,1]])
            
            if lon[NARRindices[point_idx,0], NARRindices[point_idx,1]] < 0:
                lonString = '%2.2f' % lon[NARRindices[point_idx,0], NARRindices[point_idx,1]]
            else:
                lonString = '%2.3f' % (360.0 - lon[NARRindices[point_idx,0], NARRindices[point_idx,1]])

            currentPoint = os.path.join(self.scene_dir, 'points/%s_%s' % (latString, lonString))
            
            try:
                os.makedirs(currentPoint)
            except OSError:
                pass
            
            if self.geometricHeight[0,point_idx] < 0: gdalt = 0.000 
            else:  gdalt = self.geometricHeight[0,point_idx]
            
            # write to middle file
            p = pressures[0]
            t = self.temperature[point_idx]
            hgt = self.geometricHeight[point_idx]
            rh = self.relativeHumidity[point_idx]
            
            maxLevel = len(p) - 1
            
            delete = numpy.where(hgt < gdalt)
            
            indexBelow = 0
            indexAbove = 1

            if delete[0] != []:
                indexBelow = delete[0][0] - 1
                indexAbove = delete[0][0]

            if abs(gdalt-hgt[indexAbove]) < 0.001:
                tempGeoHeight = hgt[indexAbove:maxLevel]
                tempPress = p[indexAbove:maxLevel]
                tempTemp = t[indexAbove:maxLevel]
                tempRelHum = rh[indexAbove:maxLevel]
            else:
                newPressure = numpy.add(p[indexBelow], (((p[indexAbove]-p[indexBelow])*gdalt-hgt[indexBelow])/(hgt[indexAbove]-hgt[indexBelow])))

                newTemperature = t[indexBelow]+(gdalt-hgt[indexBelow])*((t[indexAbove]-t[indexBelow])/(hgt[indexAbove]-hgt[indexBelow]))          
                newRelativeHumidity = rh[indexBelow]+(gdalt-hgt[indexBelow])*((rh[indexAbove]-rh[indexBelow])/(hgt[indexAbove]-hgt[indexBelow]))
                  
                tempGeoHeight = numpy.insert(hgt[indexAbove:maxLevel], 0, gdalt)
                tempPress = numpy.insert(p[indexAbove:maxLevel], 0, newPressure)
                
                tempTemp = numpy.insert(t[indexAbove:maxLevel], 0, newTemperature)
                tempRelHum = numpy.insert(rh[indexAbove:maxLevel], 0, newRelativeHumidity)
                  
            above = numpy.where(self.stanGeoHeight > hgt[maxLevel])[0]
            
            if numpy.shape(above)[0] > 3:
                interpolateTo = above[0]
                last = len(tempGeoHeight)-1
                stanLast = numpy.shape(self.stanGeoHeight)[0]
              
                newHeight = (self.stanGeoHeight[interpolateTo]+tempGeoHeight[last])/2.0
                newPressure2 = tempPress[last]+(newHeight-tempGeoHeight[last])*((self.stanPress[interpolateTo]-tempPress[last])/(self.stanGeoHeight[interpolateTo]-tempGeoHeight[last]))
                newTemperature2 = tempTemp[last]+(newHeight-tempGeoHeight[last])*((self.stanTemp[interpolateTo]-tempTemp[last])/(self.stanGeoHeight[interpolateTo]-tempGeoHeight[last]))                
                newRelativeHumidity2 = tempRelHum[last]+(newHeight-tempGeoHeight[last])*((self.stanRelHum[interpolateTo]-tempRelHum[last])/(self.stanGeoHeight[interpolateTo]-tempGeoHeight[last]))
                
                tempGeoHeight = numpy.append(numpy.append(tempGeoHeight, newHeight), self.stanGeoHeight[interpolateTo:stanLast])
                tempPress = numpy.append(numpy.append(tempPress, newPressure2), self.stanPress[interpolateTo:stanLast])
                tempTemp = numpy.append(numpy.append(tempTemp, newTemperature2), self.stanTemp[interpolateTo:stanLast])
                tempRelHum = numpy.append(numpy.append(tempRelHum, newRelativeHumidity2), self.stanRelHum[interpolateTo:stanLast])
                
                last = len(tempGeoHeight) - 1
                    
            filename = os.path.join(self.directory, 'tempLayers.txt')
            
            dewpoint_k = tempTemp - ((100 - tempRelHum) / 5)   #kelvin
            #source: http://climate.envsci.rutgers.edu/pdf/LawrenceRHdewpointBAMS.pdf
            

            ##################### BUOY CORRECTION #################################
            
#            print tempPress[0], ' ', self.buoy_params[0]
#            print tempTemp[0], ' ', self.buoy_params[1] + 273.15
#            print dewpoint_k[0], ' ', self.buoy_params[2] + 273.15
            
#            tempPress[0] = self.buoy_params[0]
#            tempTemp[0] = self.buoy_params[1] + 273.15
#            dewpoint_k[0] = self.buoy_params[2] + 273.15
#            
#            #######################################################################

            with open(filename, 'w') as f:
                for k in range(numpy.shape(tempGeoHeight)[0]):
                    line = '%10.3f%10.3e%10.3e%10.3e%10s%10s%15s\n' % \
                    (tempGeoHeight[k], tempPress[k], tempTemp[k], tempRelHum[k] \
                    ,'0.000E+00','0.000E+00', 'AAH2222222222 2')
                    
                    line = line.replace('e', 'E')
                    f.write(line)
            
            plot_list[point_idx] = (tempGeoHeight, tempPress, tempTemp, dewpoint_k)
            
            case_list[point_idx] = currentPoint
            
            numpy.savetxt(os.path.join(self.scene_dir,'atmo_interp_%s.txt'%(point_idx)), plot_list[point_idx])
            
            # assign julian day
            jay = datetime.datetime.strftime(self.date, '%j')
            
            nml = str(numpy.shape(tempGeoHeight)[0])

            gdalt = '%1.3f' % float(gdalt)
            
            # write header and footer parts of tape5 and concatenate
            command = './bin/write_tape5.bash %s %s %s %s %s %s %s %s' % (self.directory, currentPoint, latString, lonString, jay, nml, gdalt, str(self.skin_temp))
            subprocess.check_call(command, shell=True)
            
        # write caseList to file
        case_list_file = os.path.join(self.scene_dir,'points/caseList')
    
        with open(case_list_file, 'w') as f:
            for case in case_list:
                f.write(case + '\n')

        return case_list
