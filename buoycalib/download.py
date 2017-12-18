import os
from urllib.request import urlopen
import urllib.error
import gzip
import shutil

import requests

CHUNK = 1024 * 1024 * 8   # 1 MB


class RemoteFileException(Exception):
    pass


def url_download(url, out_dir, auth=None):
    """ download a file (ftp or http), optional auth in (user, pass) format """
    
    # TODO make this work for ftp and http and https
    #if not _remote_file_exists(url):
    #    raise ValueError('url: {0} does not exist'.format(url))

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    filename = url.split('/')[-1]
    filepath = os.path.join(out_dir, filename)

    if os.path.isfile(filepath):
        return filepath

    if url[0:3] == 'ftp':
        try:
            request = urlopen(url)
        except urllib.error.URLError as e:
            print(url)
            raise e

        with open(filepath, 'wb') as fileobj:
            while True:
                chunk = request.read(CHUNK)
                if not chunk:
                    break
                fileobj.write(chunk)

    else:
        with requests.Session() as session:

            r1 = session.request('get', url)
            if auth:
                r = session.get(r1.url, auth=auth)
            else:
                r = session.get(r1.url)

            with open(filepath, 'wb') as f:
                f.write(r.content)

    return filepath


def ungzip(filepath):
    """ un-gzip a fiile (equivalent of `gzip -d filepath`) """
    new_filepath = filepath.replace('.gz', '')
    with open(new_filepath, 'wb') as f_out, gzip.open(filepath, 'rb') as f_in:
        shutil.copyfileobj(f_in, f_out)

    return new_filepath


def _remote_file_exists(url):
    status = requests.head(url).status_code

    if status != 200:
        return False
        #raise RemoteFileException('File {0} doesn\'t exist.'.format(url))

    return True