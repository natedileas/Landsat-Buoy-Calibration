
class LandsatProduct(class):
	# image radiance and related attributes
    self.image_radiance = []
    self.metadata = None    # landsat metadata
    self.scenedatetime = None 
    
    # attributes that make up the lansat id
    self.satelite = None
    self.wrs2 = None
    self.date = None
    self.station = None
    self.version = None
        
	self.scene_dir = os.path.normpath(os.path.join(settings.LANDSAT_DIR, LID))
        
    if not os.path.exists(self.scene_dir):
        os.makedirs(self.scene_dir)

	@property
    def scene_id(self):
        """ Stored internally as different parts. """
        
        lid = '%s%s%s%s%s' % (self.satelite, self.wrs2, self.date.strftime('%Y%j'), \
        self.station, self.version)
        return lid

    @scene_id.setter
    def scene_id(self, new_id):
        """ Check that the landsat id is valid before assignment. """
        
        match = re.match('^L(C8|E7|T5)\d{13}(LGN|EDC|SGS|AGS|ASN|SG1|GNC|ASA|KIR|MOR|KHC|PAC|KIS|CHM|LGS|MGR|COA|MPS)0[0-5]$', new_id)

        if match:
            self.satelite = new_id[0:3]
            self.wrs2 = new_id[3:9]
            self.date = datetime.datetime.strptime(new_id[9:16], '%Y%j')
            self.station = new_id[16:19]
            self.version = new_id[-2:]

        else:
            logging.error('scene_id.setter: %s is the wrong format' % new_id)
            sys.exit(-1)

	def download_img_data(self):
        """
        Download landsat product and parse metadata.

        Args: None

        Returns: None
        """
        
        logging.info('.download_img_data: Dealing with Landsat Data')
    
        # download landsat image data and assign returns
        downloaded_LID = landsat_data.download(self)

        self.scene_id = downloaded_LID

        # read in landsat metadata
        self.metadata = landsat_data.read_metadata(self)
        
        date = self.metadata['DATE_ACQUIRED']
        time = self.metadata['SCENE_CENTER_TIME'].replace('"', '')[0:7]
        self.scenedatetime = datetime.datetime.strptime(date+' '+time, '%Y-%m-%d %H:%M:%S')