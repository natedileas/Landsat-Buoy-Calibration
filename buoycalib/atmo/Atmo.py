
class Atmo(object):

    def __init__(self):
        # modeled radiance processing
        if self.satelite == 'LC8':   # L8
            rsr_files = [[10, os.path.join(settings.DATA_BASE, 'misc', 'L8_B10.rsp')], \
                        [11, os.path.join(settings.DATA_BASE, 'misc', 'L8_B11.rsp')]]
            img_files = [[10, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_10'])], \
                        [11, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_11'])]]
        elif self.satelite == 'LE7':   # L7
            rsr_files = [[6, os.path.join(settings.DATA_BASE, 'misc', 'L7_B6_2.rsp')]]
            img_files = [[6, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_6_VCID_2'])]]
        elif self.satelite == 'LT5':   # L5
            rsr_files = [[6, os.path.join(settings.DATA_BASE, 'misc', 'L5_B6.rsp')]]
            img_files = [[6, os.path.join(self.scene_dir, self.metadata['FILE_NAME_BAND_6'])]]

        modtran_data = self.run_modtran()
        ltoa = mod_proc.calc_ltoa(self, modtran_data)

        for band, rsr_file in rsr_files:
            logging.info('Modeled Radiance Processing: Band %s' % (band))
            self.modeled_radiance.append(mod_proc.calc_radiance(modtran_data[2], ltoa, rsr_file))
                    
        for band, img_file in img_files:
            logging.info('Image Radiance Processing: Band %s' % (band))
            self.image_radiance.append(img_proc.calc_radiance(self, img_file, band))
  
    def download_mod_data(self):
        """
        Download atmospheric data.

        Args: None

        Returns: None
        """

        logging.info('Downloading atmospheric data.')

        if self.atmo_src == 'narr':
            narr_data.download(self)
        elif self.atmo_src == 'merra':
            merra_data.download(self)
            
    def run_modtran(self):
        """
        Make tape5, run modtran and parse tape7.scn for this instance.

        Args: None

        Returns: 
            Relevant Modtran Outputs: spectral, units=[] TODO
                upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect
        """
        logging.info('Generating tape5 files.')
        # read in narr data and generate tape5 files and caseList
        point_dir, self.narr_coor = mod_proc.make_tape5s(self)
        
        logging.info('Running modtran.')
        mod_proc.run_modtran(point_dir)
        
        logging.info('Parsing modtran output.')
        upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect = mod_proc.parse_tape6(point_dir)
        return upwell_rad, downwell_rad, wavelengths, transmission, gnd_reflect