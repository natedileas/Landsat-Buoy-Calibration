import urllib2
import urllib
import os
import math
import shutil
import subprocess
import sys
import httplib
import datetime

def download(cc):
    """ download landsat data and parse metadata. """
    login_info = os.path.join(cc.filepath_base, 'data/shared/usgs_login.txt')
    
    dls = DownloadLandsatScene()
    downloaded_scene_id = dls.main(cc, login_info, cc.scene_dir)

    if downloaded_scene_id == -1:
        print '.start_download: landsat_id was -1'
        return -1

    if cc.scene_id != downloaded_scene_id:
        print 'WARNING .start_download: scene_id and landsat_id do not match'
        
        cc.scene_id = downloaded_scene_id
        
    metadata = read_metadata(cc.scene_dir, downloaded_scene_id)
    
    if metadata == -1:
        print 'WARNING .start_download: data not downloaded or unzipped correctly, metadata is null'
        return -1

    return downloaded_scene_id, metadata

def read_metadata(save_dir, dsid):
    filename = os.path.join(save_dir, '%s_MTL.txt' % dsid)
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
    def main(self, cc, usgs, output_dir):

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # read password files
        try:
            with open(usgs, 'r') as f:
                account, passwd = f.readline().split(' ')
            passwd = passwd.replace('\n', '')
            usgs = {'account': account, 'passwd': passwd}
        except:
            print 'ERROR: usgs password file problem'
            sys.exit(-1)

        path = cc.wrs2[0:3]
        row = cc.wrs2[0:3]
        clouds = cc.cloud_cover
        
        prefix = ''

        if cc.satelite == 'LC8':
            prefix = 'LC8'
            repert = '4923'
            stations = ['LGN']
        if cc.satelite == 'LE7':
            prefix = 'LE7'
            repert = '3373'
            stations = ['EDC', 'SGS', 'AGS', 'ASN', 'SG1']
            
        #assign dates
        sixteen_days = datetime.timedelta(16)
        search_date = self.__next_overpass(cc.date, int(path), prefix)
        date = datetime.datetime.strftime(search_date, '%Y%j')
            
        scene_ids = [cc.scene_id]
        
        for station in stations:
            for version in ['00', '01', '02', '03', '04']:
                scene_ids.append(prefix + path + row + date + station + version)
                   
        scene_ids = filter(None, scene_ids)
        
        for scene_id in scene_ids:
            url = 'http://earthexplorer.usgs.gov/download/%s/%s/STANDARD/EE' % (repert, scene_id)
            
            zip_check = 1   # to hold return values
            down_check = 1
            
            status = self.__get_status(scene_id, output_dir, url)
                    
            if status == 1:
                print 'main: Product %s already downloaded and unzipped ' % scene_id
                down_check = 0
                zip_check = 0
                return scene_id
            elif status == 2:
                print 'main: product %s already downloaded ' % scene_id
                down_check = 0
                zip_check = self.__unzipimage(scene_id, output_dir)
            elif status == 3:
                print 'main: product %s not already downloaded ' % scene_id
                # connect to earthexplorer
                self.__connect_earthexplorer_no_proxy(usgs)
                down_check = self.__downloadChunks(url, str(output_dir), scene_id+'.tgz')
                zip_check = self.__unzipimage(scene_id, output_dir)
            elif status == 4:
                print 'main: product %s not already downloaded, other error issues ' % scene_id
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
        unzip_dir = output_dir
        unzipdfile=[os.path.join(output_dir, scene_id + '_B10.TIF')]
    
        for i in unzipdfile:
            if os.path.exists(i):   #downloaded and unzipped
                return 1
        if os.path.isfile(tgzfile):    #downloaded, not unzipped
            return 2
        else:    #not downloaded
            try:
                data = urllib2.urlopen(url)
            except urllib2.HTTPError, e:
                if e.code == 500:
                    print 'get_status:  file does not exist!'
                else:
                    print 'get_status: HTTP Error: %s %s' % (e.code, e.reason)
                return 4
            except urllib2.URLError, e:
                print 'URL Error: %s %s' % (e.reason, url)
                return 4
            lines = data.read()

            if (data.info().gettype() == 'text/html'):
                print "Error : the file is in html format"
                return 4

            if lines.find('Download Not Found') > 0:
                print "Error: Download Not Found!", url
                return 4

            total_size = int(data.info().getheader('Content-Length').strip())

            if (total_size < 50000):
                print "Error: The file is too small to be a Landsat Image", url
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
                print 'download_chunks:  file does not exist!'
            else:
                print 'download_chunks: HTTP Error: %s %s' % (e.code, e.reason)
            return -1
        except urllib2.URLError, e:
            print 'URL Error: %s %s' % (e.reason, url)
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
                print 'download_chunks:  Downloading %s (%s)' % (nom_fic, total_size_fmt)
                while True:
                    chunk = data.read(chunk_size)

                    if not chunk:
                        break

                    downloaded += len(chunk)

                    f.write(chunk)

            return 0

        except urllib2.HTTPError, e:
            if e.code == 500:
                print 'download_chunks:  file does not exist!'
            else:
                print 'download_chunks: HTTP Error: %s %s' % (e.code, e.reason)
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
                print 'unzipimage: OSError'
                return -1
        else: 
            print 'unzipimage: File does not exist.'
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
            print 'check_cloud_limit: Image exceeds cloud cover value of ' + str(cloudcover) + ' defined by the user!'
            return -1

        return 0
