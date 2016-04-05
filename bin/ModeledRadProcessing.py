import datetime
import os
import math
import numpy
import re
import subprocess
import sys
import utm
import linecache

class ModeledRadProcessing(object):
    def __init__(self, other):
        # for tape5 generation 
        self.metadata = other.metadata
        self.buoy_coors = other.buoy_location

        # for modradprocesing
        self.filepath_base = other.filepath_base
        self.scene_dir = other.scene_dir

        # both
        self.skin_temp = other.skin_temp
        self.verbose = other.verbose
        
        self.buoy_press = other.buoy_press
        self.buoy_airtemp = other.buoy_airtemp
        self.buoy_dewpnt = other.buoy_dewpnt

        if other.satelite == 'LC8':
            self.which_landsat = [8,2]
        else: 
            self.which_landsat = [7,1]

        self.verbose = other.verbose

    def do_processing(self):
        print 'do_processing: generating tape5 files'
         
        # read in narr data and generate tape5 files and caseList
        current_dir = os.getcwd()
        os.chdir(self.filepath_base)
        mt5 = MakeTape5s(self)
        ret_vals = mt5.main()   # first_files equivalent
        
        if ret_vals != -1:
            caseList, narr_coor = ret_vals
        else:
            return -1

        print 'do_processing: running modtran and parsing tape6 files'
        
        # change access to prevent errors
        modtran_bash_path = os.path.join(self.filepath_base, 'bin/modtran.bash')
        os.chmod(modtran_bash_path, 0755)   
        
        v = -1
        if self.verbose:
            v = 0                                        
        subprocess.check_call('./bin/modtran.bash %s %s' % (v, os.path.join(self.scene_dir, 'points')), shell=True)

        return_radiance = []
        radiances = []
        
        # OLD Emissivity
        # emissivity = .986
        # reflectivity = 1 - emissivity
        
        # New Emissivity
        spec_r = numpy.array(0)
        spec_r_wvlens = numpy.array(0)
        water_file = './data/shared/water.txt'
        
        with open(water_file, 'r') as f:
            water_file = f.readlines()
            for line in water_file[3:]:
                data = line.split()
                spec_r_wvlens = numpy.append(spec_r_wvlens, float(data[0]))
                spec_r = numpy.append(spec_r, float(data[1].replace('\n', '')))
        
        num_bands = self.which_landsat[1]

        for i in range(num_bands):
            upwell_rad = []
            downwell_rad = []
            wavelengths = []
            transmission = []
            gnd_reflect = []
            
            print 'do_processing: band %s of %s' % (i+1, num_bands)
            
            for i in range(4):
                # read relevant tape6 files
                caseList_p = caseList[i]
                ret_vals = self.__read_tape6(caseList_p)
                
                upwell_rad = numpy.append(upwell_rad, ret_vals[0])   # W cm-2 sr-1 um-1
                downwell_rad = numpy.append(downwell_rad, ret_vals[1])   # W cm-2 sr-1 um-1
                wavelengths = ret_vals[2]   # microns
                transmission = numpy.append(transmission, ret_vals[3])   # no units
                gnd_reflect = numpy.append(gnd_reflect, ret_vals[4])   # W cm-2 sr-1 um-1
                
            upwell_rad = self.__offset_bilinear_interp(upwell_rad, narr_coor)
            downwell_rad = self.__offset_bilinear_interp(downwell_rad, narr_coor)
            transmission = self.__offset_bilinear_interp(transmission, narr_coor)
            gnd_reflect = self.__offset_bilinear_interp(gnd_reflect, narr_coor)
            
            #save_a = array([wavelengths, upwell_rad, downwell_rad, transmission, gnd_reflect])
            #numpy.savetxt('atmo_interp.txt', save_a, fmt='%.4e %+.4j %.4e %+.4j %.4e %+.4j %.4e %+.4j')
            
            RSR, RSR_wavelengths = self.__read_RSR()
                
            # interpolate RSR and reflectivity to match wavelength range
            # upsampling the rsr may be causing issues.
            #RSR = numpy.interp(wavelengths, RSR_wavelengths, RSR)
            #spec_reflectivity = numpy.interp(wavelengths, spec_r_wvlens, spec_r)
            
            
            upwell_rad = numpy.interp(RSR_wavelengths, wavelengths, upwell_rad)
            downwell_rad = numpy.interp(RSR_wavelengths, wavelengths, downwell_rad)
            transmission = numpy.interp(RSR_wavelengths, wavelengths, transmission)
            gnd_reflect = numpy.interp(RSR_wavelengths, wavelengths, gnd_reflect)
            spec_reflectivity = numpy.interp(RSR_wavelengths, spec_r_wvlens, spec_r)
            
            spec_emissivity = 1 - spec_reflectivity   # calculate emissivity

            RSR_wavelengths = numpy.asarray(RSR_wavelengths) / 1e6   # convert to meters
            
            # calculate temperature array
            Lt = self.__calc_temperature_array(RSR_wavelengths)  # w m-2 sr-1 m-1
            # calculate top of atmosphere radiance
            
            # OLD METHOD
            #term1 = numpy.multiply(Lt, spec_emissivity)
            #term2 = numpy.multiply(downwell_rad, spec_reflectivity)
            #term1_2 = numpy.add(term1,term2)
            #term3 = numpy.multiply(transmission, term1_2)
            #Ltoa = numpy.add(upwell_rad, term3)
            
            # NEW METHOD 
            ## Ltoa = (Lbb(T) * tau * emis) + (gnd_ref * reflect) + pth_thermal
            term1 = Lt * spec_emissivity * transmission # W m-2 sr-1 m-1
            term2 = spec_reflectivity * (gnd_reflect * 1e10) # W m-2 sr-1 m-1
            Ltoa = (upwell_rad * 1e10) + term1 + term2   # W m-2 sr-1 m-1
            
            #modplot(wavelengths, downwell_rad, upwell_rad, transmission, Ltoa, save_name=str(self.which_landsat))
                
            # calculate observed radiance
            numerator = self.__integrate(RSR_wavelengths, numpy.multiply(Ltoa, RSR))
            denominator = self.__integrate(RSR_wavelengths, RSR)
            
            try:
                modeled_rad = (numerator / denominator) / 1e6  # W m-2 sr-1 um-1
            except ZeroDivisionError:
                print 'ZeroDivisionError, modeled_rad_procssing'
                return -1
                
            return_radiance.append(modeled_rad)
            
            if self.which_landsat == [8,2]: self.which_landsat = [8,1]
            else: break

        os.chdir(current_dir)
        return return_radiance, narr_coor

    def __read_tape6(self, case):
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
        
    def __offset_bilinear_interp(self, array, narr_cor):
        narr_coor = numpy.absolute(narr_cor)   # 1, 2 , 3, 4
        buoy_coors = numpy.absolute(self.buoy_coors)
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
        
    def __read_RSR(self):
        """read in RSR data and return it to the caller.
        """
        wavelength_RSR = []
        RSR = []
        trans_RSR = []
        data = []
        
        if self.which_landsat == [8,1]:
            filename_RSR = './data/shared/L8_B11.rsp'
        if self.which_landsat == [8,2]:
            filename_RSR = './data/shared/L8_B10.rsp'
        if self.which_landsat == [7,1]:
            filename_RSR = './data/shared/L7.rsp'
            
        # read data from file 
        
        with open(filename_RSR, 'r') as f:
            for line in f:    
                data = line.split()
                data = filter(None, data)
                wavelength_RSR.append(float(data[0]))
                RSR.append(float(data[1]))
        
        return RSR, wavelength_RSR
        
    def __find_nearest(self, array,value):
        """Find nearest element to value in array.
        """
        if array != []:
            index = numpy.argmin(numpy.abs(numpy.subtract(array,value)))
            return index
    
    def __calc_temperature_array(self, wavelengths):
        """make array of blackbody radiances.
        """
        Lt= []
    
        for i in wavelengths:
            x = self.__radiance(i)
            Lt.append(x)
            
        return Lt
        
    def __radiance(self, wvlen, units='microns'):
        """calculate blackbody radiance given wavelength (in meters) and temperature.
        """
        
        # define constants
        c = 3e8   # speed of light, m s-1
        h = 6.626e-34	# J*s = kg m2 s-1
        k = 1.38064852e-23 # m2 kg s-2 K-1, boltzmann
        
        c1 = 2 * (c * c) * h   # units = kg m4 s-3
        c2 = (h * c) / k    # (h * c) / k, units = m K    
            
        # calculate radiance
        rad = c1 / (((wvlen**5)) * (math.e**((c2 / (self.skin_temp * wvlen))) - 1))
        
        # UNITS
        # (W / m^2 * sr) * <wavelength unit>
        return rad
        
    def __integrate(self, x, y, method='trap'):
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
    
    def __interpolate_radiance(self, modeled_rad_list, narr_coor):
        """interpolate radiance of narr points to POI
        """
        narr_coor = numpy.absolute(narr_coor)
        buoy_coors = numpy.absolute(self.buoy_coors)
        
        diffs_x = numpy.absolute(numpy.subtract(narr_coor[:, 0], buoy_coors[0]))
        diffs_y = numpy.absolute(numpy.subtract(narr_coor[:, 1], buoy_coors[1]))
        
        total_x = numpy.sum(diffs_x)
        total_y = numpy.sum(diffs_y)
        
        poi_rad_x = 0
        poi_rad_y = 0
        
        for j in range(4):
            poi_rad_x += modeled_rad_list[j] * (diffs_x[j] / total_x)
            poi_rad_y += modeled_rad_list[j] * (diffs_y[j] / total_y)
            
        poi_rad =(poi_rad_x + poi_rad_y) / 2.0
        
        return poi_rad


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
        self.buoy_coors = other.buoy_coors
        self.skin_temp = '%3.3f' % (other.skin_temp)
        self.whichLandsat = other.which_landsat
        self.directory = os.path.join(other.filepath_base, 'data/shared/modtran/')
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
            return -1
            
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
    
        self.date = '%s/%s/%s' % (year, month, day)
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
        case_list = ['']*num_points
        entry = 0
    
        plot_list = [0]*4
        for i in range(num_points):
            latString = '%2.3f' % (lat[NARRindices[i,0], NARRindices[i,1]])
            
            if lon[NARRindices[i,0], NARRindices[i,1]] < 0:
                lonString = '%2.2f' % lon[NARRindices[i,0], NARRindices[i,1]]
            else:
                lonString = '%2.3f' % (360.0 - lon[NARRindices[i,0], NARRindices[i,1]])

            currentPoint = os.path.join(self.scene_dir, 'points/'+latString+'_'+lonString)
            try:
                os.makedirs(currentPoint)
            except OSError:
                pass
            
            if self.geometricHeight[0,i] < 0: gdalt = 0.000 
            else:  gdalt = self.geometricHeight[0,i]
              
            p = pressures[0]
            t = self.temperature[i]
            hgt = self.geometricHeight[i]
            rh = self.relativeHumidity[i]
            
            numLevels = len(p)
            maxLevel = numLevels-1
          
            command = "cat "+self.directory+"tail.txt | sed 's/latitu/"+latString+"/' > "+self.directory+"newTail.txt"
            subprocess.check_call(command, shell=True)
            
            command = "cat "+self.directory+"/newTail.txt | sed 's/longit/"+lonString+"/' > "+self.directory+"/newTail2.txt"
            subprocess.check_call(command, shell=True)
            
            # assign julian day
            dt = datetime.datetime.strptime(self.date, '%Y/%m/%d')
            tt = dt.timetuple()
            JDAY = tt.tm_yday                
            jay = str(JDAY)
            
            if self.whichLandsat == [7,1]:
                start = '10.000'
                stop = '12.987'
                step = '0.063'
            if self.whichLandsat == [8,1]:
                start = '09.000'
                stop = '14.000'
                step = '0.050'
            if self.whichLandsat == [8,2]:
                start = '09.000'
                stop = '14.000'
                step = '0.050'
            else:
                start = '09.000'
                stop = '14.000'
                step = '0.050'
                
            command = "cat "+self.directory+"/newTail2.txt | sed 's/jay/"+jay+"/' > "+self.directory+"/newTail3.txt"
            subprocess.check_call(command, shell=True)
            command = "cat "+self.directory+"/newTail3.txt | sed 's/startp/"+start+"/' > "+self.directory+"/newTail4.txt" 
            subprocess.check_call(command, shell=True)
            command = "cat "+self.directory+"/newTail4.txt | sed 's/stoppp/"+stop+"/' > "+self.directory+"/newTail5.txt" 
            subprocess.check_call(command, shell=True)
            command = "cat "+self.directory+"/newTail5.txt | sed 's/stepp/"+step+"/' > "+self.directory+"/newTail6.txt" 
            subprocess.check_call(command, shell=True)
      
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
                    
            # write to middle file
            filename = os.path.join(self.directory, 'tempLayers.txt')
            
            dewpoint_k = tempTemp - ((100 - tempRelHum) / 5)   #kelvin
            #source: http://climate.envsci.rutgers.edu/pdf/LawrenceRHdewpointBAMS.pdf
            
            
