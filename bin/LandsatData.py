import datetime
import urllib2
import urllib
import os
import math
import shutil
import time
import subprocess
import logging
import sys
import httplib

class LandsatData(object):
    """ Download Landsat Images and Metadata.
    
    Attributes:
        filepath_base: parent directory, base of all other paths.
        save_dir: directory to save landsat images in.
        logger: logger object for non-verbose output.
        scene_id: scene_id to download, string
        whichsat: which landsat version, (7 or 8), int
        date: date on which the image was captured
        scene_coors: WRS2 path and row
        cloud_cover: max acceptable cloud cover, in percent.
    
    Methods:
        __init__(self, other): initialize the attributes using a CalibrationController object
        start_download(self): download landsat data and parse metadata.
        read_metadata(self): read and parse landsat metadata, return dict
        
    Utilizes Subclass DownloadLandsatScene(object).
    """
    def __init__(self, other):
        """ initialize the attributes using a CalibrationController object. """
        self.filepath_base = other.filepath_base
        self.save_dir = os.path.join(self.filepath_base, other.image_file_extension)
        
        log_file = os.path.join(self.filepath_base, 'logs/CalibrationController.log')
        logging.basicConfig(filename=log_file, filemode='w', level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.scene_id = None   #fix error in start_download
        
        if other._scene_id:
            self.scene_id = other._scene_id
            
            if other._scene_id[0:3] == 'LC8':
                self.whichsat = 8
            else:
                self.whichsat = 7
            self.date = datetime.datetime.strptime(other._scene_id[9:16], '%Y%j')
            self.scene_coors = other._scene_id[3:9]

        else:
            if not other.satelite or not other.julian_date:
                if not other.year or not other.WRS2_path:
                    self.logger.error('.__init__: Either scene ID or equivalent \
                        arguments are required.')
                    sys.exit(-1)
            else:
                self.whichsat =  other.satelite
                self.scene_coors = other.WRS2_path + other.WRS2_row
                self.date = datetime.datetime.strptime(other.year+other.julian_date, '%Y%j').timetuple()
        
        if other.cloud_cover:
            self.cloud_cover = other.cloud_cover
        else:
            self.cloud_cover = 100

    def start_download(self):
        """ download landsat data and parse metadata. """
        usgs = os.path.join(self.filepath_base, 'logs/usgs_login.txt')
        args = [usgs, self.save_dir, self.scene_coors, self.date, self.whichsat, self.cloud_cover]
                
        if self.scene_id:
            args.append(self.scene_id)

        dls = DownloadLandsatScene()
        landsat_id = dls.main(*args)

        if landsat_id == -1:
            self.logger.warning('.start_download: landsat_id was -1')
            return -1

        if self.scene_id:
            if self.scene_id != landsat_id:
                self.logger.warning('.start_download: scene_id and landsat_id \
                                    do not match')
            
            self.scene_id = landsat_id
        else:
            self.scene_id = landsat_id
            
        metadata = self.read_metadata()
        
        if metadata == -1:
            self.logger.warning('.start_download: data not downlaoded or unzipped correctly')
            return -1

        return self.scene_id, metadata

    def read_metadata(self):
        """ read and parse landsat metadata.

        Should only be called on a valid LandsatData instance.

        Args:
            imageBase: used for the filename of the metadata file, string

        Returns:
            meta_data: dictionary of metadata values, keyed by their names

        Raises:
            IndexError: Error in reading metadata
            ValueError: Attempt to float() NaN: handled
        """

        filename = os.path.join(self.save_dir, '%s_MTL.txt' %
                                ( self.scene_id))
        info = []*2
        chars = ['\n', '"', '\'']    # characters to remove from lines
        desc = []
        data = []

        # open file, split, and save to two lists
        try:
            with open(filename, 'r') as f:
                for line in f:
                    try:
                        info = line.split(' = ')
                        info[1] = info[1].translate(None, ''.join(chars))
                        desc.append(info[0])
                        data.append(float(info[1]))
                    except IndexError:
                        break
                    except ValueError:
                        data.append(info[1])
        except IOError:
            return -1

        desc = [x.strip(' ') for x in desc]   # remove empty entries in list
        metadata = dict(zip(desc, data))   # create dictionary

        return metadata


class DownloadLandsatScene(object):
    """ Control download process, return id of downloaded scenes. 
        
    Attributes:
        logger: logging object for non-verbose output
        
    Methods:
        main: use this class.
        get_status: find out what the status of the file is.
        connect_earthexplorer_no_proxy: connect to earth explorer.
        sizeof_fmt: calc size fo file in bytes to MB
        downloadChunks: actually download file.
        cycle_day: find day when landsat passes over.
        next_overpass: find next day when landsat passes over.
        unzipimage: exactly what it sounds like.
        check_cloud_limit: check cloud limit using the helper function.
        read_cloudcover_in_metadata: read cloud percentage in metadata.
    """
    def main(self, usgs=None, output=None, scene=None, date=None, bird=None, clouds=None, scene_id=None):
        
        logging.basicConfig(filename='CalibrationController.log',
                            filemode='w', level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        output_dir = str(output)[:-22]

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # read password files
        try:
            with open(usgs, 'r') as f:
                account, passwd = f.readline().split(' ')
            passwd = passwd.replace('\n', '')
            usgs = {'account': account, 'passwd': passwd}
        except:
            self.logger.warning('main: error with usgs password file')
            sys.exit(-1)

        path = scene[0:3]
        row = scene[3:6]
        
        prefix = ''

        if bird == 8:
            prefix = 'LC8'
            repert = '4923'
            stations = ['LGN']
        if bird == 7:
            prefix = 'LE7'
            repert = '3373'
            stations = ['EDC', 'SGS', 'AGS', 'ASN', 'SG1']
            
        #assign dates
        sixteen_days = datetime.timedelta(16)
        search_date = self.__next_overpass(date, int(path), prefix)
        date = datetime.datetime.strftime(search_date, '%Y%j')
            
        scene_ids = [scene_id]
        
        
        for station in stations:
            for version in ['00', '01', '02', '03', '04']:
                scene_ids.append(prefix + scene + date + station + version)
                   
        scene_ids = filter(None, scene_ids)
        
        # connect to earthexplorer
        self.__connect_earthexplorer_no_proxy(usgs)
        
        for scene_id in scene_ids:
            url = 'http://earthexplorer.usgs.gov/download/%s/%s/STANDARD/EE' % (repert, scene_id)
            
            zip_check = 1   # to hold return values
            down_check = 1
            
            status = self.__get_status(scene_id, output_dir, url)
                    
            if status == 1:
                self.logger.info('main: Product %s already downloaded and unzipped ', scene_id)
                down_check = 0
                zip_check = 0
                return scene_id
            elif status == 2:
                self.logger.info('main: product %s already downloaded ', scene_id)
                down_check = 0
                zip_check = self.__unzipimage(scene_id, output_dir)
            elif status == 3:
                self.logger.info('main: product %s not already downloaded ', scene_id)
                down_check = self.__downloadChunks(url, str(output_dir), scene_id+'.tgz')
                zip_check = self.__unzipimage(scene_id, output_dir)
            elif status == 4:
                self.logger.info('main: product %s not already downloaded, other error issues ', scene_id)
                down_check = 1
                zip_check = 1
                    
            if zip_check == 0 and down_check == 0 and clouds is not None:
                check = self.__check_cloud_limit(os.path.join(output_dir, scene_id), clouds)
                return scene_id
            elif zip_check == 0 and down_check == 0 and clouds is None:
                return scene_id
            
        return -1

        
    def __get_status(self, scene_id, output_dir, url):
        """ get status of file. """
        tgzfile = os.path.join(output_dir, scene_id + '.tgz')
        unzip_dir = os.path.join(output_dir, scene_id)
        unzipdfile = os.path.join(unzip_dir, scene_id + '_B10.TIF')
    
        if os.path.exists(unzipdfile):   #downloaded and unzipped
            return 1
        elif os.path.isfile(tgzfile):    #downloaded, not unzipped
            return 2
        else:    #not downloaded
            try:
                data = urllib2.urlopen(url)
            except urllib2.HTTPError, e:
                if e.code == 500:
                    self.logger.error('get_status:  file does not exist!')
                else:
                    self.logger.error('get_status: HTTP Error: %s %s' % (e.code, e.reason))
                return 4
            except urllib2.URLError, e:
                self.logger.error('URL Error: %s %s' % (e.reason, url))
                return 4
            lines = data.read()

            if (data.info().gettype() == 'text/html'):
                self.logger.error("Error : the file is in html format")
                return 4

            if lines.find('Download Not Found') > 0:
                self.logger.error("Error: Download Not Found!", url)
                return 4

            total_size = int(data.info().getheader('Content-Length').strip())

            if (total_size < 50000):
                self.logger.error("Error: The file is too small to be a Landsat Image", url)
                return 4
                
            return 3
    
    def __connect_earthexplorer_no_proxy(self, usgs):
        """ connect to earthexplorer without a proxy. """
        try:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
            urllib2.install_opener(opener)
            params = urllib.urlencode(dict(username=usgs['account'], password=usgs['passwd']))
            f = opener.open('https://ers.cr.usgs.gov/login/', params)   # ND changed 7/7/15
            data = f.read()
            f.close()
            if data.find('You must sign in as a registered user to download data or place orders for USGS EROS products') > 0:
                print 'Authentification failed'
                sys.exit(-1)
            return
        except urllib2.HTTPError, e:
            if e.code == 500:
                self.logger.error('download_chunks:  file does not exist!')
            else:
                self.logger.error('download_chunks: HTTP Error: %s %s' % (e.code, e.reason))
            return -1
        except urllib2.URLError, e:
            self.logger.error('URL Error: %s %s' % (e.reason, url))
            return -1
            
        except httplib.BadStatusLine:
            pass

    def __sizeof_fmt(self, num):
        for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return '%3.1f %s' % (num, x)
            num /= 1024.0

    def __downloadChunks(self, url, rep, nom_fic):
        """ Downloads large files in pieces.
        inspired by http://josh.gourneau.com
        """
        try:
            downloaded = 0
            chunk_size = 1024 * 1024 * 8

            out_file = os.path.join(rep, nom_fic)

            data = urllib2.urlopen(url)   # ND reopen url, previous stuff read entire file, caused error

            total_size = int(data.info().getheader('Content-Length').strip())
            total_size_fmt = self.__sizeof_fmt(total_size)

            with open(out_file, 'wb') as f:
                start = time.clock()
                self.logger.info(  'download_chunks:  Downloading %s (%s)' % (nom_fic, total_size_fmt))
                while True:
                    chunk = data.read(chunk_size)

                    if not chunk:
                        break

                    downloaded += len(chunk)

                    f.write(chunk)

            return 0

        except urllib2.HTTPError, e:
            if e.code == 500:
                self.logger.error('download_chunks:  file does not exist!')
            else:
                self.logger.error('download_chunks: HTTP Error: %s %s' % (e.code, e.reason))
            return -1
        except urllib2.URLError, e:
            self.logger.error('URL Error: %s %s' % (e.reason, url))
            return -1

        return rep, nom_fic

    def __cycle_day(self, path):
        """ provides the day in cycle given the path number. """
        cycle_day_path1 = 5
        cycle_day_increment = 7
        nb_days_after_day1 = cycle_day_path1 + cycle_day_increment * (path - 1)

        cycle_day_path = math.fmod(nb_days_after_day1, 16)
        if path >= 98:   # change date line
            cycle_day_path += 1
            
        return(cycle_day_path)

    def __next_overpass(self, date1, path, sat):
        """ Provides the next overpass for path after date1. """
        date0 = 0

        if sat == 'LE7':
            date0 = datetime.datetime(1999, 1, 11)
        elif sat == 'LC8':
            date0 =  datetime.datetime(2013, 5, 1)
        
        next_day = math.fmod((date1-date0).days - self.__cycle_day(path) + 1, 16)
        if next_day != 0:
            date_overpass = date1 + datetime.timedelta(16 - next_day)
        else:
            date_overpass = date1
        return(date_overpass)

    def __unzipimage(self, scene_id, outputdir):
        """ Unzip tgz file. """
        tgz_file = os.path.join(outputdir, scene_id + '.tgz')
        out_dir = os.path.join(outputdir, scene_id)
        
        if os.path.exists(tgz_file):
            try:
                os.mkdir(out_dir)
                subprocess.check_call('tar zxvf ' + tgz_file + ' -C ' + out_dir + ' >/dev/null', shell=True)
                os.remove(tgz_file)
            except OSError:
                self.logger.error('unzipimage: OSError')
                return -1
        else: 
            self.logger.error('unzipimage: File does not exist.')
            return -1
            
        return 0

    def __read_cloudcover_in_metadata(self, image_path):
        """ Read cloud cover from image metadata. """
        output_list = []
        fields = ['CLOUD_COVER']
        cloud_cover = 0
        imagename = os.path.basename(os.path.normpath(image_path))
        metadatafile = os.path.join(image_path, imagename + '_MTL.txt')
        metadata = open(metadatafile, 'r')

        for line in metadata:
            line = line.replace('\r', '')
            for f in fields:
                if line.find(f) >= 0:
                    lineval = line[line.find('= ') + 2:]
                    cloud_cover = lineval.replace('\n', '')
        return float(cloud_cover)

    def __check_cloud_limit(self, imagepath, limit):
        """ check cloud limit provided by user. """
        cloudcover = self.__read_cloudcover_in_metadata(imagepath)
        if cloudcover > limit:
            shutil.rmtree(imagepath)
            self.logger.info('check_cloud_limit: Image exceeds cloud cover value of " + str(cloudcover) + " defined by the user!')
            return -1

        return 0
