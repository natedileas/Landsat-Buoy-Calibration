import datetime
import logging
import os
import sys
import tarfile
import urllib2, urllib

import settings

def download(cc):
    """ 
    Download and extract landsat data. 

    Args:
        cc: CalibrationController object

    Returns:
        scene_id: scene_id that was downloaded

    """
    # assign prefix, repert, stations
    if cc.satelite == 'LC8':
        repert = '4923'
        
    elif cc.satelite == 'LE7':
        repert = '3373'

    elif cc.satelite == 'LT5':
        repert = '3119'

    scene_ids = [cc.scene_id]
    date = datetime.datetime.strftime(cc.date, '%Y%j')

    for version in ['00', '01', '02', '03', '04']:
        scene_ids.append(cc.satelite + cc.wrs2 + date + cc.station + version)
    
    for scene_id in scene_ids:
        url = settings.LANDSAT_URL % (repert, scene_id)
        tarfile = os.path.join(settings.LANDSAT_DIR, scene_id + '.tgz')
        metafile = os.path.join(cc.scene_dir, scene_id + '_MTL.txt')
        
        # already downloaded and unzipped
        if os.path.exists(metafile):
            logging.info('Product %s already downloaded and unzipped ' % scene_id)
            break
            
        # already downloaded
        elif os.path.isfile(tarfile):
            logging.info('product %s already downloaded ' % scene_id)
            unzipimage(tarfile, cc.scene_dir)
            os.remove(tarfile)
            break
            
        # not downloaded
        else:
            logging.info('product %s not already downloaded ' % scene_id)

            connect_earthexplorer_no_proxy()

            if download_landsat_product(url, tarfile) is False:
                continue

            unzipimage(tarfile, cc.scene_dir)
            os.remove(tarfile)

            break

    if cc.scene_id != scene_id:
        logging.warning('scene_id and landsat_id do not match')

    return scene_id

def connect_earthexplorer_no_proxy():
    """ 
    Connect to EarthExplorer without a proxy.
    
    Args:
        usgs: dict, user and password information

    Returns:
        None
        
    Raises:
        urllib2.HTTPError: if authentication does not occur
    """
    logging.info("Establishing connection to Earthexplorer...")

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
    urllib2.install_opener(opener)
    params = urllib.urlencode(settings.USGS_LOGIN)

    f = opener.open("https://ers.cr.usgs.gov/login", params)
    data = f.read()
    f.close()

    if data.find('You must sign in as a registered user to download data or place orders for USGS EROS products')>0 :
        logging.error('Authentification failed')
        raise urllib.HTTPError('Authentification failed')

    logging.info('Connected')

def download_landsat_product(url,out_file):
    """
    Download the landsat product from the url.

    Args:
        url: url to download from
        out_file: file to save to

    Returns:
        True or False, depending on success
    
    Raises: 
        TypeError: if the downlaod is not found
    """

    try:
        req = urllib2.urlopen(url)

        if (req.info().gettype()=='text/html'):
            logging.error( "In HTML format, authentication probably failed.")
            lignes=req.read()

            if lignes.find('Download Not Found')>0 :
                raise TypeError('Download Not Found')
            else:
                raise urllib2.HTTPError()

        total_size = int(req.info().getheader('Content-Length').strip())

        if (total_size<50000):
            logging.error("The file is too small to be a Landsat Product")
            return False

        CHUNK = 1024 * 1024 *8

        logging.info('Downloading Landsat Product')

        with open(out_file, 'wb') as fp:
            while True:
                chunk = req.read(CHUNK)
                if not chunk: break
                fp.write(chunk)

    except urllib2.HTTPError, e:
        if e.code == 500:
            logging.error('File doesn\'t exist')
        else:
            logging.error("HTTP Error: %s %s:" % (e.reason , url))
        return False
    except urllib2.URLError, e:
        logging.error("URL Error: %s %s:" % (e.reason , url))
        return False

    logging.info('Finished Download')
    return True

def unzipimage(in_file, out_dir):
    """ 
    Unzip tar file.
    
    Args:
        in_file: file to extract from
        out_dir: directory to extract files to

    Returns:
        None
    """
        
    with tarfile.open(in_file, 'r') as f:
        #files = f.getmembers()  # TODO choose which files to extract from info
        # match regexs to files.name , search for bands and MTL file
        # then f.extractfile(name or info_object)
        f.extractall(out_dir)

def read_metadata(cc):
    """ 
    Read landsat metadata from MTL file and return a dict with the values.
    
    Args:
        cc: CalibrationController object

    Returns:
        metadata: dict of landsat metadata from _MTL.txt file.
    """
    filename = os.path.join(cc.scene_dir, cc.scene_id + '_MTL.txt')
    chars = ['\n', '"', '\'']    # characters to remove from lines
    desc = []
    data = []

    # open file, split, and save to two lists

    with open(filename, 'r') as f:
        for line in f:
            try:
                info = line.strip(' ').split(' = ')
                info[1] = info[1].translate(None, ''.join(chars))
                desc.append(info[0])
                data.append(float(info[1]))
            except ValueError:
                data.append(info[1])
            except IndexError:
                #normal thing, caused by non-delimeted lines
                pass
    
    metadata = dict(zip(desc, data))   # create dictionary

    return metadata
