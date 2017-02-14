import ..settings

class Buoy(object):
    def __init__(self, bid):

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


    def download(self):
        # download data
        pass


    def load(self):
        # load chosen dataset
        pass


    def calculate(self):
        # calculate skin temperature
        pass
