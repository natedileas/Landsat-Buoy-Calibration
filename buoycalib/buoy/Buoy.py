    

class Buoy(object):

    # buoy and related attributes
        self._buoy_id = None
        self.buoy_location = None  # [lat, lon]
        self.skin_temp = None   # calculated from buoy dataset
        self.buoy_press = None
        self.buoy_airtemp = None
        self.buoy_dewpnt = None
        
    @property
    def buoy_id(self):
        return self._buoy_id

    @buoy_id.setter
    def buoy_id(self, new_id):
        """ Check that the buoy id is valid before assignment. """
        
        match = re.match('^\d{5}$', new_id)

        if match:   # if it matches the pattern
            self._buoy_id = match.group()
        else:
            self._buoy_id = new_id
            logging.warning('.buoy_id: @buoy_id.setter: %s is the wrong format' % new_id)

    def calculate_buoy_information(self):
        """
        Pick buoy dataset, download, and calculate skin_temp.

        Args: None

        Returns: None
        """
        datasets, buoy_coors, depths = buoy_data.find_datasets(self)
        
        filename = os.path.join(settings.NOAA_DIR, 'buoy_height.txt')
        buoys, heights = numpy.genfromtxt(filename, skip_header=7, usecols=(0,1), unpack=True)
        buoy_heights = dict(zip(buoys, heights))
        
        year = self.date.strftime('%Y')
        mon_str = self.date.strftime('%b')
        month = self.date.strftime('%m')
        hour = self.scenedatetime.hour
        
        if self.buoy_id:
            if self.buoy_id in datasets:
                idx = datasets.index(self.buoy_id)
                datasets = [datasets[idx]]
                depths = [depths[idx]]
            else:
                logging.error('User Requested Buoy is not in scene.')
                sys.exit(-1)
        
        for idx, buoy in enumerate(datasets):
            if self.date.year < 2016:
                url = settings.NOAA_URLS[0] % (buoy, year)
            else:
                url = settings.NOAA_URLS[1] % (mon_str, buoy, int(month))
            
            zipped_file = os.path.join(settings.NOAA_DIR, os.path.basename(url))
            unzipped_file = zipped_file.replace('.gz', '')
            
            try:
                if not buoy_data.get_buoy_data(zipped_file, url): 
                    continue

                data, headers = buoy_data.open_buoy_data(self, unzipped_file)
                self.skin_temp = buoy_data.find_skin_temp(hour, data, headers, depths[idx])
                
                self.buoy_id = buoy
                self.buoy_location = buoy_coors[idx]
                
                try:
                    self.buoy_height = buoy_heights[self.buoy_id]
                except KeyError:
                    self.buoy_height = 0.0
                
                try:
                    self.buoy_press = data[hour, headers['BAR']]
                except KeyError:
                    self.buoy_press = data[hour, headers['PRES']]

                self.buoy_airtemp = data[hour, headers['ATMP']]
                self.buoy_dewpnt = data[hour, headers['DEWP']]
                self.buoy_rh = atmo_data.calc_rh(self.buoy_airtemp, self.buoy_dewpnt)

                logging.info('Used buoy: %s'% buoy)
                break
                
            except buoy_data.BuoyDataError as e:
                logging.warning('Dataset %s didn\'t work (%s). Trying a new one' % (buoy, e))
                continue
                
        if not self.buoy_location:
            logging.error('User Requested Buoy Did not work.')
            sys.exit(-1)
