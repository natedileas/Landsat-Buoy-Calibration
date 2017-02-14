import narr
import merra

class Atmo(object):

    def __init__(self, source):
        self.atmo_src = source
        self.source = narr if source == 'narr' else merra

    def download(self):
        """
        Download atmospheric data.
        """
        logging.info('Downloading atmospheric data.')

        self.source.download(self)

        return self
            

    def load(self):
        # laod in data
        return self

    def process(self):
        modtran_data = self.run_modtran()
        ltoa = mod_proc.calc_ltoa(self, modtran_data)
        for band, rsr_file in rsr_files:
            logging.info('Modeled Radiance Processing: Band %s' % (band))
            self.modeled_radiance.append(mod_proc.calc_radiance(modtran_data[2], ltoa, rsr_file))

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