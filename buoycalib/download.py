import os
from urllib.request import urlopen
import urllib.error
import urllib.request
import urllib.parse
import re
import tarfile
import gzip
import shutil
import warnings

import requests

CHUNK = 1024 * 1024 * 8   # 1 MB


class RemoteFileException(Exception):
    pass


def url_download(url, out_dir, _filename=None, auth=None):
    """ download a file (ftp or http), optional auth in (user, pass) format """

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    filename = _filename if _filename else url.split('/')[-1]
    filepath = os.path.join(out_dir, filename)

    if os.path.isfile(filepath):
        return filepath

    if url[0:3] == 'ftp':
        download_ftp(url, filepath)
    else:
        download_http(url, filepath, auth)

    return filepath


def download_http(url, filepath, auth=None):

    with requests.Session() as session:
        req = session.request('get', url)

        if auth:
            resource = session.get(req.url, auth=auth)

            if resource.status_code != 200:
                raise RemoteFileException('url: {0} does not exist'.format(url))
        else:
            if not _remote_file_exists(url, auth):
                raise RemoteFileException('url: {0} does not exist'.format(url))

            resource = session.get(req.url)

        with open(filepath, 'wb') as f:
            f.write(resource.content)

    return filepath


def download_ftp(url, filepath):
    try:
        request = urlopen(url)
    except urllib.error.URLError as e:
        print(url)
        raise RemoteFileException('url: {0} does not exist'.format(url))

    with open(filepath, 'wb') as fileobj:
        while True:
            chunk = request.read(CHUNK)
            if not chunk:
                break
            fileobj.write(chunk)

    return filepath


def ungzip(filepath):
    """ un-gzip a fiile (equivalent of `gzip -d filepath`) """
    new_filepath = filepath.replace('.gz', '')

    with open(new_filepath, 'wb') as f_out, gzip.open(filepath, 'rb') as f_in:
        try:
           shutil.copyfileobj(f_in, f_out)
        except OSError as e:
            warnings.warn(str(e) + filepath, RuntimeWarning)

    return filepath


def untar(filepath, directory):
    with tarfile.open(filepath, 'r') as tf:
        tf.extractall(directory)

    return directory


def _remote_file_exists(url, auth=None):

    if auth:
        resp = requests.get(url, auth=auth)
        status = resp.status_code
    else:
        status = requests.head(url).status_code

    if status != 200:
        return False

    return True


def connect_earthexplorer_no_proxy(username, password):
    # inspired by: https://github.com/olivierhagolle/LANDSAT-Download
    # mkmitchel (https://github.com/mkmitchell) solved the token issue
    cookies = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(cookies)
    urllib.request.install_opener(opener)
    
    data = urllib.request.urlopen("https://ers.cr.usgs.gov").read()
    data = data.decode('utf-8')
    m = re.search(r'<input .*?name="csrf_token".*?value="(.*?)"', data)
    if m:
        token = m.group(1)
    else:
        print("Error : CSRF_Token not found")
        sys.exit(-3)
        
    params = urllib.parse.urlencode(dict(username=username, password=password, csrf_token=token)).encode('utf-8')
    request = urllib.request.Request("https://ers.cr.usgs.gov/login", params, headers={})
    f = urllib.request.urlopen(request)

    data = f.read()
    f.close()
    if data.decode('utf-8').find('You must sign in as a registered user to download data or place orders for USGS EROS products')>0:
        # auth failed, TODO raise warning
        return False

    return True


def download_earthexplorer(url, out_file):
    """ 
    Slightly lower level implemenation that handles earthexplorer's redirection.
    inspired by: https://github.com/olivierhagolle/LANDSAT-Download
    """ 
    try:
        req = urllib.request.urlopen(url)
    
        #if downloaded file is html
        if (req.info().get_content_type()=='text/html'):
            raise RemoteFileException("error : file is in html and not an expected binary file, url: {0}".format(url))

        #if file too small           
        total_size = int(req.getheader('Content-Length').strip())
        if (total_size<50000):
           raise RemoteFileException("Error: The file is too small to be a Landsat Image, url: {0}".format(url))

        #download
        CHUNK = 1024 * 1024 *8

        with open(out_file, 'wb') as fp:
            while True:
                chunk = req.read(CHUNK)
                if not chunk: break
                fp.write(chunk)

    except urllib.error.HTTPError as e:
        if e.code == 500:
            raise RemoteFileException("File doesn't exist url: {0}".format(url))
        else:
            raise RemoteFileException("HTTP Error:" + e.code + url)
    
    except urllib.error.URLError as e:
        raise RemoteFileException("URL Error: {1} url: {0}".format(url, e.reason))

    return out_file