#            #########################  RADIOSONDE CORRECTION   ##################################
#            radiosonde = []
#            rad_file = '../testing/radiosonde_test/4_14_13.rsd'
#            with open(rad_file, 'r') as f:
#                lines = f.readlines()
#                for line in lines[5:]:
#                    if not '99999' in line:
#                        #line = line.replace('99999', '0')
#                        data=line.split()
#                
#                        radiosonde.append([float(data[2])/1000.0, float(data[1])/10.0, float(data[3])/10.0+273.15, float(data[4])/10.0+273.15])
#                    
#            radiosonde = numpy.asarray(radiosonde)
#            #radiosonde = numpy.reshape(radiosonde, (4, numpy.shape(radiosonde)[0]))
#            rad_height = radiosonde[:, 0]
#            rad_press = radiosonde[:, 1]
#            rad_temp = radiosonde[:, 2]
#            rad_dewpoint = radiosonde[:, 3]
#            
#            radiosonde = numpy.array([rad_height, rad_press, rad_temp, rad_dewpoint])
#            
#            sorts_idxs = numpy.argsort(rad_height)
#            
#            find_nearest = lambda a, a0: (numpy.abs(a - a0)).argmin()
#            
#            j = 0
#            indexs = []
#            while len(indexs) < 3:
#                idx = numpy.where(sorts_idxs == j)
#                if rad_press[idx] != 0.0:
#                    if rad_temp[idx] != 0.0:
#                        if rad_height[idx] != 0.0:
#                            if rad_dewpoint[idx] != 0.0:
#                                 indexs.append(idx)
#                j += 1
#            indexs = [x[0][0] for x in indexs]
#            
#            a = find_nearest(tempGeoHeight, rad_height[indexs[-1]])
#            tempGeoHeight = numpy.insert(tempGeoHeight[a:], 0, rad_height[indexs])
#            tempPress = numpy.insert(tempPress[a:], 0, rad_press[indexs])
#            tempTemp = numpy.insert(tempTemp[a:], 0, rad_temp[indexs])
#            dewpoint_k = numpy.insert(dewpoint_k[a:], 0, rad_dewpoint[indexs])
            #######################################################################

            ##################### BUOY CORRECTION #################################
            
