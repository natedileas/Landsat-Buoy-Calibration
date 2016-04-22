import os
import sys
import subprocess
import datetime
import time
import logging

def download(cc):
    """ download landsat data and parse metadata. """
    
    #downloaded_LID = DownloadLandsatScene().main(cc)

    if not os.path.exists(cc.scene_dir):
        os.makedirs(cc.scene_dir)

    # read password file
    try:
        with open(os.path.join(cc.filepath_base, 'data/shared/usgs_login.txt'), 'r') as f:
            account, passwd = f.readline().split(' ')
        passwd = passwd.replace('\n', '')
        usgs = {'account': account, 'passwd': passwd}
    except IOError:
        logging.error('usgs password file problem (IOError)')
        sys.exit(-1)
        
    prefix = 'LC8'

    # assign prefix,  repert, stations
    if cc.satelite == 'LC8':
        prefix = 'LC8'
        repert = '4923'
        stations = ['LGN']
    if cc.satelite == 'LE7':
        prefix = 'LE7'
        repert = '3373'
        stations = ['EDC', 'SGS', 'AGS', 'ASN', 'SG1']

    scene_ids = [cc.scene_id]
    date = datetime.datetime.strftime(cc.date, '%Y%j')
    
    for station in stations:
        for version in ['00', '01', '02', '03', '04']:
            scene_ids.append(prefix + cc.wrs2 + date + station + version)
    
    # remove any ids which are None
    scene_ids = filter(None, scene_ids)
    
    # iterate through ids
    tgz_out_dir = os.path.realpath(os.path.join(cc.scene_dir, '..'))
    for scene_id in scene_ids:
        url = 'http://earthexplorer.usgs.gov/download/%s/%s/STANDARD/EE' % (repert, scene_id)
        tgzfile = os.path.join(tgz_out_dir, scene_id + '.tgz')
        metafile = os.path.join(cc.scene_dir, scene_id + '_MTL.txt')
        unzipdfile = os.path.join(cc.scene_dir, scene_id + '_B10.TIF')
        
        # already downloaded and unzipped
        if os.path.exists(unzipdfile) and os.path.exists(metafile):
            logging.info('Product %s already downloaded and unzipped ' % scene_id)
            break
            
        # already downloaded
        elif os.path.isfile(tgzfile):
            logging.info('product %s already downloaded ' % scene_id)
            unzipimage(tgzfile, cc.scene_dir)
            break
            
        # not downloaded
        else:
            logging.info('product %s not already downloaded ' % scene_id)
            
            # connect
            connect_cmd = "wget -q --cookies=on --save-cookies cookies.txt --keep-session-cookies --post-data 'username=nid4986&password=Fivyx689' https://ers.cr.usgs.gov/login/ >/dev/null"
            download_cmd = 'wget --cookies=on --load-cookies cookies.txt --keep-session-cookies --output-document=%s %s' % (tgzfile, url)
            
            if not os.path.exists(os.path.join(cc.filepath_base, 'cookies.txt')):
                subprocess.check_call(connect_cmd, shell=True)   
                os.remove(os.path.join(cc.filepath_base, 'index.html'))
                time.sleep(1)
                
            subprocess.check_call(download_cmd, shell=True)
            
            unzipimage(tgzfile, cc.scene_dir)
            break

    if cc.scene_id != scene_id:
        logging.warning('scene_id and landsat_id do not match')

    return scene_id

def unzipimage(tgz_file, out_dir):
    """ Unzip tgz file. """
    
    if os.path.exists(tgz_file):
        try:
            subprocess.check_call('tar zxvf %s -C %s >/dev/null' % (tgz_file, out_dir), shell=True)
            os.remove(tgz_file)
        except KeyboardInterrupt:
            logging.error('KeyboardInterrupt')
            sys.exit(-1)
    else: 
        logging.error('File %s does not exist.' % tgz_file)
        sys.exit(-1)
        
    return 0

def read_metadata(cc):
    filename = os.path.join(cc.scene_dir, cc.scene_id + '_MTL.txt')
    chars = ['\n', '"', '\'']    # characters to remove from lines
    desc = []
    data = []

    # open file, split, and save to two lists
    try:
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
                    logging.warning('Index Error in metadata parsing, normal thing')
                    
    except IOError:
        logging.error('Metadata not in expected file path: %s.' % filename)
        sys.exit(-1)
    
    metadata = dict(zip(desc, data))   # create dictionary

    return metadata
