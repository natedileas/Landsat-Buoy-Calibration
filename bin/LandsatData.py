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


class LandsatData(object):
    def __init__(self, other):
        """initializer of LandsatData.
        """
        logging.basicConfig(filename='CalibrationController.log',
                            filemode='w', level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        if other._scene_id:
            self.scene_id = other._scene_id
            self.whichsat = other._scene_id[0:3]
            self.year = other._scene_id[9:13]
            self.julian_day = int(other._scene_id[13:16])
            self.scene_coors = other._scene_id[3:9]

        else:
            if not other.satelite or not other.julian_date:
                if not other.year or not other.WRS2_path:
                    self.logger.error('.__init__: Either scene ID or equivalent \
                        arguments are required.')
                    sys.exit(-1)
            else:
                self.julian_day = int(other.julian_date)
                self.whichsat = other.satelite
                self.year = other.year
                self.scene_coors = [other.WRS2_path, other.WRS2_row]

        if other.cloud_cover:
            self.cloud_cover = other.cloud_cover
        else:
            self.cloud_cover = 100

        self.save_dir = os.path.join(other.filepath_base, 'data/landsat')

    def start_download(self):
        """download landsat data and parse metadata.
        """
        month = str(datetime.datetime.strptime(str(self.julian_day),
                    '%j'))[5:7]
        day = str(datetime.datetime.strptime(str(self.julian_day), '%j'))[8:10]
        date = self.year + month + day

        start_date = str(int(date)-1)
        end_date = str(int(date)+1)

        args = ['scene', 'logs/usgs_login.txt', self.save_dir,
                self.scene_coors, start_date, end_date, self.whichsat,
                self.cloud_cover]

        dls = DownloadLandsatScene()
        landsat_id = dls.main(*args)

        if landsat_id == []:
            self.logger.warning('.start_download: nothing was downloaded')
            return -1

        if self.scene_id != landsat_id[0]:
            self.logger.warning('.start_download: scene_id and landsat_id \
                                do not match')
            return -1

        metadata = LandsatData.read_metadata(self)

        return landsat_id[0], metadata

    def read_metadata(self):
        """read and parse landsat metadata.

        Should only be called on a valid LandsatData instance.

        Args:
            imageBase: used for the filename of the metadata file, string

        Returns:
            meta_data: dictionary of metadata values, keyed by their names

        Raises:
            IndexError: Error in reading metadata
            ValueError: Attempt to float() NaN: handled
        """

        filename = os.path.join(self.save_dir, '%s/%s_MTL.txt' %
                                (self.scene_id, self.scene_id))
        info = []*2
        chars = ['\n', '"']    # characters to remove from lines
        desc = []
        data = []

        # open file, split, and save to two lists
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

        desc = [x.strip(' ') for x in desc]   # remove empty entries in list
        metadata = dict(zip(desc, data))   # create dictionary

        return metadata


class DownloadLandsatScene(object):
    def main(self, option=None, usgs=None, output=None, scene=None,
             start_date=None, end_date=None, bird=None, clouds=None):
        """Control download process, return id(s) of downloaded scenes.
        """
        logging.basicConfig(filename='CalibrationController.log',
                            filemode='w', level=logging.INFO)
        logger = logging.getLogger(__name__)
        downloaded_ids = []

        output_dir = '%s' % (output)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # read password files
        try:
            with open(usgs, 'r') as f:
                account, passwd = f.readline().split(' ')
            passwd = passwd.replace('\n', '')
            usgs = {'account': account, 'passwd': passwd}
        except:
            logger.warning('main: error with usgs password file')
            sys.exit(-1)

        path = scene[0:3]
        row = scene[3:6]

        year_start = int(start_date[0:4])
        month_start = int(start_date[4:6])
        day_start = int(start_date[6:8])

        date_start = datetime.datetime(year_start, month_start, day_start)

        if end_date is not None:
            year_end = int(end_date[0:4])
            month_end = int(end_date[4:6])
            day_end = int(end_date[6:8])
            date_end = datetime.datetime(year_end, month_end, day_end)
        else:
            date_end = datetime.datetime.now()

        # connect to earthexplorer
        DownloadLandsatScene.connect_earthexplorer_no_proxy(self, usgs)

        if bird.startswith('LC8'):
            repert = '4923'
            stations = ['LGN']
        if bird.startswith('LE7'):
            repert = '3373'
            stations = ['EDC', 'SGS', 'AGS', 'ASN', 'SG1']

        check = 1

        curr_date = DownloadLandsatScene.next_overpass(self, date_start,
                                                       int(path), bird)

        while (curr_date < date_end) and check == 1:
            date_asc = curr_date.strftime('%Y%j')
            notfound = False

            logger.info('main: Searching for images: ' + date_asc + '...')

            curr_date = curr_date+datetime.timedelta(16)

            for station in stations:
                for version in ['00', '01', '02']:
                    scene_id = bird + scene + date_asc + station + version
                    tgzfile = os.path.join(output_dir, scene_id + '.tgz')
                    unzipdfile = os.path.join(output_dir, scene_id)

                    url = 'http://earthexplorer.usgs.gov/download/%s/%s/STANDARD/EE' % (repert, scene_id)

                    if os.path.exists(unzipdfile):
                        logger.info('main: Product %s already downloaded and unzipped', scene_id)
                        downloaded_ids.append(scene_id)
                        check = 0

                    elif os.path.isfile(tgzfile):
                        logger.info('main: product %s already downloaded', scene_id)

                        p = DownloadLandsatScene.unzipimage(self, scene_id, output_dir)
                        if p == 1 and clouds is not None:
                            check = DownloadLandsatScene.check_cloud_limit(self, unzipdfile, clouds)
                            if check == 0:
                                downloaded_ids.append(scene_id)
                        else:
                            downloaded_ids.append(scene_id)

                    else:
                        try:
                            DownloadLandsatScene.downloadChunks(self, url, str(output_dir), scene_id+'.tgz', logger)
                        except KeyboardInterrupt:
                            logger.warning('main: Product %s not found', scene_id)
                            notfound = True
                        if notfound is False:
                            p = DownloadLandsatScene.unzipimage(self, scene_id, output_dir)
                            if p == 1 and clouds is not None:
                                check = DownloadLandsatScene.check_cloud_limit(self, unzipdfile, clouds)
                                if check == 0:
                                    downloaded_ids.append(scene_id)
                            else:
                                downloaded_ids.append(scene_id)
                        else:
                            downloaded_ids.append(scene_id)
        return downloaded_ids

    def connect_earthexplorer_no_proxy(self, usgs):
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
                pass   # file does not exist
            else:
                print 'HTTP Error:', e.code, e.reason
                pass
            return False
        except urllib2.URLError, e:
            print 'URL Error:', e.code, e.reason
            return False

    def sizeof_fmt(self, num):
        for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if num < 1024.0:
                return '%3.1f %s' % (num, x)
            num /= 1024.0

    def downloadChunks(self, url, rep, nom_fic, logger):
        """ Downloads large files in pieces.
        inspired by http://josh.gourneau.com
        """

        try:
            data = urllib2.urlopen(url)
            lines = data.read()

            if (data.info().gettype() == 'text/html'):
                print "Error : the file is in html format"

            if lines.find('Download Not Found') > 0:
                raise TypeError

            total_size = int(data.info().getheader('Content-Length').strip())

            if (total_size < 50000):
                print "Error: The file is too small to be a Landsat Image", url

            total_size_fmt = DownloadLandsatScene.sizeof_fmt(self, total_size)

            downloaded = 0
            chunk_size = 1024 * 1024 * 8

            out_file = os.path.join(rep, nom_fic)

            data = urllib2.urlopen(url)   # ND reopen url, previous stuff read entire file, caused error

            with open(out_file, 'wb') as f:
                start = time.clock()
                logger.info('download_chunks:  Downloading %s (%s)' % (nom_fic, total_size_fmt))
                while True:
                    chunk = data.read(chunk_size)
                    if not chunk:
                        break

                    downloaded += len(chunk)
                    done = int(50 * downloaded / total_size)
                    size_dwnld = DownloadLandsatScene.sizeof_fmt(self, (downloaded // (time.clock() - start)) / 8)
                    f.write(chunk)

        except urllib2.HTTPError, e:
            if e.code == 500:
                pass   # file does not exist
            else:
                print "HTTP Error:", e.code, url
            return False
        except urllib2.URLError, e:
            print "URL Error:", e.reason, url
            return False

        return rep, nom_fic

    def cycle_day(self, path):
        """provides the day in cycle given the path number.
        """
        cycle_day_path1 = 5
        cycle_day_increment = 7
        nb_days_after_day1 = cycle_day_path1 + cycle_day_increment * (path - 1)

        cycle_day_path = math.fmod(nb_days_after_day1, 16)
        if path >= 98:   # change date line
            cycle_day_path += 1
        return(cycle_day_path)

    def next_overpass(self, date1, path, sat):
        """Provides the next overpass for path after date1.
        """
        date0_L5 = datetime.datetime(1985, 5, 4)
        date0_L7 = datetime.datetime(1999, 1, 11)
        date0_L8 = datetime.datetime(2013, 5, 1)

        if sat == 'LT5':
            date0 = date0_L5
        elif sat == 'LE7':
            date0 = date0_L7
        elif sat == 'LC8':
            date0 = date0_L8
        next_day = math.fmod((date1-date0).days - DownloadLandsatScene.cycle_day(self, path) + 1, 16)
        if next_day != 0:
            date_overpass = date1 + datetime.timedelta(16 - next_day)
        else:
            date_overpass = date1
        return(date_overpass)

    def unzipimage(self, tgzfile, outputdir):
        """Unzip tgz file.
        """
        success = 0
        if os.path.exists(outputdir + '/' + tgzfile + '.tgz'):
            try:
                if sys.platform.startswith('linux'):
                    subprocess.call('mkdir ' + outputdir + '/' + tgzfile, shell=True)   # Unix
                    subprocess.call('tar zxvf ' + outputdir + '/' + tgzfile + '.tgz -C ' + outputdir+'/'+tgzfile+' >/dev/null', shell=True)   # Unix
                elif sys.platform.startswith('win'):
                    subprocess.call('tartool ' + outputdir + '/' + tgzfile + '.tgz ' + outputdir + '/' + tgzfile, shell=True)  # W32
                success = 1
            except TypeError:
                print 'Failed to unzip %s' % tgzfile
            os.remove(outputdir + '/' + tgzfile + '.tgz')
        return success

    def read_cloudcover_in_metadata(self, image_path):
        """Read image metadata.
        """
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

    def check_cloud_limit(self, imagepath, limit):
        """check cloud limit provided by user.
        """
        removed = 0
        cloudcover = DownloadLandsatScene.read_cloudcover_in_metadata(self, imagepath)
        if cloudcover > limit:
            shutil.rmtree(imagepath)
            print "Image was removed because the cloud cover value of " + str(cloudcover) + " exceeded the limit defined by the user!"
            removed = 1
        return removed