#            print tempPress[0], ' ', self.buoy_params[0]
#            print tempTemp[0], ' ', self.buoy_params[1] + 273.15
#            print dewpoint_k[0], ' ', self.buoy_params[2] + 273.15
            
#            tempPress[0] = self.buoy_params[0]
#            tempTemp[0] = self.buoy_params[1] + 273.15
#            dewpoint_k[0] = self.buoy_params[2] + 273.15
#            
#            #######################################################################
#            
#            ################### RADIOSONDE TEST ##################################
#            
#            tempGeoHeight = rad_height
#            tempPress = rad_press
#            tempTemp = rad_temp
#            dewpoint_k = rad_dewpoint
            
            #########################################################################
            with open(filename, 'w') as f:
                for k in range(numpy.shape(tempGeoHeight)[0]):
                    line = '%10.3f%10.3e%10.3e%10.3e%10s%10s%15s\n' % \
                    (tempGeoHeight[k], tempPress[k], tempTemp[k], tempRelHum[k] \
                    ,'0.000E+00','0.000E+00', 'AAH2222222222 2')
                    
                    line = line.replace('e', 'E')
                    f.write(line)
            
            plot_list[i] = (tempGeoHeight, tempPress, tempTemp, dewpoint_k)
            
            
            
            #print plot_list[i]
            # determine number of layers for current ground altitude and insert into head file
            numLayers = numpy.shape(tempGeoHeight)[0]
    
            nml = str(numLayers)
            gdalt = '%1.3f' % (float(str(gdalt)))
                  
            command = "cat "+self.directory+"/head.txt | sed 's/nml/"+nml+"/' > "+self.directory+"/newHead.txt"
            subprocess.call(command, shell=True)
            
            command = "cat "+self.directory+"/newHead.txt | sed 's/gdalt/"+str(gdalt)+"/' > "+self.directory+"/newHead2.txt"
            subprocess.call(command, shell=True)

            command = "cat "+self.directory+"/newHead2.txt | sed 's/tmp____/"+str(self.skin_temp)+"/' > "+self.directory+"/newHead3.txt"
            subprocess.call(command, shell=True)
                  
            command = "cat "+self.directory+"/newHead3.txt | sed 's/albe/1.00/' > "+self.directory+"/newHead4.txt"
            subprocess.call(command, shell=True)
                  
            headFile = os.path.join(self.directory,'newHead4.txt')
            tailFile = os.path.join(self.directory, 'newTail6.txt')
            tempLayers = os.path.join(self.directory, 'tempLayers.txt')
            
            newFile = os.path.join(currentPoint, 'tape5')
            command = ' '.join(['cat', headFile, tempLayers, tailFile, '>', newFile])
            subprocess.check_call(command, shell=True)
            
            newfiles = ['newHead.txt','newHead1.txt','newHead2.txt','newHead3.txt','newHead4.txt'
            'newTail.txt','newTail1.txt','newTail2.txt','newTail3.txt','newTail4.txt' ,'newTail5.txt' ,'newTail6.txt']
            try:
                for asdf in newfiles:
                    os.remove(os.path.join(self.directory, asdf))
            except OSError:
                pass
            
            case_list[entry] = currentPoint
            entry += 1


            numpy.savetxt(os.path.join(self.scene_dir,'atmo_interp_%s.txt'%(i)), plot_list[i])
    
        # write commandList and caseList to file
        case_list_file = os.path.join(self.scene_dir,'points/caseList')
    
        with open(case_list_file, 'w') as f:
            for i in range(len(case_list)):
                f.write(case_list[i])
                f.write('\n')


        #import test_plot
        #test_plot.plot_atmo(plot_list, radiosonde, show=True)

        return case_list
